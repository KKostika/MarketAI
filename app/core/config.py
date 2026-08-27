from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./marketai.db"
    DB_ECHO: bool = False  

    OPENAI_API_KEY: str | None = None
    STOCK_API_KEY: str | None = None
    NEWS_API_KEY: str | None = None
    JWT_SECRET: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    STOCK_API_URL: str = "https://www.alphavantage.com"
    NEWS_API_URL: str = "https://newsapi.org/v2/everything"
    BASE_URL: str | None = None




    class Config:
        env_file = ".env"

settings = Settings()
