from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl

class Settings(BaseSettings):
    APP_NAME: str = "EaseMe API"
    APP_ENV: str = "dev"
    APP_DEBUG: bool = True

    DATABASE_URL: AnyUrl

    SUPABASE_JWKS_URL: str
    JWT_AUDIENCE: str = "authenticated"
    JWT_ISSUER: str

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.4

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()  # type: ignore
