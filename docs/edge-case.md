# AI-Powered Restaurant Recommendation System — Edge Cases & Corner Scenarios

This document maps out the potential edge cases, failure modes, and corner scenarios for the AI-Powered Restaurant Recommendation System. It serves as a guide for development, robust error handling, and testing.

---

## Table of Contents
1. [Data Ingestion & Preprocessing Edge Cases](#1-data-ingestion--preprocessing-edge-cases)
2. [User Input & Validation Edge Cases](#2-user-input--validation-edge-cases)
3. [Domain Filtering & Budget Mapping Edge Cases](#3-domain-filtering--budget-mapping-edge-cases)
4. [Groq LLM Integration & Orchestration Edge Cases](#4-groq-llm-integration--orchestration-edge-cases)
5. [Response Parsing & Post-LLM Grounding Edge Cases](#5-response-parsing--post-llm-grounding-edge-cases)
6. [Presentation Layer (Streamlit UI) Edge Cases](#6-presentation-layer-streamlit-ui-edge-cases)

---

## 1. Data Ingestion & Preprocessing Edge Cases

These scenarios occur when loading and cleaning the Zomato Hugging Face dataset on startup or cache building.

| Scenario / Edge Case | Trigger / Condition | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Missing Critical Fields** | A restaurant row has `null` or missing values for `name` or `location`. | Domain logic filters and UI cards will crash or display incomplete entries. | **Drop and Log:** Drop the row during preprocessing. Log a warning with the row index/identifier. |
| **Unparseable / Malformed Ratings** | Ratings are stored as non-numeric strings (e.g., `"NEW"`, `"-"`, `"None"`, or `"4.2/5"`). | Coercion to `float` raises a `ValueError`. | **Normalize & Impute:**<br>1. Strip string noise (e.g., `"/5"`).<br>2. Convert to float.<br>3. Map unrated indicators (like `"NEW"`, `"-"`) to `0.0` or a sentinel value (e.g., `None`), or exclude them from recommendation eligibility if a minimum rating filter is active. |
| **Malformed Cost Fields** | Cost is formatted with currency symbols (e.g., `"Rs. 500"`, `"₹1,200"`), commas, ranges (e.g., `"300-500"`), or is missing. | Coercion to `int` fails. | **Regex Parser:**<br>1. Use regex to strip non-digit characters except commas and hyphens.<br>2. If a range is provided, calculate the average (e.g., `"300-500"` $\rightarrow$ `400`).<br>3. If missing, assign `None` and exclude from budget matching, or assign a default/median value based on other restaurants in that locality. |
| **Messy Cuisine Strings** | Cuisines are stored in various delimiters (e.g., `"Italian, Chinese"`, `"Italian|Chinese"`, `"Italian / Chinese"`) or have trailing spaces. | Multi-cuisine queries won't match, or exact matches will fail due to spacing. | **Tokenization & Normalization:**<br>1. Replace alternate delimiters (e.g., `|`, `/`) with commas.<br>2. Split by comma and strip whitespace from each element.<br>3. Convert all cuisines to lowercase for matching, while preserving a title-cased list for UI rendering. |
| **Inconsistent Locality vs. City** | Locations are named inconsistently (e.g., `"Bangalore"`, `"Bengaluru"`, or specific suburbs like `"Indiranagar, Bangalore"`). | Filtering for `"Bangalore"` returns zero results because the data matches a suburb name or old spelling. | **Locality Canonicalization:**<br>1. Maintain an alias dictionary for cities (e.g., `"bengaluru"` $\rightarrow$ `"bangalore"`).<br>2. Support substring matches (e.g., if a user selects `"Bangalore"`, match any restaurant containing `"Bangalore"` in its location field). |
| **Duplicate Restaurant Entries** | The dataset contains identical restaurants with same name and address due to scrape repeats. | LLM prompt contains duplicate candidates; recommendations contain duplicate items. | **De-duplication:** Deduplicate rows on `name` + `address` / `latitude` + `longitude` during ingestion. |
| **Hugging Face Down / No Network** | Hugging Face is unreachable during the first startup (cache miss). | App crashes on startup. | **Local Fallback:** Bundle a minimal, clean static CSV sample of the dataset in the project repo. Fallback to loading this file if Hugging Face is offline. |

---

## 2. User Input & Validation Edge Cases

These scenarios occur when users submit preferences through the presentation layer.

| Scenario / Edge Case | Trigger / Condition | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Empty or Whitespace Fields** | User submits spaces for location or cuisine. | Database filters match nothing, or filters fetch unwanted entries. | **Input Trimming & Required Validation:** Enforce non-empty inputs in `InputValidator`. Strip leading/trailing whitespaces. |
| **Special Characters / Injection Attempts** | User inputs SQL-like commands, HTML tags, or system prompt commands (e.g., `"Ignore previous instructions..."`) in input fields. | Prompt injection or UI layout breakage. | **Sanitization:**<br>1. Sanitize additional preferences to strip HTML tags.<br>2. Design system prompts to treat user input strictly as data context (e.g., XML tags or JSON structure) to isolate it from instruction parsing. |
| **Location Not in Dataset** | User enters a location that exists globally but is missing from the Zomato dataset (e.g., `"New York"`). | Empty candidate list, UI shows a blank recommendation page. | **Autocomplete dropdowns:** Populate UI selection boxes with known, unique cities extracted from the dataset rather than free-text fields. |
| **Cuisine Misspellings** | User searches for `"Itallian"` instead of `"Italian"`. | 0 matching candidates. | **Levenshtein Distance / Fuzzy Match:** If no exact match is found, check if a fuzzy match exists in the unique cuisine list and suggest it, or use a dropdown selector in the UI. |
| **Extreme "Additional Preferences"** | User pastes a huge block of text (e.g., 50,000 characters) into the "additional preferences" text box. | Prompts exceed the Groq model's token limits, causing API errors (400 Bad Request) or high latency. | **Character Limits:** Enforce a strict maximum length (e.g., 500 characters) in the UI and validate it in the application layer. |

---

## 3. Domain Filtering & Budget Mapping Edge Cases

These scenarios occur inside the `RestaurantFilter` and `BudgetMapper` before passing candidates to the LLM.

| Scenario / Edge Case | Trigger / Condition | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Zero Filter Matches** | No restaurants match the combined hard filters (e.g., high rating + low budget + specific cuisine in a small town). | The filtered list is empty. If sent to the LLM, the LLM will fail or hallucinate. | **Short-circuit:** If the candidate list is empty, bypass the LLM completely. Return an empty recommendation list immediately with a helpful UI message (e.g., *"No restaurants matched your filters. Try lowering the minimum rating or widening your budget."*). |
| **Extremely Large Candidate Pool** | A query matches 500 restaurants (e.g., medium budget North Indian in Delhi). | Sending 500 candidates to the LLM exceeds context limits and increases costs/latency. | **Pre-sorting & Capping:** Apply a deterministic sorting algorithm (e.g., sort by rating descending, then by votes descending) and cap the candidates at `MAX_CANDIDATES` (typically 20). |
| **Boundary Budget Values** | A restaurant's cost-for-two is exactly ₹500 or ₹1500 (the default thresholds). | It might get excluded if ranges are exclusive (e.g., `low: 0-500`, `medium: 500-1500` - where does 500 land?). | **Inclusive Ranges:** Use overlapping or inclusive comparison operators: `low`: $0 \le x \le 500$, `medium`: $500 < x \le 1500$, `high`: $x > 1500$. |
| **Null/None Cost Filtering** | Restaurant matches location, rating, and cuisine, but `cost_for_two` is `None`. | Budget filtering might drop it, even if it is a perfect match. | **Handle Nulls Gracefully:**<br>1. If budget is set to `"medium"`, check if similar restaurants suggest a default range.<br>2. Alternatively, exclude null-cost restaurants *only* if the budget filter is active, or warn the user that some unpriced options were omitted. |
| **Highly Restrictive Soft Preferences** | The hard filters return 20 candidates, but none match the user's soft "additional preference" (e.g., `"dog-friendly"`). | The LLM might rank restaurants poorly or struggle to find a match. | **Grounded explanations:** Ensure prompt instructions state that if no candidate matches the soft preferences, the LLM should still rank by hard constraints and clearly state in the explanation that the soft preferences could not be met. |

---

## 4. Groq LLM Integration & Orchestration Edge Cases

These scenarios cover failures in communicating with the Groq API and managing tokens.

| Scenario / Edge Case | Trigger / Condition | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Rate Limit Exceeded (HTTP 429)** | High volume of users or rapid requests exceeds Groq API token-per-minute (TPM) or request-per-minute (RPM) limits. | The API request fails, and the application cannot generate recommendations. | **Exponential Backoff & Fallback:**<br>1. Implement exponential backoff retry logic (using packages like `tenacity`).<br>2. If retries fail, fall back to a deterministic recommendation list (e.g., sorted by rating) with a warning banner indicating that AI-explanations are temporarily unavailable. |
| **API Timeout** | Groq API takes too long to respond (e.g., network latency or backend overload). | The app hangs, causing a poor user experience. | **Strict Timeouts:** Set a client-side timeout (e.g., 5 seconds). Catch timeouts and trigger the fallback recommendation engine. |
| **API Key Missing/Expired** | `GROQ_API_KEY` is empty, incorrect, or expired in the `.env` file. | The application crashes on the first LLM request. | **Startup Check:** Validate the presence and format of the `GROQ_API_KEY` when starting the app. If missing, disable LLM recommendation mode, warn the administrator/user, and use the fallback rule-based system. |
| **Model Deprecation** | The configured model (e.g., `llama-3.1-8b-instant`) is deprecated or removed from the Groq catalog. | API calls return HTTP 400 Bad Request. | **Configurable Fallback:** Use a list of models in order of preference. If the primary model fails with a model-not-found error, try the secondary model (e.g., fallback from `llama-3.3-70b-versatile` to `llama-3.1-8b-instant`). |

---

## 5. Response Parsing & Post-LLM Grounding Edge Cases

These scenarios cover parsing failures, hallucinations, or malformed JSON returned by the Groq LLM.

| Scenario / Edge Case | Trigger / Condition | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Malformed JSON Response** | The LLM output contains extra conversational text, is truncated, or fails JSON syntax validation. | `json.loads()` raises a `JSONDecodeError`. | **Resilient Parser & Retry:**<br>1. Use regex to extract everything between the outer `{` and `}` or `[ ` and ` ]`. <br>2. If parsing still fails, run a second, cheaper "fixer" call to the LLM, or fallback to returning the filtered candidates sorted by rating/votes with a generic system-generated explanation. |
| **Hallucinated Restaurant IDs** | The LLM invents a restaurant or uses an ID that was not in the provided candidates list. | Merging the recommendation with the original dataset raises a key lookup error. | **Grounded Validation:** Strictly filter the LLM's response list against the original candidate set. Ignore/drop any recommended restaurant whose ID is not present in the candidate set. |
| **Hallucinated Attributes** | The LLM references details not present in the dataset (e.g., *"This place has a beautiful rooftop gardens"* when the dataset has no such detail). | Misleading recommendations. | **Strict Prompt Rules:** Provide strong system prompt guidelines emphasizing that explanations must only be based on the provided attributes, or make it clear to the user that descriptions are AI-generated based on training data context. |
| **Duplicate Ranks / Ranks Missing** | LLM assigns rank `1` to multiple restaurants, or skips rank numbers (e.g., ranks: `1, 2, 5`). | UI sorting is inconsistent or looks broken. | **Re-indexing:** Ignore the ranks returned by the LLM for sorting. Order the list by the array sequence returned in the JSON and re-assign sequential ranks `1` through `N` programmatically. |
| **No Recommendations Returned** | LLM returns a valid JSON structure, but the `"recommendations"` array is empty despite candidates being sent. | UI displays a blank result state even though matches exist. | **Default Ranking:** If the LLM returns an empty array, fall back to ranking the top 5 candidates by rating and display them with standard system explanations. |

---

## 6. Presentation Layer (Streamlit UI) Edge Cases

These scenarios happen during user interactions within the Streamlit browser UI.

| Scenario / Edge Case | Trigger / Condition | Impact | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Rapid Double Submission** | User double-clicks the "Get Recommendations" button or clicks it repeatedly while loading. | Triggering duplicate LLM API calls, causing rate-limiting and wasting tokens. | **Disable Button / Loading State:** Use Streamlit's native loading features (`st.spinner`, button disabling) or a session state boolean (`st.session_state.loading = True`) to prevent multiple clicks during active requests. |
| **Session State Disconnect** | Streamlit page refreshes, or connection to the local server drops temporarily. | User loses all selected preferences and results. | **State Persistence:** Cache critical data blocks like the preprocessed dataset using `@st.cache_resource` so that page re-rendering is instant and doesn't trigger reload latency. |
| **Extremely Long Text Rendering** | The LLM-generated explanation is exceptionally long (e.g., paragraph-length). | UI layout breaks or looks visually unappealing. | **Clamping UI Text:** Truncate explanations visually using a "Read More" expander or restrict characters in the system prompt instructions (e.g., *"Limit explanations to 2-3 sentences"*). |
| **Displaying Non-Standard Characters** | Restaurant names or cuisines contain non-ASCII characters or emojis. | Rendering errors in the console or UI. | **UTF-8 Encoding:** Ensure all file reads, writes, and output rendering use `utf-8` encoding. |
