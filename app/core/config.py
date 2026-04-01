from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_maps_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_speech_model: str = "whisper-large-v3"
    audio_max_file_size_mb: int = 25
    google_search_radius_meters: int = 5000
    google_near_me_radius_meters: int = 2500
    google_language: str = "fr"
    google_region: str = "ma"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
