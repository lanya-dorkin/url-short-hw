from pydantic_settings import BaseSettings
from functools import lru_cache
from redis import Redis
import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("url_shortener")

# Detect test environment
is_test = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    Settings can be overridden by environment variables or .env file.
    """

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://urlshortener:urlshortener@postgres:5432/urlshortener",
    )

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_RETRY_ATTEMPTS: int = 3
    REDIS_RETRY_DELAY: int = 1

    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    SHORT_CODE_LENGTH: int = 6
    DEFAULT_EXPIRY_DAYS: int = 30

    UNUSED_LINKS_THRESHOLD_DAYS: int = os.getenv("UNUSED_LINKS_THRESHOLD_DAYS", 90)

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to avoid loading .env file multiple times.
    """
    return Settings()


settings = get_settings()


def get_redis() -> Redis:
    """
    Get Redis client or dummy implementation if unavailable.

    Returns a dummy Redis client for testing environment or when Redis is unavailable.
    The dummy client implements the same interface but does nothing.
    """
    if is_test:
        return DummyRedis()

    retry_attempts = settings.REDIS_RETRY_ATTEMPTS
    retry_delay = settings.REDIS_RETRY_DELAY
    
    for attempt in range(retry_attempts):
        try:
            redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()
            return redis_client
        except Exception as e:
            if attempt < retry_attempts - 1:
                logger.warning(f"Redis connection attempt {attempt+1} failed: {e}. Retrying in {retry_delay}s...")
                import time
                time.sleep(retry_delay)
            else:
                logger.error(f"Redis connection failed after {retry_attempts} attempts: {e}")
                return DummyRedis()


class DummyRedis:
    """
    A dummy Redis client for testing and development.

    Implements the same interface as Redis but does nothing.
    Useful for testing or when Redis is unavailable.
    """

    def setex(self, *args, **kwargs):
        logger.debug("DummyRedis: setex called")
        pass

    def get(self, *args, **kwargs):
        logger.debug("DummyRedis: get called")
        return None

    def delete(self, *args, **kwargs):
        logger.debug("DummyRedis: delete called") 
        pass

    def exists(self, *args, **kwargs):
        logger.debug("DummyRedis: exists called")
        return False

    def ping(self, *args, **kwargs):
        logger.debug("DummyRedis: ping called")
        return True
