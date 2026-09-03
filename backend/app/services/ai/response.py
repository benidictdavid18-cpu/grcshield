"""The shapes a model is allowed to answer in.

Two jobs.

**Constrain the request.** Each of these models is turned into a JSON schema and handed
to Ollama as the `format`, so generation is constrained to the shape rather than merely
asked for it. That is the difference between "please reply in JSON" and a grammar.

**Constrain the answer.** Whatever comes back is parsed and validated against the same
model before anything reaches the API layer. A field the model invented is dropped; a
field it omitted fails validation. Malformed output raises ``InvalidAiResponse``, which
the route turns into a 502 with a readable message -- never a 500, and never a partially
parsed suggestion rendered as if it were whole.

**What is absent is the point.** Look for a field on any of these models that carries a
likelihood, an impact, a score, a band, a conclusion, a design or operating
effectiveness rating, an approval or an acceptance. There is none, in any of them, by
construction. The assistant has no vocabulary in which to express a GRC decision, so it
cannot make one -- not as a matter of prompt discipline, but as a matter of the schema
it is required to answer in. ``test_no_ai_response_model_can_express_a_grc_decision``
walks every field of every model in this file and fails the build if one appears.
"""

import json
import re
from enum import Enum
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict, Field

from app.services.ai.provider import InvalidAiResponse

# Bounds on every list a model returns. A suggestion list of forty items is not more
# helpful than one of six; it is a wall of text an analyst will skim and stop trusting.
MAX_ITEMS = 8
MAX_ITEM_CHARS = 600
MAX_TEXT_CHARS = 2_000


