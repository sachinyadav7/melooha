from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://melooha:melooha@localhost:5432/melooha"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"

    # Question balance rules
    free_questions: int = 1  # given once when a user signs up
    questions_per_pack: int = 5  # added by one "Add questions" tap


settings = Settings()
