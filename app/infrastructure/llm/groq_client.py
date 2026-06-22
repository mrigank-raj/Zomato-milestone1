from groq import Groq
from app.infrastructure.llm.base import LLMClient
from app.domain.models import LLMRequest

class GroqClient(LLMClient):
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def complete(self, request: LLMRequest) -> str:
        response = self.client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            temperature=request.temperature,
            max_tokens=2500,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
