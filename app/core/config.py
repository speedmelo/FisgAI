from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Melo Strategic AI"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./melo_strategic.db"

    SERPER_API_KEY: str = ""
    AI_API_KEY: str = ""
    AI_API_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    AI_MODEL: str = "gemini-1.5-flash"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
