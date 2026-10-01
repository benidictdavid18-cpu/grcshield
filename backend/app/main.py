import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import current_user, require_write
from app.api.routes import (
    records,
    ai,
    audit_trail,
    auth,
    frameworks,
    health,
    isms,
    metrics,
    privacy,
    provenance,
    acceptance,
    bootstrap,
    context,
    documents,
    attachments,
    soa_releases,
    treatment,
    planning,
    assurance,
    incidents,
    suppliers,
    people,
    obligations,
    operations,
    monitoring,
    notifications,
    maintenance,
    reports,
    risks,
    soa,
    testing,
)
from app.core.config import get_settings
from app.core.headers import SecurityHeadersMiddleware

settings = get_settings()
logger = logging.getLogger("grcshield")

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.validate_deployment()
    if settings.ai_enabled and not settings.ollama_host_is_local:
        # Ollama has no authentication of its own. Pointing OLLAMA_BASE_URL at a public
        # address publishes an unauthenticated inference endpoint to the internet, and
        # the time to notice that is at start-up rather than in an incident review.
        logger.warning(
            "OLLAMA_BASE_URL (%s) is not a loopback or private address. Ollama has no "
            "authentication; do not expose it to the public internet.",
            settings.ollama_base_url,
        )
    from app.services.maintenance import worker

    task = asyncio.create_task(worker()) if settings.maintenance_enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


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

# Added last, which makes it outermost, so every response -- a CORS preflight the
# middleware above answers itself, an error, a PDF -- carries the headers. HSTS only
# outside development; see core/headers.py.
app.add_middleware(SecurityHeadersMiddleware, hsts=settings.environment != "development")

# Open: liveness, and the endpoint you need in order to authenticate at all.
app.include_router(health.router)
app.include_router(auth.router)

# Everything else requires a valid token, and refuses a mutating request from a
# read-only role. Applied once at the router level rather than per-endpoint, because a
# per-endpoint decorator is a rule you can forget to apply to the next endpoint.
_protected = [
    records.router,
    frameworks.router,
    risks.router,
    soa.router,
    testing.router,
    isms.router,
    privacy.router,
    provenance.router,
    acceptance.router,
    bootstrap.router,
    context.router,
    documents.router,
    attachments.router,
    soa_releases.router,
    treatment.router,
    planning.router,
    assurance.router,
    incidents.router,
    suppliers.router,
    people.router,
    obligations.router,
    operations.router,
    monitoring.router,
    maintenance.router,
    metrics.router,
    reports.router,
    audit_trail.router,
]
for router in _protected:
    app.include_router(router, dependencies=[Depends(require_write)])

# The assistant. Authenticated like everything else, but mounted on ``current_user``
# rather than ``require_write``, because ``require_write`` decides what is a mutation by
# HTTP method and these POSTs mutate nothing. They read records and return text; there
# is no path from that router to a register write, and the response schemas have no
# field capable of carrying a GRC decision. The reasoning is set out in full at the top
# of app/api/routes/ai.py, and both claims are asserted in the test suite.
app.include_router(ai.router, dependencies=[Depends(current_user)])
app.include_router(notifications.router, dependencies=[Depends(current_user)])
