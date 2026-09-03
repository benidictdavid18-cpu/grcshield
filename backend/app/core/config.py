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

    # --- Local AI (Ollama) -------------------------------------------------
    # The assistant is optional. Every one of these has a working default so the
    # application starts, and behaves correctly, with no AI configuration at all.
    ai_enabled: bool = True
    ollama_base_url: str = "http://localhost:11434"

    # A default, not an assumption. The status endpoint checks whether this model is
    # actually pulled and says so plainly when it is not, so a missing model is a
    # visible configuration problem rather than a runtime failure.
    ollama_model: str = "llama3.2:3b"
    ollama_timeout: int = 60

    # Ollama allocates a 4096-token context by default, whatever the model itself
    # supports, and silently truncates a longer prompt rather than refusing it. The
    # largest prompt this application builds -- the Annex A catalogue plus a full risk
    # record -- runs close enough to that ceiling to be uncomfortable, and the failure
    # mode is a confidently incomplete answer rather than an error. Set explicitly so
    # the margin is a decision rather than a default nobody looked at.
    ollama_num_ctx: int = 8192

    # Ceiling on the characters of record content sent to the model in one request.
    # Bounds the prompt, the latency and the blast radius of a pathological record.
    ai_max_input_chars: int = 12_000

    # Free text an analyst may add to a request. Deliberately small: this is a question
    # about a record, not a channel for supplying a system prompt.
    ai_max_question_chars: int = 500

    # /ai/status answers from a cached probe for this long. Status is polled by every
    # page load; probing a local model server on each one is waste, not diagnostics.
    ai_status_cache_seconds: int = 30

    # Ask Ollama to constrain generation to the response JSON schema. Falls back to
    # plain JSON mode automatically when the running Ollama build rejects a schema.
    ai_structured_output: bool = True

    @property
    def jwt_secret_is_default(self) -> bool:
        return self.jwt_secret == "dev-only-not-a-secret-change-me"

    @property
    def ollama_host_is_local(self) -> bool:
        """True when the configured Ollama URL points at this machine or a private net.

        Ollama has no authentication of its own. Pointing this at a public address
        publishes an unauthenticated inference endpoint, so the application warns at
        start-up rather than discovering it later.
        """
        from urllib.parse import urlparse

        host = (urlparse(self.ollama_base_url).hostname or "").lower()
        if host in ("localhost", "127.0.0.1", "::1", "host.docker.internal", "ollama"):
            return True
        return (
            host.startswith("10.")
            or host.startswith("192.168.")
            or any(host.startswith(f"172.{octet}.") for octet in range(16, 32))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
