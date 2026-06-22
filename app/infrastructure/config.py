import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def _parse_float(val: str | None, default: float) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        logging.warning(f"Could not parse float value '{val}', falling back to default '{default}'")
        return default

def _parse_int(val: str | None, default: int) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        logging.warning(f"Could not parse integer value '{val}', falling back to default '{default}'")
        return default

@dataclass
class AppConfig:
    # Required parameters
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")

    # Optional / LLM Configuration
    llm_model: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    llm_temperature: float = _parse_float(os.getenv("LLM_TEMPERATURE"), 0.3)

    # Domain Constraints
    max_candidates: int = _parse_int(os.getenv("MAX_CANDIDATES"), 20)

    # Cache and Logging
    dataset_cache_path: str = os.getenv("DATASET_CACHE_PATH", "data/cache.csv")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self) -> bool:
        """
        Validate that critical configurations are present.
        Returns True if valid, raises ValueError if a required configuration is missing.
        """
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is missing. "
                "Please configure it in your environment or .env file."
            )
        return True

def get_llm_client(config: AppConfig):
    from app.infrastructure.llm.groq_client import GroqClient
    return GroqClient(api_key=config.groq_api_key)
