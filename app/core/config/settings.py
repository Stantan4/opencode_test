"""
Application Settings
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Account Risk System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: List[str] = ["*"]

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "account_risk"
    DATABASE_URL: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_LOGIN_EVENTS: str = "login_events"
    KAFKA_TOPIC_OPERATION_EVENTS: str = "operation_events"
    KAFKA_CONSUMER_GROUP: str = "risk_system"

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_DATABASE: str = "account_risk"

    # JWT
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Risk Thresholds
    RISK_THRESHOLD_LOW: int = 30
    RISK_THRESHOLD_MEDIUM: int = 60
    RISK_THRESHOLD_HIGH: int = 80

    # Model
    MODEL_PATH: str = "data/models/lstm_anomaly_detector.pt"
    MODEL_VERSION: str = "1.0.0"
    ONNX_MODEL_PATH: str = "data/models/lstm_anomaly_detector.onnx"

    # Notification
    SMS_PROVIDER: str = "aliyun"  # aliyun, tencent
    SMS_TEMPLATE_ID: str = ""
    SMS_SIGN_NAME: str = ""
    SMS_ACCESS_KEY: str = ""
    SMS_SECRET_KEY: str = ""

    EMAIL_PROVIDER: str = "sendgrid"  # sendgrid, aws_ses
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@example.com"

    JPUSH_APP_KEY: str = ""
    JPUSH_MASTER_SECRET: str = ""

    # IP Geolocation
    IP_GEO_PROVIDER: str = "maxmind"  # maxmind, ipapi
    MAXMIND_DB_PATH: str = "data/geoip/GeoLite2-City.mmdb"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    def get_database_url(self) -> str:
        """Get PostgreSQL database URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
