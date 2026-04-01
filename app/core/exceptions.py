class AppError(Exception):
    def __init__(self, message: str, code: str = "app_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class LLMAnalysisError(AppError):
    def __init__(self, message: str = "Impossible d'analyser la requete utilisateur") -> None:
        super().__init__(message=message, code="llm_analysis_error")


class GoogleMapsError(AppError):
    def __init__(self, message: str = "Erreur Google Maps API") -> None:
        super().__init__(message=message, code="google_maps_error")


class AudioTranscriptionError(AppError):
    def __init__(self, message: str = "Impossible de transcrire l'audio utilisateur") -> None:
        super().__init__(message=message, code="audio_transcription_error")


class ValidationError(AppError):
    def __init__(self, message: str = "Requete invalide") -> None:
        super().__init__(message=message, code="validation_error")
