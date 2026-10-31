from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://melooha:melooha@localhost:5432/melooha"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
