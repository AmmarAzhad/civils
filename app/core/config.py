from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    DATABASE_URL: str
    TEST_DATABASE_URL: str
    REDIS_URL: str

    class Config:
        case_sensitive = True
        env_file = ".env"  # T
        env_file_encoding = 'utf-8'

settings = Settings()