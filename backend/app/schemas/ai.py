"""Request and response shapes for the assistant endpoints.

Requests are small on purpose. Every one of them names a record that already exists, or
a topic and a document type. There is no field anywhere in this file that carries a
system prompt, a template, a model name, a temperature or any other generation
parameter, because an endpoint that accepted one would be an endpoint through which a
user could rewrite the assistant's instructions.

The single free-text field is ``question``, it is bounded, and it arrives in the user
message labelled as a question about the record rather than as an instruction.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings
from app.models.ai import AiFeature, AiInteractionStatus
from app.services.ai.response import (
    ConsistencySweepSuggestion,
    ControlMappingSuggestion,
    ControlTestSuggestion,
    FindingDraftSuggestion,
    PolicyDraftSuggestion,
    RemediationSuggestion,
    RiskAssistSuggestion,
    RiskDescriptionSuggestion,
)

_settings = get_settings()
MAX_QUESTION_CHARS = _settings.ai_max_question_chars
MAX_TOPIC_CHARS = 200
MAX_DRAFT_FIELD_CHARS = 1_000


class _In(BaseModel):
    """Reject unknown keys outright.

    ``extra="forbid"`` is doing real work on an AI endpoint. A silently ignored extra
    field is how a request grows a ``system_prompt`` that somebody assumes is honoured;
    a 422 makes the answer to "can I pass my own prompt?" unambiguous.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class QuestionMixin(_In):
    question: str | None = Field(default=None, max_length=MAX_QUESTION_CHARS)

    @field_validator("question")
    @classmethod
    def blank_is_none(cls, value: str | None) -> str | None:
        return value or None


# --- Requests ------------------------------------------------------------------


class RiskAssistIn(QuestionMixin):
    risk_ref: str = Field(min_length=3, max_length=16)


class RiskDescriptionIn(QuestionMixin):
    """Either point at an existing risk, or supply the analysis directly.

    Both paths exist because the assistant is useful at two different moments: while
    drafting a new risk that is not in the register yet, and while tightening the
    wording of one that is.
    """

    risk_ref: str | None = Field(default=None, max_length=16)
    asset: str | None = Field(default=None, max_length=MAX_DRAFT_FIELD_CHARS)
    threat: str | None = Field(default=None, max_length=MAX_DRAFT_FIELD_CHARS)
    vulnerability: str | None = Field(default=None, max_length=MAX_DRAFT_FIELD_CHARS)
    event: str | None = Field(default=None, max_length=MAX_DRAFT_FIELD_CHARS)
    impact: str | None = Field(default=None, max_length=MAX_DRAFT_FIELD_CHARS)

    @field_validator("risk_ref")
    @classmethod
    def blank_ref_is_none(cls, value: str | None) -> str | None:
        return value or None

    def has_free_text(self) -> bool:
        return any([self.asset, self.threat, self.vulnerability, self.event, self.impact])


class ControlMappingIn(QuestionMixin):
    risk_ref: str = Field(min_length=3, max_length=16)


class ControlTestAssistIn(QuestionMixin):
    test_ref: str = Field(min_length=3, max_length=24)


class FindingDraftIn(QuestionMixin):
    test_ref: str = Field(min_length=3, max_length=24)


class RemediationAssistIn(QuestionMixin):
    finding_ref: str = Field(min_length=3, max_length=24)


class ConsistencySweepIn(QuestionMixin):
    control_id: str = Field(min_length=2, max_length=24)


class PolicyDocumentType(str, Enum):
    POLICY = "POLICY"
    PROCEDURE = "PROCEDURE"
    CONTROL_DESCRIPTION = "CONTROL_DESCRIPTION"
    EVIDENCE_REQUEST = "EVIDENCE_REQUEST"
    COMPLIANCE_QUESTIONNAIRE = "COMPLIANCE_QUESTIONNAIRE"


class PolicyDraftIn(QuestionMixin):
    document_type: PolicyDocumentType
    topic: str = Field(min_length=3, max_length=MAX_TOPIC_CHARS)
    # Bounded, and checked against the seeded catalogue before use. An unbounded list
    # here would be a way to inflate the prompt from the client side.
    annex_a_refs: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("annex_a_refs")
    @classmethod
    def refs_are_short(cls, value: list[str]) -> list[str]:
        for ref in value:
            if len(ref) > 24:
                raise ValueError("An Annex A reference cannot be longer than 24 characters.")
        return value


# --- Responses -----------------------------------------------------------------


class ContextItemOut(BaseModel):
    """One line of "here is what the model was shown"."""

    model_config = ConfigDict(from_attributes=True)

    label: str
    value: str


