from pathlib import Path

from groq import Groq

from app.core.config import settings
from app.core.exceptions import AudioTranscriptionError, ValidationError

_SUPPORTED_AUDIO_EXTENSIONS = {
    ".flac",
    ".m4a",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".ogg",
    ".wav",
    ".webm",
}
_LANGUAGE_ALIASES = {
    "ar": "ar",
    "ar-ma": "ar",
    "en": "en",
    "en-us": "en",
    "fr": "fr",
    "fr-fr": "fr",
}


class AudioTranscriptionService:
    def __init__(self) -> None:
        self._client = Groq(api_key=settings.llm_api_key) if settings.llm_api_key else None

    def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> str:
        if self._client is None:
            raise AudioTranscriptionError(
                "Aucune cle LLM valide detectee: impossible de transcrire l'audio cote backend."
            )

        if not audio_bytes:
            raise ValidationError("Le fichier audio est vide.")

        max_size_bytes = settings.audio_max_file_size_mb * 1024 * 1024
        if len(audio_bytes) > max_size_bytes:
            raise ValidationError(
                f"Le fichier audio depasse la limite de {settings.audio_max_file_size_mb} MB."
            )

        safe_filename = self._normalize_filename(filename)
        self._validate_extension(safe_filename)

        request_payload = {
            "file": (safe_filename, audio_bytes),
            "model": settings.groq_speech_model,
            "response_format": "json",
            "temperature": 0.0,
        }

        normalized_language = self._normalize_language(language)
        if normalized_language:
            request_payload["language"] = normalized_language

        try:
            transcription = self._client.audio.transcriptions.create(**request_payload)
        except Exception as exc:
            raise AudioTranscriptionError(
                f"Erreur pendant la transcription audio: {str(exc)}"
            ) from exc

        text = " ".join(str(getattr(transcription, "text", "")).split()).strip()
        if len(text) < 2:
            raise AudioTranscriptionError(
                "La transcription est vide ou trop courte. Reessayez avec une question plus claire."
            )
        return text

    def _normalize_filename(self, filename: str | None) -> str:
        candidate = (filename or "").strip()
        if not candidate:
            return "question.webm"
        return Path(candidate).name

    def _validate_extension(self, filename: str) -> None:
        extension = Path(filename).suffix.lower()
        if extension and extension in _SUPPORTED_AUDIO_EXTENSIONS:
            return

        raise ValidationError(
            "Format audio non supporte. Utilisez mp3, wav, m4a, ogg, webm, mp4 ou flac."
        )

    def _normalize_language(self, language: str | None) -> str | None:
        if language is None:
            return None

        candidate = str(language).strip().lower()
        if not candidate:
            return None
        return _LANGUAGE_ALIASES.get(candidate, candidate)
