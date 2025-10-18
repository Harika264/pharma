from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_NAME: str
    S3_REGION: str = "us-east-1"
    USE_MINIO: bool = True

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    BOLT_LLM_ENDPOINT: str = ""
    BOLT_LLM_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "openai"
    LLM_MAX_RETRIES: int = 3
    LLM_TIMEOUT: int = 30

    IQVIA_API_URL: str
    IQVIA_API_KEY: str
    EXIM_API_URL: str
    EXIM_API_KEY: str
    USPTO_API_URL: str
    CLINICAL_TRIALS_API_URL: str
    WEB_SEARCH_API_URL: str

    WORKER_TIMEOUT: int = 20
    WORKER_RETRY_LIMIT: int = 3
    WORKER_RETRY_BACKOFF: int = 2

    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 300
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 600

    RATE_LIMIT_PER_MINUTE: int = 100

    CACHE_TTL_SECONDS: int = 86400
    CACHE_ENABLED: bool = True

    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"

    ENABLE_PII_REDACTION: bool = True

    DATA_RETENTION_DAYS: int = 90

    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
