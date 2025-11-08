from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    class Config:
        env_file = ".env"
        
settings = Settings()