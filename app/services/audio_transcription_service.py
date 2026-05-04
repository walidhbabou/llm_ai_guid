import asyncio
import os
import tempfile
from pathlib import Path
from threading import Lock

from groq import Groq
from imageio_ffmpeg import get_ffmpeg_exe
from faster_whisper import WhisperModel

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
    _local_model: WhisperModel | None = None
    _local_model_lock = Lock()

    def __init__(self) -> None:
        self._client = Groq(api_key=settings.llm_api_key) if settings.llm_api_key else None

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> str:
        if not audio_bytes:
            raise ValidationError("Le fichier audio est vide.")

        max_size_bytes = settings.audio_max_file_size_mb * 1024 * 1024
        if len(audio_bytes) > max_size_bytes:
            raise ValidationError(
                f"Le fichier audio depasse la limite de {settings.audio_max_file_size_mb} MB."
            )

        safe_filename = self._normalize_filename(filename)
        self._validate_extension(safe_filename)

        if self._client is None:
            # Run local transcription in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._transcribe_local(
                    audio_bytes=audio_bytes,
                    filename=safe_filename,
                    language=language,
                ),
            )

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

    def _transcribe_local(
        self,
        *,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> str:
        normalized_language = self._normalize_language(language)
        model = self._get_local_model()
        suffix = Path(filename).suffix or ".webm"

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file.flush()
                temp_path = temp_file.name

            segments, _info = model.transcribe(
                temp_path,
                language=normalized_language,
                vad_filter=True,
            )
        except Exception as exc:
            raise AudioTranscriptionError(
                f"Erreur pendant la transcription audio locale: {str(exc)}"
            ) from exc
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        text = " ".join(segment.text.strip() for segment in segments).strip()
        if len(text) < 2:
            raise AudioTranscriptionError(
                "La transcription est vide ou trop courte. Reessayez avec une question plus claire."
            )
        return text

    def _get_local_model(self) -> WhisperModel:
        if self._local_model is not None:
            return self._local_model

        with self._local_model_lock:
            if self._local_model is None:
                self._ensure_ffmpeg_available()
                self._local_model = WhisperModel(
                    settings.local_whisper_model,
                    device=settings.local_whisper_device,
                    compute_type=settings.local_whisper_compute_type,
                )
        return self._local_model

    def _ensure_ffmpeg_available(self) -> None:
        try:
            ffmpeg_exe = get_ffmpeg_exe()
        except Exception as exc:
            raise AudioTranscriptionError(
                "FFmpeg est requis pour la transcription locale mais n'a pas ete trouve."
            ) from exc

        ffmpeg_dir = os.path.dirname(ffmpeg_exe)
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        os.environ.setdefault("FFMPEG_BINARY", ffmpeg_exe)

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
