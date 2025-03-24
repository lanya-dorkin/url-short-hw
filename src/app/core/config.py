from pydantic_settings import BaseSettings
from functools import lru_cache
from redis import Redis
import os
import sys

# Detect test environment
is_test = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://urlshortener:urlshortener@postgres:5432/urlshortener",
    )

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    SHORT_CODE_LENGTH: int = 6
    DEFAULT_EXPIRY_DAYS: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_redis() -> Redis:
    if is_test:
        return DummyRedis()

    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        return redis_client
    except Exception as e:
        print(f"Redis connection error: {e}")
        return DummyRedis()


class DummyRedis:
    """A dummy Redis client for testing and development"""

    def setex(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        return None

    def delete(self, *args, **kwargs):
        pass

    def exists(self, *args, **kwargs):
        return False

    def ping(self, *args, **kwargs):
        return True
