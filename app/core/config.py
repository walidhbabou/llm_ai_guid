from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_maps_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
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
