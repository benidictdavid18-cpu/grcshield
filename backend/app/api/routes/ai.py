"""Assistant endpoints.

**Authorisation.** This router is mounted with ``current_user`` and not with
``require_write``, and that is a deliberate decision rather than an oversight.

``require_write`` refuses a mutating request from a read-only role, and it identifies
"mutating" by HTTP method. That heuristic is right for every other router in this
application, because every non-GET route in them writes to a register. It is wrong
here. These endpoints are POSTs for an unglamorous reason -- a risk record does not fit
in a query string -- and not one of them can change a GRC record: there is no code path
from this file to a register write, the response schemas have no field capable of
expressing a decision, and a test asserts both.

Applying a write control to a read operation would not make the system safer. It would
teach the reader that POST means mutation, which is the exact confusion this feature
has to avoid. So the two enforcement points stand as documented: every route here
requires a valid token, and none of them requires a write role, because none of them
writes. A read-only auditor asking an assistant to summarise a workpaper is the read-
only use case, not an exception to it.

**Status codes.** An assistant that is unavailable is an ordinary condition, not a
server fault:

    503  the assistant is disabled, the model server is down, or it timed out
    502  the model answered with something that is not the requested structure
    404  the record named in the request does not exist
    422  the request itself is malformed or oversized

None of them is a 500, and none of them affects any other endpoint.
"""

from collections import Counter
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models.ai import AiFeature, AiInteraction
from app.models.soa import SoAEntry
from app.models.user import User
from app.schemas.ai import (
    AiEnvelope,
    AiInteractionOut,
    AiInteractionSummaryOut,
    AiStatusOut,
    ContextItemOut,
    ControlMappingIn,
    ControlMappingOut,
    ControlTestAssistIn,
    ControlTestAssistOut,
    FindingDraftIn,
    FindingDraftOut,
    PolicyDraftIn,
    PolicyDraftOut,
    RemediationAssistIn,
    RemediationAssistOut,
    ResolvedControlOut,
    RiskAssistIn,
    RiskAssistOut,
    RiskDescriptionIn,
    RiskDescriptionOut,
)
from app.services.ai import context as ai_context
from app.services.ai.provider import (
    AiDisabled,
    AiUnavailable,
    InvalidAiResponse,
)
from app.services.ai.response import (
    ControlMappingSuggestion,
    ControlTestSuggestion,
    FindingDraftSuggestion,
    PolicyDraftSuggestion,
    RemediationSuggestion,
    RiskAssistSuggestion,
    RiskDescriptionSuggestion,
    Suggestion,
)
from app.services.ai.service import (
    ADVISORY_LABEL,
    ADVISORY_NOTE,
    AIService,
    AiResult,
    check_control_refs,
    get_ai_service,
    normalise_control_ref,
)

router = APIRouter(prefix="/ai", tags=["ai"])


# --- Status --------------------------------------------------------------------


@router.get("/status", response_model=AiStatusOut)
def ai_status(
    refresh: bool = Query(default=False),
    service: AIService = Depends(get_ai_service),
) -> AiStatusOut:
    """Whether the assistant can answer, and if not, what to do about it.

    Answers from a cached probe. The chip that renders this sits in the masthead of
    every page, and probing a model server on every page load would be self-inflicted
    load dressed up as monitoring.
    """
    probed = service.status(force=refresh)
    return AiStatusOut(
        enabled=probed.enabled,
        ready=probed.ready,
        provider=probed.provider,
        configured_model=probed.configured_model,
        reachable=probed.reachable,
        model_available=probed.model_available,
        detail=probed.detail,
        available_models=list(probed.available_models),
        version=probed.version,
        host_is_local=probed.host_is_local,
        checked_at=probed.checked_at,
    )


# --- Shared plumbing ------------------------------------------------------------


