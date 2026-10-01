from pydantic import BaseModel


class MaintenancePolicyOut(BaseModel):
    ai_retention_days: int
    ai_request_limit: int
    ai_rate_window_seconds: int
    ai_concurrency_limit: int
    limiter_scope: str = (
        "Single server process; use a shared gateway limiter before deploying multiple workers."
    )
    retention_state: dict | None
