from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GRCShield"
    environment: str = "development"

    # Portfolio disclaimer surfaced by the API and stamped on every report.
    # Rule 1 of the project charter: never imply FinFlow is certified or audited.
    data_disclaimer: str = (
        "Sample / Portfolio Assessment. FinFlow Technologies is a fictional company. "
        "No certification body or audit firm has assessed this data."
    )

    database_url: str = "postgresql+psycopg://grcshield:grcshield@db:5432/grcshield"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Overridden by JWT_SECRET in any real deployment. The default exists so the demo
    # starts without configuration; it is not a secret and is not treated as one.
    jwt_secret: str = "dev-only-not-a-secret-change-me"

    # Demo credentials, published in the README on purpose. Sourced from settings so a
    # deployment can change them without touching seed code.
    demo_auditor_username: str = "auditor"
    demo_auditor_password: str = "auditor-demo-2026"
    demo_manager_username: str = "isms.manager"
    demo_manager_password: str = "manager-demo-2026"

    @property
    def jwt_secret_is_default(self) -> bool:
        return self.jwt_secret == "dev-only-not-a-secret-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