def _run(
    service: AIService,
    db: Session,
    user: User,
    *,
    feature: AiFeature,
    record_context: ai_context.RecordContext,
    response_type: type[Suggestion],
    question: str | None,
) -> AiResult:
    """Call the service and translate its failures into honest status codes."""
    try:
        return service.generate(
            db,
            username=user.username,
            user_role=user.role.value,
            feature=feature,
            context=record_context,
            response_type=response_type,
            question=question,
        )
    except AiDisabled as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except AiUnavailable as exc:
        # Covers a stopped Ollama, a missing model and a timeout. Every one of them
        # means the same thing to the caller, and none of them is this service's fault.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except InvalidAiResponse as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _envelope(result: AiResult) -> dict:
    return {
        "feature": result.feature,
        "advisory": True,
        "requires_human_review": True,
        "label": ADVISORY_LABEL,
        "note": ADVISORY_NOTE,
        "provider": result.provider,
        "model": result.model,
        "generated_at": result.generated_at,
        "latency_ms": result.latency_ms,
        "context_provided": [
            ContextItemOut(label=item.label, value=item.value) for item in result.context_items
        ],
        "guardrail_notes": result.guardrail_notes,
        "interaction_ref": result.interaction_ref,
    }


def _not_found(exc: ai_context.ContextNotFound) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Risk ----------------------------------------------------------------------


@router.post("/risk-assist", response_model=RiskAssistOut)
def risk_assist(
    payload: RiskAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> RiskAssistOut:
    """Think out loud about a risk that is already in the register.

    Nothing this returns is written anywhere. Likelihood, impact, the residual
    justification, the treatment decision and the appetite comparison are untouched by
    this call and untouchable from it.
    """
    try:
        record = ai_context.risk_context(db, payload.risk_ref)
    except ai_context.ContextNotFound as exc:
        raise _not_found(exc)

    result = _run(
        service,
        db,
        user,
        feature=AiFeature.RISK_ASSIST,
        record_context=record,
        response_type=RiskAssistSuggestion,
        question=payload.question,
    )
    return RiskAssistOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=result.suggestion,
    )


@router.post("/risk-description", response_model=RiskDescriptionOut)
def risk_description(
    payload: RiskDescriptionIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> RiskDescriptionOut:
    """Draft a risk statement as threat, vulnerability, event and impact.

    The draft is returned, not saved. Writing it into the register is a separate,
    deliberate act by the analyst through the endpoints that already validate it.
    """
    if payload.risk_ref:
        try:
            record = ai_context.risk_context(db, payload.risk_ref)
        except ai_context.ContextNotFound as exc:
            raise _not_found(exc)
    elif payload.has_free_text():
        record = _draft_context(payload)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Supply either risk_ref, to rework an existing risk, or at least one of "
                "asset, threat, vulnerability, event or impact to draft a new one. "
                "There is nothing to write a risk statement from otherwise."
            ),
        )

    result = _run(
        service,
        db,
        user,
        feature=AiFeature.RISK_DESCRIPTION,
        record_context=record,
        response_type=RiskDescriptionSuggestion,
        question=payload.question,
    )
    return RiskDescriptionOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=result.suggestion,
    )


def _draft_context(payload: RiskDescriptionIn) -> ai_context.RecordContext:
    """Context for a risk that does not exist yet.

    Analyst-supplied text, which is why it goes through the same fencing as anything
    read out of the database. It arrived over HTTP; that it came from a signed-in
    analyst rather than a database row does not make it an instruction.
    """
    body = "\n".join(
        f"{label}: {value}"
        for label, value in (
            ("Asset at risk", payload.asset),
            ("Threat", payload.threat),
            ("Vulnerability", payload.vulnerability),
            ("Event", payload.event),
            ("Impact", payload.impact),
        )
        if value
    )
    return ai_context.RecordContext(
        entity_type=None,
        entity_ref=None,
        headline="New risk, not yet in the register",
        items=[
            ai_context.ContextItem("Source", "Draft supplied by the analyst; not yet a record"),
            ai_context.ContextItem("Organisation", "FinFlow Technologies, from the ISMS scope"),
        ],
        sections={
            "draft analysis supplied by the analyst": body,
            "the organisation this risk belongs to": ai_context.ORGANISATION_PROFILE,
        },
    )


