from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "sqlite:///./melooha.db"
    frontend_origin: str = "http://localhost:3000"

    # Question balance rules
    free_questions: int = 1  # given once when a user signs up
    questions_per_pack: int = 5  # added by one "Add questions" tap

    # LLM providers. Gemini is tried first, Groq is the fallback.
    # Model names change over time: check the current free-tier models and override in .env.
    gemini_api_key: str = ""
    groq_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    groq_model: str = "qwen/qwen3.8-27b"
    llm_timeout_seconds: float = 30.0


settings = Settings()
