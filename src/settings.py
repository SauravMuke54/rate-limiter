# settings.py
import os


class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost")
    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "10.0"))
    default_upstream: str = os.getenv("DEFAULT_UPSTREAM", "http://www.google.com")
    default_limit: int = int(os.getenv("DEFAULT_LIMIT", "2"))
    default_window: int = int(os.getenv("DEFAULT_WINDOW", "60"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()