@router.post("/control-mapping", response_model=ControlMappingOut)
def control_mapping(
    payload: ControlMappingIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> ControlMappingOut:
    """Suggest Annex A controls to consider for a risk.

    Two things happen that a bare model call would not do. The real 93-row catalogue is
    supplied in the prompt, so the model selects rather than recalls; and every
    identifier it returns is then checked back against that catalogue, so anything it
    invented -- classically a 2013 identifier like A.9.4.2 -- is dropped and reported
    rather than shown next to the real ones.

    A suggestion is not an applicability decision. Marking a control applicable, with a
    justification that survives ``soa_validation``, remains the analyst's act.
    """
    try:
        record, catalogue = ai_context.control_mapping_context(db, payload.risk_ref)
        risk = ai_context.load_risk(db, payload.risk_ref)
    except ai_context.ContextNotFound as exc:
        raise _not_found(exc)

    result = _run(
        service,
        db,
        user,
        feature=AiFeature.CONTROL_MAPPING,
        record_context=record,
        response_type=ControlMappingSuggestion,
        question=payload.question,
    )

    suggestion: ControlMappingSuggestion = result.suggestion  # type: ignore[assignment]
    proposed = [item.control for item in suggestion.suggested_controls]
    known, rejected = check_control_refs(proposed, catalogue)

    already_linked = {ref for link in risk.control_links for ref in link.control.annex_a_refs}
    soa_rows = (
        {row.control_ref: row for row in db.scalars(select(SoAEntry).where(SoAEntry.control_ref.in_(known)))}
        if known
        else {}
    )

    resolved: list[ResolvedControlOut] = []
    seen: set[str] = set()
    for item in suggestion.suggested_controls:
        # Same normalisation the checker used, so a suggestion cannot pass one and
        # fail the other.
        ref = normalise_control_ref(item.control)
        if ref not in catalogue or ref in seen:
            continue
        seen.add(ref)
        entry = soa_rows.get(ref)
        resolved.append(
            ResolvedControlOut(
                control_ref=ref,
                title=catalogue[ref],
                reason=item.reason,
                already_linked=ref in already_linked,
                soa_applicable=entry.applicable if entry else None,
                soa_implementation_status=(
                    entry.implementation_status.value if entry else None
                ),
            )
        )

    # The suggestion object is returned with the invented identifiers already removed,
    # so a client that renders it directly cannot show one by accident.
    filtered = suggestion.model_copy(
        update={
            "suggested_controls": [
                item.model_copy(update={"control": normalise_control_ref(item.control)})
                for item in suggestion.suggested_controls
                if normalise_control_ref(item.control) in catalogue
            ]
        }
    )

    return ControlMappingOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=filtered,
        resolved_controls=resolved,
        rejected_controls=rejected,
    )


# --- Control testing, findings, remediation -------------------------------------


@router.post("/control-test-assist", response_model=ControlTestAssistOut)
def control_test_assist(
    payload: ControlTestAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> ControlTestAssistOut:
    """Help review a workpaper.

    The conclusion, the design rating and the operating rating are not in the response
    schema. The assistant can ask whether the recorded conclusion is supportable; it
    cannot record one.
    """
    try:
        record = ai_context.control_test_context(db, payload.test_ref)
    except ai_context.ContextNotFound as exc:
        raise _not_found(exc)

    result = _run(
        service,
        db,
        user,
        feature=AiFeature.CONTROL_TEST_ASSIST,
        record_context=record,
        response_type=ControlTestSuggestion,
        question=payload.question,
    )
    return ControlTestAssistOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=result.suggestion,
    )


