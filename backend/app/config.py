from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    database_url: str = "postgresql+psycopg://app:dev_password_change_me@postgres:5432/user_management"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "local-development-secret-change-before-deployment"
    jwt_expire_minutes: int = 60
    otp_expire_seconds: int = 600
    otp_max_attempts: int = 5
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    smtp_starttls: bool = False
    email_from: str = "no-reply@example.com"


settings = Settings()
