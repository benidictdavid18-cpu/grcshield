"""The AI assistant layer.

    app/api/routes/ai.py      HTTP: authentication, request shapes, status codes
        │
        ▼
    service.py                the flow, and the interaction log
        │           ├── context.py     what the model is allowed to see
        │           ├── prompts.py     what it is told, assembled server-side
        │           ├── response.py    what it is allowed to answer
        │           └── guardrails.py  fencing in, claim checking out
        ▼
    provider.py               the abstraction: complete() and status()
        │
        ▼
    ollama.py                 the only module that knows Ollama exists

The direction of the arrows is the design. The GRC services -- ``risk_scoring``,
``soa_validation``, ``control_testing``, ``privacy_continuity`` -- do not appear
anywhere in this package's imports, and nothing in this package writes to a register.
The assistant reads records and produces text beside them. It is not in the path of any
decision the management system makes.
"""

from app.services.ai.context import ContextItem, ContextNotFound, RecordContext
from app.services.ai.provider import (
    AiDisabled,
    AiError,
    AiProvider,
    AiTimeout,
    AiUnavailable,
    Completion,
    InvalidAiResponse,
    ProviderStatus,
)
from app.services.ai.service import (
    ADVISORY_LABEL,
    ADVISORY_NOTE,
    AiResult,
    AIService,
    AiStatus,
    check_control_refs,
    get_ai_service,
    normalise_control_ref,
    output_guardrail_codes,
    output_guardrail_notes,
)

__all__ = [
    "ADVISORY_LABEL",
    "ADVISORY_NOTE",
    "AIService",
    "AiDisabled",
    "AiError",
    "AiProvider",
    "AiResult",
    "AiStatus",
    "AiTimeout",
    "AiUnavailable",
    "Completion",
    "ContextItem",
    "ContextNotFound",
    "InvalidAiResponse",
    "ProviderStatus",
    "RecordContext",
    "check_control_refs",
    "get_ai_service",
    "normalise_control_ref",
    "output_guardrail_codes",
    "output_guardrail_notes",
]
