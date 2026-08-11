from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import secrets


class Settings(BaseSettings):
    # -------------------------
    # Application
    # -------------------------
    app_name: str = Field("Enterprise PM Agent", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    app_env: str = Field("development", env="APP_ENV")
    debug: bool = Field(False, env="DEBUG")

    # -------------------------
    # Server
    # -------------------------
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    workers: int = Field(4, env="WORKERS")

    # -------------------------
    # Database
    # -------------------------
    database_url: str = Field(..., env="DATABASE_URL")
    db_pool_size: int = Field(10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")
    db_echo: bool = Field(False, env="DB_ECHO")

    # -------------------------
    # Redis
    # -------------------------
    redis_url: str = Field(..., env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_ssl: bool = Field(False, env="REDIS_SSL")

    # -------------------------
    # Security
    # -------------------------
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field("HS256", env="ALGORITHM")

    backend_cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="BACKEND_CORS_ORIGINS"
    )

    @field_validator("backend_cors_origins", mode="before")
    def parse_cors(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # -------------------------
    # Email
    # -------------------------
    smtp_tls: bool = Field(True, env="SMTP_TLS")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_host: str = Field("smtp.example.com", env="SMTP_HOST")
    smtp_user: Optional[str] = Field(None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    emails_from_email: str = Field("noreply@example.com", env="EMAILS_FROM_EMAIL")
    emails_from_name: str = Field("Enterprise PM Agent", env="EMAILS_FROM_NAME")
    emails_enabled: bool = Field(True, env="EMAILS_ENABLED")

    # -------------------------
    # AI
    # -------------------------
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    google_ai_api_key: Optional[str] = Field(None, env="GOOGLE_AI_API_KEY")

    ai_model_provider: str = Field("openai", env="AI_MODEL_PROVIDER")
    ai_model_name: str = Field("gpt-4-turbo-preview", env="AI_MODEL_NAME")
    ai_max_tokens: int = Field(4000, env="AI_MAX_TOKENS")
    ai_temperature: float = Field(0.7, env="AI_TEMPERATURE")

    # -------------------------
    # Integrations
    # -------------------------
    jira_base_url: Optional[str] = Field(None, env="JIRA_BASE_URL")
    jira_username: Optional[str] = Field(None, env="JIRA_USERNAME")
    jira_api_token: Optional[str] = Field(None, env="JIRA_API_TOKEN")

    azure_devops_organization: Optional[str] = Field(None, env="AZURE_DEVOPS_ORGANIZATION")
    azure_devops_personal_access_token: Optional[str] = Field(None, env="AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN")

    servicenow_instance: Optional[str] = Field(None, env="SERVICENOW_INSTANCE")
    servicenow_username: Optional[str] = Field(None, env="SERVICENOW_USERNAME")
    servicenow_password: Optional[str] = Field(None, env="SERVICENOW_PASSWORD")

    sap_client: Optional[str] = Field(None, env="SAP_CLIENT")
    sap_user: Optional[str] = Field(None, env="SAP_USER")
    sap_password: Optional[str] = Field(None, env="SAP_PASSWORD")
    sap_language: str = Field("EN", env="SAP_LANGUAGE")

    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    gitlab_token: Optional[str] = Field(None, env="GITLAB_TOKEN")
    bitbucket_username: Optional[str] = Field(None, env="BITBUCKET_USERNAME")
    bitbucket_app_password: Optional[str] = Field(None, env="BITBUCKET_APP_PASSWORD")

    # -------------------------
    # Feature Flags
    # -------------------------
    feature_workflow_engine: bool = Field(True, env="FEATURE_WORKFLOW_ENGINE")
    feature_custom_fields: bool = Field(True, env="FEATURE_CUSTOM_FIELDS")
    feature_ai_assistant: bool = Field(True, env="FEATURE_AI_ASSISTANT")
    feature_advanced_reporting: bool = Field(True, env="FEATURE_ADVANCED_REPORTING")
    feature_integration_sync: bool = Field(True, env="FEATURE_INTEGRATION_SYNC")
    feature_notifications: bool = Field(True, env="FEATURE_NOTIFICATIONS")
    feature_audit_logging: bool = Field(True, env="FEATURE_AUDIT_LOGGING")
    feature_rate_limiting: bool = Field(True, env="FEATURE_RATE_LIMITING")
    feature_caching: bool = Field(True, env="FEATURE_CACHING")

    # -------------------------
    # Rate Limiting
    # -------------------------
    rate_limit_requests_per_minute: int = Field(60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst: int = Field(10, env="RATE_LIMIT_BURST")

    # -------------------------
    # Monitoring
    # -------------------------
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


settings = Settings()
