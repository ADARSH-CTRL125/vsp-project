from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./vsp.db"
    jwt_secret: str = "development-only-change-this-secret-before-deployment"
    jwt_minutes: int = 30
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    public_base_url: str = "http://127.0.0.1:8000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
