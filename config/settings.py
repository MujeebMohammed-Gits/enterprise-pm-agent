"""
Configuration management for Enterprise PM Agent
Handles environment variables, settings validation, and environment-specific configurations
"""

from typing import List, Optional, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/epma",
        env="DATABASE_URL"
    )
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    echo: bool = Field(default=False, env="DB_ECHO")

    model_config = SettingsConfigDict(env_prefix="DB_")


class RedisSettings(BaseSettings):
    """Redis configuration for caching and pub/sub"""
    url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    ssl: bool = Field(default=False, env="REDIS_SSL")

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class SecuritySettings(BaseSettings):
    """Security-related configuration"""
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY"
    )
    access_token_expire_minutes: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(
        default=7, env="REFRESH_TOKEN_EXPIRE_DAYS"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    # CORS origins - can be comma-separated string or list
    backend_cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="BACKEND_CORS_ORIGINS"
    )

    @validator("backend_cors_origins", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(env_prefix="")


class EmailSettings(BaseSettings):
    """Email configuration for notifications"""
    smtp_tls: bool = Field(default=True, env="SMTP_TLS")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_host: str = Field(default="smtp.example.com", env="SMTP_HOST")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    emails_from_email: str = Field(
        default="noreply@example.com", env="EMAILS_FROM_EMAIL"
    )
    emails_from_name: str = Field(
        default="Application", env="EMAILS_FROM_NAME"
    )
    emails_enabled: bool = Field(default=True, env="EMAILS_ENABLED")

    model_config = SettingsConfigDict(env_prefix="")


class AISettings(BaseSettings):
    """AI service configuration"""
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    google_ai_api_key: Optional[str] = Field(default=None, env="GOOGLE_AI_API_KEY")
    model_provider: str = Field(
        default="openai", env="AI_MODEL_PROVIDER"
    )  # openai, anthropic, google
    model_name: str = Field(
        default="gpt-4-turbo-preview", env="AI_MODEL_NAME"
    )
    max_tokens: int = Field(default=4000, env="AI_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="AI_TEMPERATURE")

    model_config = SettingsConfigDict(env_prefix="")


class IntegrationSettings(BaseSettings):
    """Third-party integration configurations"""
    # Jira
    jira_base_url: Optional[str] = Field(default=None, env="JIRA_BASE_URL")
    jira_username: Optional[str] = Field(default=None, env="JIRA_USERNAME")
    jira_api_token: Optional[str] = Field(default=None, env="JIRA_API_TOKEN")

    # Azure DevOps
    azure_devops_organization: Optional[str] = Field(
        default=None, env="AZURE_DEVOPS_ORGANIZATION"
    )
    azure_devops_personal_access_token: Optional[str] = Field(
        default=None, env="AZURE_DEVOPS_PERSONAL_ACCESS_TOKEN"
    )

    # ServiceNow
    servicenow_instance: Optional[str] = Field(
        default=None, env="SERVICENOW_INSTANCE"
    )
    servicenow_username: Optional[str] = Field(
        default=None, env="SERVICENOW_USERNAME"
    )
    servicenow_password: Optional[str] = Field(
        default=None, env="SERVICENOW_PASSWORD"
    )

    # SAP
    sap_client: Optional[str] = Field(default=None, env="SAP_CLIENT")
    sap_user: Optional[str] = Field(default=None, env="SAP_USER")
    sap_password: Optional[str] = Field(default=None, env="SAP_PASSWORD")
    sap_language: str = Field(default="EN", env="SAP_LANGUAGE")

    # Git providers
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    gitlab_token: Optional[str] = Field(default=None, env="GITLAB_TOKEN")
    bitbucket_username: Optional[str] = Field(
        default=None, env="BITBUCKET_USERNAME"
    )
    bitbucket_app_password: Optional[str] = Field(
        default=None, env="BITBUCKET_APP_PASSWORD"
    )

    model_config = SettingsConfigDict(env_prefix="")


class FeatureFlags(BaseSettings):
    """Feature flags for enabling/disabling functionality"""
    workflow_engine: bool = Field(default=True, env="FEATURE_WORKFLOW_ENGINE")
    custom_fields: bool = Field(default=True, env="FEATURE_CUSTOM_FIELDS")
    ai_assistant: bool = Field(default=True, env="FEATURE_AI_ASSISTANT")
    advanced_reporting: bool = Field(default=True, env="FEATURE_ADVANCED_REPORTING")
    integration_sync: bool = Field(default=True, env="FEATURE_INTEGRATION_SYNC")
    notifications: bool = Field(default=True, env="FEATURE_NOTIFICATIONS")
    audit_logging: bool = Field(default=True, env="FEATURE_AUDIT_LOGGING")
    rate_limiting: bool = Field(default=True, env="FEATURE_RATE_LIMITING")
    caching: bool = Field(default=True, env="FEATURE_CACHING")

    model_config = SettingsConfigDict(env_prefix="")


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration"""
    requests_per_minute: int = Field(
        default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )
    burst: int = Field(default=10, env="RATE_LIMIT_BURST")

    model_config = SettingsConfigDict(env_prefix="")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    model_config = SettingsConfigDict(env_prefix="")


class Settings(BaseSettings):
    """Main application settings"""
    # Application info
    app_name: str = Field(default="Enterprise PM Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_env: str = Field(
        default="development", env="APP_ENV"
    )  # development, staging, production
    debug: bool = Field(default=False, env="DEBUG")

    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")

    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    security: SecuritySettings = SecuritySettings()
    email: EmailSettings = EmailSettings()
    ai: AISettings = AISettings()
    integrations: IntegrationSettings = IntegrationSettings()
    features: FeatureFlags = FeatureFlags()
    rate_limit: RateLimitSettings = RateLimitSettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    # Computed properties
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        env_nested_max_split=1,
    )


# Global settings instance
settings = Settings()