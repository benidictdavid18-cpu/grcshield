"""The assistant, assembled.

One class holds the whole flow, so the flow is readable in one place:

    build context  ->  render prompt  ->  ask the provider  ->  validate the answer
                   ->  run output guardrails  ->  log the interaction  ->  return

Nothing in this module knows about HTTP, and nothing in it writes to a GRC record. The
only table it touches is ``ai_interactions``, which is an activity log, not part of the
management system's data. That separation is the architectural claim this feature makes,
and it is worth being able to point at a single file and show it.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.ai import AiFeature, AiInteraction, AiInteractionStatus
from app.services.ai import guardrails, prompts
from app.services.ai.context import ContextItem, RecordContext
from app.services.ai.ollama import OllamaProvider
from app.services.ai.provider import (
    AiDisabled,
    AiProvider,
    AiTimeout,
    AiUnavailable,
    InvalidAiResponse,
    ProviderStatus,
)
from app.services.ai.response import Suggestion, json_schema_for, parse

logger = logging.getLogger("grcshield.ai")

# Shown on every suggestion, in the API response and in the UI. Fixed text, defined
# once, so it cannot drift into something softer on one screen than another.
ADVISORY_LABEL = "AI suggestion — analyst validation required"
ADVISORY_NOTE = (
    "This suggestion is advisory. It has not changed any record in this system, and it "
    "carries no weight in the risk methodology. An analyst must validate it before any "
    "part of it is recorded."
)


@dataclass(frozen=True)
class AiResult:
    feature: AiFeature
    provider: str
    model: str
    generated_at: datetime
    latency_ms: int
    suggestion: Suggestion
    context_items: list[ContextItem]
    guardrail_notes: list[str] = field(default_factory=list)
    interaction_ref: str | None = None


@dataclass(frozen=True)
class AiStatus:
    enabled: bool
    provider: str
    configured_model: str
    reachable: bool
    model_available: bool
    ready: bool
    detail: str
    available_models: tuple[str, ...]
    version: str | None
    host_is_local: bool
    checked_at: datetime


class AIService:
    """The application's single entry point to a model.

    Constructed with a provider rather than constructing one, so a test supplies a fake
    and the production wiring supplies Ollama. That is the whole reason this class and
    ``AiProvider`` are separate: the tests in this project must not need a running model
    server, and a test suite that silently depends on one is a test suite that fails on
    somebody else's machine.
    """

    def __init__(self, provider: AiProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings
        self._status_cache: tuple[float, ProviderStatus] | None = None

    # --- Status ---------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return self._settings.ai_enabled

    def status(self, *, force: bool = False) -> AiStatus:
        """Cheap, cached, and never raises.

        The status chip is on every page. Probing the model server on every page load
        would be a self-inflicted load problem dressed up as monitoring, so the probe
        result is held for ``AI_STATUS_CACHE_SECONDS``.
        """
        now = datetime.now(UTC)
        if not self.enabled:
            return AiStatus(
                enabled=False,
                provider=self._provider.name,
                configured_model=self._settings.ollama_model,
                reachable=False,
                model_available=False,
                ready=False,
                detail=(
                    "The AI assistant is disabled by configuration (AI_ENABLED=false). "
                    "All GRC functionality is available."
                ),
                available_models=(),
                version=None,
                host_is_local=self._settings.ollama_host_is_local,
                checked_at=now,
            )

        cached = self._cached_status(force=force)
        return AiStatus(
            enabled=True,
            provider=cached.provider,
            configured_model=cached.configured_model,
            reachable=cached.reachable,
            model_available=cached.model_available,
            ready=cached.ready,
            detail=cached.detail,
            available_models=cached.available_models,
            version=cached.version,
            host_is_local=self._settings.ollama_host_is_local,
            checked_at=now,
        )

    def _cached_status(self, *, force: bool) -> ProviderStatus:
        ttl = max(0, self._settings.ai_status_cache_seconds)
        if not force and self._status_cache is not None:
            checked_at, cached = self._status_cache
            if time.monotonic() - checked_at < ttl:
                return cached
        probed = self._provider.status()
        self._status_cache = (time.monotonic(), probed)
        return probed

    def reset_status_cache(self) -> None:
        self._status_cache = None

    # --- Generation -----------------------------------------------------------

    def generate(
        self,
        db: Session,
        *,
        username: str,
        user_role: str,
        feature: AiFeature,
        context: RecordContext,
        response_type: type[Suggestion],
        question: str | None = None,
    ) -> AiResult:
        """Run one assistant task end to end.

        Every exit from this method -- success, disabled, unreachable, timeout, garbage
        response -- writes an interaction log row before it returns or raises. A failure
        nobody recorded is a failure nobody can count, and "how often is the assistant
        actually available?" is a question an operator will eventually ask.
        """
        if not self.enabled:
            self._log(
                db,
                username=username,
                user_role=user_role,
                feature=feature,
                context=context,
                status=AiInteractionStatus.DISABLED,
                prompt_chars=0,
                error_note="AI_ENABLED is false.",
            )
            raise AiDisabled(
                "The AI assistant is disabled by configuration. All GRC functionality "
                "is unaffected."
            )

        system = prompts.system_prompt(feature.value)
        rendered = context.render(max_chars=self._settings.ai_max_input_chars)
        cleaned_question = guardrails.neutralise(
            question, max_chars=self._settings.ai_max_question_chars
        )
        user = prompts.user_prompt(
            rendered_context=rendered,
            question=cleaned_question or None,
            schema_hint=", ".join(response_type.model_fields),
        )
        prompt_chars = len(system) + len(user)

        started = time.monotonic()
        try:
            completion = self._provider.complete(
                system_prompt=system,
                user_prompt=user,
                json_schema=json_schema_for(response_type),
            )
        except AiTimeout as exc:
            self._log(
                db,
                username=username,
                user_role=user_role,
                feature=feature,
                context=context,
                status=AiInteractionStatus.TIMEOUT,
                prompt_chars=prompt_chars,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_note=str(exc),
            )
            raise
        except AiUnavailable as exc:
            self._log(
                db,
                username=username,
                user_role=user_role,
                feature=feature,
                context=context,
                status=AiInteractionStatus.PROVIDER_UNAVAILABLE,
                prompt_chars=prompt_chars,
                latency_ms=int((time.monotonic() - started) * 1000),
                error_note=str(exc),
            )
            raise

        wall_ms = int((time.monotonic() - started) * 1000)

        try:
            suggestion = parse(completion.text, response_type)
        except InvalidAiResponse as exc:
            self._log(
                db,
                username=username,
                user_role=user_role,
                feature=feature,
                context=context,
                status=AiInteractionStatus.INVALID_RESPONSE,
                prompt_chars=prompt_chars,
                response_chars=len(completion.text),
                latency_ms=wall_ms,
                error_note=str(exc),
            )
            raise

        codes = output_guardrail_codes(suggestion)
        notes = [_FLAG_MESSAGES.get(code, code) for code in codes]
        interaction_ref = self._log(
            db,
            username=username,
            user_role=user_role,
            feature=feature,
            context=context,
            status=AiInteractionStatus.OK,
            prompt_chars=prompt_chars,
            response_chars=len(completion.text),
            latency_ms=wall_ms,
            digest=_digest(completion.text),
            # The log gets the codes; the analyst gets the sentences. A log column full
            # of paragraphs is a log column nobody can aggregate.
            guardrail_flags=codes,
        )

        return AiResult(
            feature=feature,
            provider=self._provider.name,
            model=completion.model,
            generated_at=datetime.now(UTC),
            # The provider reports its own generation time; wall time includes the
            # request. Wall time is the honest number for "how long did the analyst
            # wait", so it is the one reported.
            latency_ms=wall_ms,
            suggestion=suggestion,
            context_items=list(context.items),
            guardrail_notes=notes,
            interaction_ref=interaction_ref,
        )

    # --- Interaction log ------------------------------------------------------

    def _log(
        self,
        db: Session,
        *,
        username: str,
        user_role: str,
        feature: AiFeature,
        context: RecordContext,
        status: AiInteractionStatus,
        prompt_chars: int,
        response_chars: int | None = None,
        latency_ms: int | None = None,
        digest: str | None = None,
        guardrail_flags: list[str] | None = None,
        error_note: str | None = None,
    ) -> str | None:
        """Write the log row. Never lets a logging failure become a request failure.

        The suggestion is the thing the analyst asked for. If the audit row cannot be
        written, that is worth a loud server-side warning and worth investigating, but
        it is not worth throwing away a response the user is waiting for.
        """
        try:
            interaction = AiInteraction(
                interaction_ref=_next_interaction_ref(db),
                username=username,
                user_role=user_role,
                feature=feature,
                entity_type=context.entity_type,
                entity_ref=context.entity_ref,
                provider=self._provider.name,
                model=self._settings.ollama_model,
                status=status,
                latency_ms=latency_ms,
                prompt_chars=prompt_chars,
                response_chars=response_chars,
                response_digest=digest,
                guardrail_flags=", ".join(guardrail_flags) if guardrail_flags else None,
                error_note=error_note,
            )
            db.add(interaction)
            db.commit()
            return interaction.interaction_ref
        except SQLAlchemyError:
            logger.warning("Could not write the AI interaction log row.", exc_info=True)
            db.rollback()
            return None


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _next_interaction_ref(db: Session) -> str:
    existing = db.scalars(select(AiInteraction.interaction_ref)).all()
    numbers = [
        int(ref.rsplit("-", 1)[-1]) for ref in existing if ref.rsplit("-", 1)[-1].isdigit()
    ]
    return f"AI-{max(numbers, default=0) + 1:06d}"


def output_guardrail_codes(suggestion: Suggestion) -> list[str]:
    """Which forbidden-claim patterns the model's own words tripped.

    Flagged, not censored. The analyst sees the sentence *and* sees that it tripped a
    rule, which is more useful than a quietly edited suggestion -- and it is the same
    stance the rest of this application takes with an optimistic effectiveness basis:
    surfaced rather than blocked, because visible beats silent.
    """
    return guardrails.forbidden_claim_flags(_all_text(suggestion.model_dump()))


def output_guardrail_notes(suggestion: Suggestion) -> list[str]:
    """The same flags, rendered as the sentences shown beside the suggestion."""
    return [_FLAG_MESSAGES.get(code, code) for code in output_guardrail_codes(suggestion)]


_FLAG_MESSAGES: dict[str, str] = {
    "asserted-compliance": (
        "The suggestion asserts compliance. Compliance is determined by assessment, not "
        "by a document mentioning a standard. Treat that sentence as unsupported."
    ),
    "asserted-certification": (
        "The suggestion refers to certification. FinFlow is not certified by any body, "
        "and no part of this system may say otherwise."
    ),
    "asserted-required-wording": (
        "The suggestion claims a standard requires particular wording. Standards state "
        "objectives; the organisation chooses how to meet them."
    ),
    "asserted-control-effectiveness": (
        "The suggestion states that a control is effective. Effectiveness is recorded "
        "from a control test, not from an assistant's reading of a description."
    ),
    "asserted-test-conclusion": (
        "The suggestion states a test conclusion. The conclusion is the tester's, "
        "recorded on the workpaper and reviewed by someone else."
    ),
    "asserted-risk-score": (
        "The suggestion proposes a risk score. Likelihood and impact are scored by the "
        "analyst and cannot be set from here."
    ),
    "claimed-verification": (
        "The suggestion claims to have verified or tested something. It has not; it has "
        "read text supplied to it."
    ),
    "claimed-audit-signoff": (
        "The suggestion refers to an audit sign-off or approval. No such decision is "
        "recorded here."
    ),
}


def _all_text(payload) -> str:
    """Flatten a validated suggestion into one string for pattern matching."""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return " ".join(_all_text(value) for value in payload.values())
    if isinstance(payload, list):
        return " ".join(_all_text(item) for item in payload)
    return ""


def normalise_control_ref(raw: str) -> str:
    """What the model meant, from what the model wrote.

    Used by both the checker and the route so a suggestion cannot be accepted by one
    and dropped by the other.
    """
    return guardrails.extract_annex_a_ref(raw)


def check_control_refs(
    refs: list[str], catalogue: dict[str, str]
) -> tuple[list[str], list[str]]:
    """Split suggested Annex A identifiers into ones that exist and ones that do not.

    The catalogue passed in is the seeded ISO/IEC 27001:2022 Annex A list -- the same 93
    rows the Statement of Applicability is built from -- so this is a check against the
    real thing rather than against a pattern.

    Worth doing even though the catalogue was supplied in the prompt. Running it against
    a real model produced all three failures below on the first attempt, which is rather
    the point:

      * a 2013 identifier (A.9.4.2), because there is far more 2013 text in the world
        than 2022 text, and an auditor would spot the citation instantly;
      * an internal control identifier (AC-002) lifted straight out of the risk record
        it had just been shown, which is a different kind of confusion and deserves a
        different sentence;
      * a correct control written as "A.8.18: Use of privileged utility programs",
        which is a formatting slip rather than a wrong answer and is now accepted.

    Each rejection says which of those it was, because "invalid" tells the analyst
    nothing about how much to trust the rest of the answer.
    """
    known: list[str] = []
    rejected: list[str] = []
    for raw in refs:
        original = raw.strip()
        ref = normalise_control_ref(original)
        if ref in catalogue:
            known.append(ref)
        elif guardrails.looks_like_annex_a_2013_ref(ref):
            rejected.append(
                f"{ref} is an ISO/IEC 27001:2013 identifier. The 2022 edition renumbered "
                "Annex A into four themes and has no control with that reference; the "
                "suggestion was dropped."
            )
        elif guardrails.looks_like_an_internal_control_id(original):
            rejected.append(
                f"{original[:60]} is an identifier from FinFlow's own control library, "
                "not an Annex A reference. The model was shown both and conflated them; "
                "the suggestion was dropped."
            )
        else:
            rejected.append(
                f"{original[:60]} is not an ISO/IEC 27001:2022 Annex A control "
                "identifier; the suggestion was dropped."
            )
    return known, rejected


def check_record_refs(
    cited: list[str], supplied: set[str]
) -> tuple[list[str], list[str]]:
    """Split cited record references into ones the model was shown and ones it was not.

    The same idea as the Annex A catalogue check, applied to the sweep. A contradiction
    is only worth anything if the analyst can go and read the two records; a citation to
    a record that was never supplied is a fabrication, and it is the failure mode that
    would do the most damage here -- an invented disagreement between two real-sounding
    references reads exactly like a real one.
    """
    known: list[str] = []
    rejected: list[str] = []
    for raw in cited:
        ref = raw.strip().upper()
        if ref in supplied:
            known.append(ref)
        else:
            rejected.append(raw.strip()[:60])
    return known, rejected


# --- Wiring -------------------------------------------------------------------


@lru_cache
def get_ai_service() -> AIService:
    """The production service, as a FastAPI dependency.

    Cached because the provider is stateless and the status cache should be shared
    across requests. Tests replace it through ``dependency_overrides`` rather than by
    monkeypatching a module global, which keeps the substitution visible in the test.
    """
    settings = get_settings()
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout=settings.ollama_timeout,
        structured_output=settings.ai_structured_output,
        num_ctx=settings.ollama_num_ctx,
    )
    return AIService(provider, settings)
