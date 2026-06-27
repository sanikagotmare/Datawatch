from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    gemini_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    database_url: str = "sqlite:///./datawatch.db"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    chroma_persist_dir: str = "./chroma_db"
    environment: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"
        populate_by_name = True


@lru_cache()
def get_settings():
    return Settings()