class Confidence(str, Enum):
    """The model's own account of how sure it is.

    Recorded and displayed, never acted on. A language model's stated confidence is a
    stylistic property of the text it generated, not a measurement, and it must not be
    allowed to look like the effectiveness ratings elsewhere in this application, which
    are backed by tests.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class _Base(BaseModel):
    # Extra keys are dropped rather than rejected: a model that adds a field has not
    # failed the task, and failing the whole request over it would trade a usable
    # suggestion for a pedantic error.
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class Suggestion(_Base):
    """Fields every assistant returns, whatever it was asked."""

    summary: str = Field(default="", max_length=MAX_TEXT_CHARS)
    observations: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    suggestions: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    # The anti-hallucination field. A model told to answer "insufficient information
    # available" has somewhere to put that answer, which makes it far likelier to give
    # it than a model whose only option is to fill the space with something.
    missing_information: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    confidence: Confidence = Confidence.MEDIUM


class RiskAssistSuggestion(Suggestion):
    threat_scenarios: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    vulnerabilities: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    # Areas, not verdicts. "Consider access control and logging" is help; "A.8.5 is
    # applicable" is a Statement of Applicability decision the analyst makes.
    control_areas: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    questions_to_investigate: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    treatment_options: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)


class RiskDescriptionSuggestion(Suggestion):
    """A risk statement in the house structure: threat, vulnerability, event, impact.

    Four fields rather than one paragraph, because the structure is the value. A risk
    written as one sentence hides which part of it the analyst actually assessed.
    """

    threat: str = Field(default="", max_length=MAX_ITEM_CHARS)
    vulnerability: str = Field(default="", max_length=MAX_ITEM_CHARS)
    event: str = Field(default="", max_length=MAX_ITEM_CHARS)
    impact: str = Field(default="", max_length=MAX_ITEM_CHARS)
    risk_statement: str = Field(default="", max_length=MAX_TEXT_CHARS)


class SuggestedControl(_Base):
    control: str = Field(default="", max_length=24)
    reason: str = Field(default="", max_length=MAX_ITEM_CHARS)


class ControlMappingSuggestion(Suggestion):
    suggested_controls: list[SuggestedControl] = Field(
        default_factory=list, max_length=MAX_ITEMS
    )


class ControlTestSuggestion(Suggestion):
    evidence_summary: str = Field(default="", max_length=MAX_TEXT_CHARS)
    possible_exceptions: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    missing_evidence: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    why_it_might_matter: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    additional_testing: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)


class FindingDraftSuggestion(Suggestion):
    """The classic audit finding structure, minus the verdict.

    Condition, criteria, cause and effect are how a finding is written. Severity is
    absent on purpose: severity drives remediation priority and due dates, and it is a
    judgment the auditor signs.
    """

    draft_title: str = Field(default="", max_length=240)
    condition: str = Field(default="", max_length=MAX_TEXT_CHARS)
    criteria: str = Field(default="", max_length=MAX_TEXT_CHARS)
    risk_and_impact: str = Field(default="", max_length=MAX_TEXT_CHARS)
    possible_root_causes: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    suggested_remediation_language: str = Field(default="", max_length=MAX_TEXT_CHARS)


class RemediationSuggestion(Suggestion):
    """Correction and corrective action are separate fields because they are separate
    things. ISO/IEC 27001:2022 Clause 10.2 asks for both: the correction fixes the
    instance, the corrective action addresses the cause so it does not recur. A model
    given one field for both will write the correction and call it done."""

    correction: str = Field(default="", max_length=MAX_TEXT_CHARS)
    corrective_action: str = Field(default="", max_length=MAX_TEXT_CHARS)
    root_cause_questions: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    remediation_steps: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    evidence_required_to_close: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    # A role, never a person, and never a date. Assigning an owner and a deadline is
    # the act that makes remediation real, and it belongs to the business.
    suggested_owner_role: str = Field(default="", max_length=120)
    priority_rationale: str = Field(default="", max_length=MAX_ITEM_CHARS)


class PolicySection(_Base):
    heading: str = Field(default="", max_length=200)
    body: str = Field(default="", max_length=MAX_TEXT_CHARS)


class PolicyDraftSuggestion(Suggestion):
    document_title: str = Field(default="", max_length=240)
    purpose: str = Field(default="", max_length=MAX_TEXT_CHARS)
    scope: str = Field(default="", max_length=MAX_TEXT_CHARS)
    sections: list[PolicySection] = Field(default_factory=list, max_length=MAX_ITEMS)
    open_questions: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)


# --- Parsing -------------------------------------------------------------------

_FENCED = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> dict[str, Any]:
    """Pull an object out of a model response, tolerantly but not credulously.

    Constrained generation makes this the uncommon path, but "uncommon" is not "never":
    an older Ollama, a model that ignores the grammar, a thinking model that leaks its
    preamble. Three attempts, in order of how much benefit of the doubt each extends --
    the whole body, a fenced block, then the outermost braces. If none parses, the
    response is not usable and saying so is better than guessing.
    """
    candidates: list[str] = []
    stripped = text.strip()
    if stripped:
        candidates.append(stripped)

    fenced = _FENCED.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())

    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed

    preview = stripped[:160].replace("\n", " ")
    raise InvalidAiResponse(
        "The model did not return a JSON object. This usually means the configured "
        f"model ignores structured output. First characters received: '{preview}'"
    )


def parse(text: str, model_type: type[Suggestion]) -> Suggestion:
    """Extract, trim to the declared bounds, then validate.

    The order matters and was got wrong first time. Validating before trimming means a
    model that returned twelve observations instead of eight fails the whole request,
    and the analyst gets an error where a perfectly usable answer was available. Length
    limits exist to bound what is rendered, not to adjudicate whether a suggestion was
    worth having, so they are applied as trimming and only then validated.

    What is *not* softened: a response that is not a JSON object, or that is missing
    the structure entirely. That is a failure, and it raises.
    """
    payload = extract_json(text)
    coerced = _coerce(payload, model_type)
    try:
        return model_type.model_validate(coerced)
    except Exception as exc:  # pydantic.ValidationError, and anything it wraps
        raise InvalidAiResponse(
            f"The model's response did not match the expected structure: {exc}"
        ) from exc


def _declared_max_length(model_type: type[BaseModel], name: str) -> int | None:
    """The max_length a field declares, read off the Pydantic field metadata."""
    info = model_type.model_fields.get(name)
    if info is None:
        return None
    for constraint in info.metadata:
        value = getattr(constraint, "max_length", None)
        if isinstance(value, int):
            return value
    return None


def _item_model(annotation) -> type[BaseModel] | None:
    """The element type of a ``list[SomeModel]`` annotation, if it is one."""
    for arg in get_args(annotation):
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


def _coerce(payload: dict[str, Any], model_type: type[BaseModel]) -> dict[str, Any]:
    """Bring an over-generous response inside the declared bounds.

    Trims list length to what the field allows, string length to what the field allows,
    and recurses into nested objects so a long ``reason`` on one suggested control does
    not fail the other seven. Unknown keys are left alone; ``extra="ignore"`` drops them
    a moment later.
    """
    coerced: dict[str, Any] = {}
    for key, value in payload.items():
        info = model_type.model_fields.get(key)
        if info is None:
            coerced[key] = value
            continue

        cap = _declared_max_length(model_type, key)
        if isinstance(value, list):
            nested = _item_model(info.annotation)
            trimmed = value[: cap or MAX_ITEMS]
            items: list[Any] = []
            for item in trimmed:
                if isinstance(item, str):
                    items.append(item[:MAX_ITEM_CHARS])
                elif isinstance(item, dict) and nested is not None:
                    items.append(_coerce(item, nested))
                else:
                    items.append(item)
            coerced[key] = items
        elif isinstance(value, str) and cap:
            coerced[key] = value[:cap]
        else:
            coerced[key] = value

    # A model's self-reported confidence is decorative -- it is displayed and never
    # acted on -- so an unrecognised value drops back to the default rather than
    # failing a suggestion whose substance is fine.
    confidence = coerced.get("confidence")
    if confidence is not None and confidence not in {c.value for c in Confidence}:
        coerced.pop("confidence")

    return coerced


def json_schema_for(model_type: type[Suggestion]) -> dict[str, Any]:
    """The schema handed to Ollama as the generation format."""
    return model_type.model_json_schema()