class AiEnvelope(BaseModel):
    """The wrapper every assistant response carries.

    ``advisory`` and ``requires_human_review`` are constants, not values the model can
    influence. There is no code path that sets either of them to false, and a test
    asserts it. If a future version ever wanted an authoritative AI answer, the change
    would have to be made here in the open rather than emerging from a prompt.
    """

    feature: AiFeature
    advisory: bool = True
    requires_human_review: bool = True
    label: str
    note: str
    provider: str
    model: str
    generated_at: datetime
    latency_ms: int
    entity_type: str | None = None
    entity_ref: str | None = None
    # What the model was given. This is the explainability contract: a reader can see
    # the inputs, the output, and that a human still has to sign it.
    context_provided: list[ContextItemOut]
    guardrail_notes: list[str] = Field(default_factory=list)
    interaction_ref: str | None = None


class RiskAssistOut(AiEnvelope):
    suggestion: RiskAssistSuggestion


class RiskDescriptionOut(AiEnvelope):
    suggestion: RiskDescriptionSuggestion


class ResolvedControlOut(BaseModel):
    """A suggested control, checked against the catalogue and the current SoA.

    The SoA fields are why this is more useful than the model's raw list: a suggestion
    to consider a control that is already applicable, already implemented and already
    linked to this risk is not a suggestion, it is a restatement.
    """

    control_ref: str
    title: str
    reason: str
    already_linked: bool
    soa_applicable: bool | None = None
    soa_implementation_status: str | None = None


class ControlMappingOut(AiEnvelope):
    suggestion: ControlMappingSuggestion
    resolved_controls: list[ResolvedControlOut]
    # Identifiers the model produced that are not in ISO/IEC 27001:2022 Annex A, with
    # the reason each was dropped. Reported rather than hidden: an assistant that cites
    # a 2013 control number is telling you something about how far to trust the rest.
    rejected_controls: list[str] = Field(default_factory=list)


class ControlTestAssistOut(AiEnvelope):
    suggestion: ControlTestSuggestion


class FindingDraftOut(AiEnvelope):
    suggestion: FindingDraftSuggestion


class RemediationAssistOut(AiEnvelope):
    suggestion: RemediationSuggestion


class PolicyDraftOut(AiEnvelope):
    suggestion: PolicyDraftSuggestion


class SweepCandidateOut(BaseModel):
    """A control the rules say is worth asking about, and why.

    Computed without the model. The queue costs one query; only the reading costs a
    model call.
    """

    model_config = ConfigDict(from_attributes=True)

    control_id: str
    title: str
    record_count: int
    record_types: list[str]
    reasons: list[str]


class ConsistencySweepOut(AiEnvelope):
    suggestion: ConsistencySweepSuggestion
    # References the model cited that it was never shown. Reported rather than hidden:
    # an invented disagreement between two real-sounding records is the worst thing this
    # feature could produce, so it is named when it happens.
    uncited_records: list[str] = Field(default_factory=list)
    records_compared: list[str] = Field(default_factory=list)


class AiStatusOut(BaseModel):
    """What the status chip renders.

    ``reachable`` and ``model_available`` stay separate all the way to the UI because
    they need different sentences: "start Ollama" and "pull the model" are different
    instructions and a single boolean would give neither.
    """

    enabled: bool
    ready: bool
    provider: str
    configured_model: str
    reachable: bool
    model_available: bool
    detail: str
    available_models: list[str] = Field(default_factory=list)
    version: str | None = None
    host_is_local: bool
    checked_at: datetime
    # Restated on the status endpoint so anything that polls it, including a monitor,
    # sees the guarantee rather than having to know it.
    core_functionality_requires_ai: bool = False


class AiInteractionOut(BaseModel):
    """One row of the interaction log.

    No prompt, no response text, by design -- see the docstring on the model. The
    digest is what ties a suggestion someone kept back to the interaction.
    """

    model_config = ConfigDict(from_attributes=True)

    interaction_ref: str
    created_at: datetime
    username: str
    user_role: str
    feature: AiFeature
    entity_type: str | None
    entity_ref: str | None
    provider: str
    model: str
    status: AiInteractionStatus
    latency_ms: int | None
    prompt_chars: int
    response_chars: int | None
    response_digest: str | None
    guardrail_flags: str | None
    error_note: str | None


class AiInteractionSummaryOut(BaseModel):
    total: int
    by_status: dict[str, int]
    by_feature: dict[str, int]
    with_guardrail_flags: int
    first_recorded: date | None = None
    last_recorded: date | None = None