@router.post("/finding-draft", response_model=FindingDraftOut)
def finding_draft(
    payload: FindingDraftIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> FindingDraftOut:
    """Draft finding text from a control test.

    The workflow is unchanged: a test concludes, a finding is drafted, a human reviews
    it, and only then is it a finding. This endpoint produces text for the first step
    and returns it. It does not create an ``AuditFinding``, does not set a severity, and
    does not touch the DRAFT status that exists precisely so a person confirms it.
    """
    try:
        record = ai_context.finding_draft_context(db, payload.test_ref)
    except ai_context.ContextNotFound as exc:
        raise _not_found(exc)

    result = _run(
        service,
        db,
        user,
        feature=AiFeature.FINDING_DRAFT,
        record_context=record,
        response_type=FindingDraftSuggestion,
        question=payload.question,
    )
    return FindingDraftOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=result.suggestion,
    )


@router.post("/remediation-assist", response_model=RemediationAssistOut)
def remediation_assist(
    payload: RemediationAssistIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> RemediationAssistOut:
    """Suggest correction, corrective action and what closing would take.

    An owner role is suggested; no owner is assigned. No due date is proposed at all.
    Both of those are agreed with the business, and a date nobody agreed is not a plan.
    """
    try:
        record = ai_context.remediation_context(db, payload.finding_ref)
    except ai_context.ContextNotFound as exc:
        raise _not_found(exc)

    result = _run(
        service,
        db,
        user,
        feature=AiFeature.REMEDIATION_ASSIST,
        record_context=record,
        response_type=RemediationSuggestion,
        question=payload.question,
    )
    return RemediationAssistOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=result.suggestion,
    )


@router.post("/policy-draft", response_model=PolicyDraftOut)
def policy_draft(
    payload: PolicyDraftIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    service: AIService = Depends(get_ai_service),
) -> PolicyDraftOut:
    """Draft a policy, procedure, control description or evidence request.

    Written against FinFlow's actual shape -- fully remote, no premises, one cloud
    region -- because the failure mode of a generic draft is a document that controls
    physical access to data centres for a company that has none.
    """
    record = ai_context.policy_context(
        db,
        topic=payload.topic,
        document_type=payload.document_type.value.replace("_", " ").lower(),
        annex_a_refs=payload.annex_a_refs,
    )
    result = _run(
        service,
        db,
        user,
        feature=AiFeature.POLICY_DRAFT,
        record_context=record,
        response_type=PolicyDraftSuggestion,
        question=payload.question,
    )
    return PolicyDraftOut(
        **_envelope(result),
        entity_type=record.entity_type,
        entity_ref=record.entity_ref,
        suggestion=result.suggestion,
    )


# --- Interaction log ------------------------------------------------------------


@router.get("/interactions", response_model=list[AiInteractionOut])
def list_interactions(
    feature: AiFeature | None = Query(default=None),
    entity_ref: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AiInteractionOut]:
    """The AI activity log, newest first.

    Contains no prompt and no response text. See ``app.models.ai`` for why: every
    prompt is assembled from records already in this database under their own access
    control, and a second copy in a log table would add exposure without adding
    assurance.
    """
    stmt = select(AiInteraction).order_by(AiInteraction.id.desc()).limit(limit)
    if feature is not None:
        stmt = stmt.where(AiInteraction.feature == feature)
    if entity_ref:
        stmt = stmt.where(AiInteraction.entity_ref == entity_ref.strip().upper())
    return [AiInteractionOut.model_validate(row) for row in db.scalars(stmt)]


@router.get("/interactions/summary", response_model=AiInteractionSummaryOut)
def interaction_summary(db: Session = Depends(get_db)) -> AiInteractionSummaryOut:
    rows = db.scalars(select(AiInteraction)).all()
    statuses = Counter(row.status.value for row in rows)
    features = Counter(row.feature.value for row in rows)
    stamps: list[date] = [row.created_at.date() for row in rows if row.created_at]
    return AiInteractionSummaryOut(
        total=len(rows),
        by_status=dict(statuses),
        by_feature=dict(features),
        with_guardrail_flags=sum(1 for row in rows if row.guardrail_flags),
        first_recorded=min(stamps) if stamps else None,
        last_recorded=max(stamps) if stamps else None,
    )


# Imported for the response model union in the OpenAPI schema; keeps the envelope
# discoverable from the generated documentation.
__all__ = ["router", "AiEnvelope"]
