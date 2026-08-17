import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import require_write
from app.api.routes import (
    auth,
    frameworks,
    health,
    isms,
    metrics,
    privacy,
    reports,
    risks,
    soa,
    testing,
)
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger("grcshield")

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.jwt_secret_is_default and settings.environment != "development":
        logger.warning(
            "JWT_SECRET is still the built-in development default. Set JWT_SECRET before "
            "exposing this service to anything."
        )
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    description=(
        "Governance, Risk and Compliance platform for FinFlow Technologies "
        "(fictional). " + settings.data_disclaimer
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Open: liveness, and the endpoint you need in order to authenticate at all.
app.include_router(health.router)
app.include_router(auth.router)

# Everything else requires a valid token, and refuses a mutating request from a
# read-only role. Applied once at the router level rather than per-endpoint, because a
# per-endpoint decorator is a rule you can forget to apply to the next endpoint.
_protected = [
    frameworks.router,
    risks.router,
    soa.router,
    testing.router,
    isms.router,
    privacy.router,
    metrics.router,
    reports.router,
]
for router in _protected:
    app.include_router(router, dependencies=[Depends(require_write)])
