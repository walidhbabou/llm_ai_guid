import json
from typing import Any

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - handled at runtime
    genai = None

from app.core.config import settings


class _GeminiMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _GeminiChoice:
    def __init__(self, content: str) -> None:
        self.message = _GeminiMessage(content)


class _GeminiCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [_GeminiChoice(content)]


class _GeminiCompletions:
    def __init__(self, client: "GroqCompatibleGemini") -> None:
        self._client = client

    def create(
        self,
        *,
        model: str,
        temperature: float = 0.2,
        max_completion_tokens: int = 260,
        response_format: dict[str, Any] | None = None,
        messages: list[dict[str, Any]],
    ) -> _GeminiCompletion:
        del model
        system_prompt = ""
        user_message = ""
        for message in messages:
            if message.get("role") == "system":
                system_prompt = str(message.get("content") or "")
            elif message.get("role") == "user":
                user_message = str(message.get("content") or "")

        content = self._client.generate_text(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            response_format=response_format,
        )
        return _GeminiCompletion(content)


class _GeminiChat:
    def __init__(self, client: "GroqCompatibleGemini") -> None:
        self.completions = _GeminiCompletions(client)


class GroqCompatibleGemini:
    def __init__(self) -> None:
        if genai is None:
            raise ImportError("google-generativeai is not installed")
        if not settings.gemini_api_key.strip():
            raise ValueError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=settings.gemini_api_key.strip())
        self._model = genai.GenerativeModel(settings.gemini_model)
        self.chat = _GeminiChat(self)

    def generate_text(
        self,
        *,
        system_prompt: str,
        user_message: str,
        temperature: float,
        max_completion_tokens: int,
        response_format: dict[str, Any] | None,
    ) -> str:
        prompt = user_message.strip()
        generation_kwargs: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_completion_tokens,
        }

        if response_format and response_format.get("type") == "json_object":
            generation_kwargs["response_mime_type"] = "application/json"
            prompt = (
                f"{prompt}\n\n"
                "Important: respond only with valid JSON. Do not add markdown, code fences, or extra text."
            )

        response = self._model.generate_content(
            [system_prompt, prompt],
            generation_config=genai.types.GenerationConfig(**generation_kwargs),
        )

        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text

        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                part_text = getattr(part, "text", None)
                if isinstance(part_text, str) and part_text.strip():
                    return part_text

        return "{}"