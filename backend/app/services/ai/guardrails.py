"""What goes in, and what comes back.

Two directions, two different problems.

**Inbound.** Record content is untrusted input to a model. A risk description, a piece
of evidence detail or an exception note is free text that somebody typed, and "somebody
typed it" is exactly the property a prompt injection needs. The defence here is not to
sanitise the text into safety — that is a losing game — but to structure the prompt so
that the model is told, before it ever sees the data, what the data is and what it is
not. Record content is fenced, labelled and never concatenated into the instruction
section. The system prompt is assembled server-side and no request field reaches it.

**Outbound.** A model will, given the chance, tell you a control is effective, a policy
is compliant, or that ISO 27001 requires a particular sentence. On a GRC platform those
are not stylistic problems; they are the exact claims the rest of this application
refuses to let a human make without evidence. So the model's output is run through the
same kind of rule the SoA justifications are: patterns that assert compliance,
certification, or a test verdict are flagged, and the flags travel with the suggestion
to the analyst and into the interaction log.

Flagged, not silently removed. Deleting the sentence would hide that the model produced
it; showing it with a flag attached tells the analyst exactly what to distrust.
"""

import re

# Field names whose values must never leave the database in a prompt. Applied by the
# context builders as a belt-and-braces check on top of explicit field whitelisting --
# the whitelist is the control, this is the assertion that the control worked.
FORBIDDEN_KEYS = frozenset(
    {
        "hashed_password",
        "password",
        "jwt_secret",
        "secret",
        "token",
        "access_token",
        "api_key",
        "apikey",
        "database_url",
        "dsn",
        "private_key",
        "credential",
        "credentials",
    }
)

# The fence around record content. Chosen to be something no GRC record would contain
# by accident, and stripped out of the content itself so a record cannot close its own
# fence and escape into the instruction section.
FENCE_OPEN = "<<<GRC-RECORD-DATA"
FENCE_CLOSE = "GRC-RECORD-DATA>>>"

_FENCE_LOOKALIKE = re.compile(r"<<<\s*GRC-RECORD-DATA|GRC-RECORD-DATA\s*>>>", re.IGNORECASE)

# Claims a GRC platform must never let a model make on the organisation's behalf.
# Each pattern maps to the flag reported to the analyst.
_FORBIDDEN_CLAIMS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        # Broad on the verb, narrow on the negation. "makes FinFlow fully compliant" and
        # "brings the organisation into compliance" are the same overclaim as "is
        # compliant", and the first phrasing is the one a model actually reaches for.
        # "is not compliant" is a different sentence and is deliberately left alone: the
        # bounded word gap cannot bridge the "not", so the negative form does not match.
        re.compile(
            r"\b(?:(?:is|are|was|were|becomes?|remains?|will be)\s+"
            r"|(?:makes?|renders?)\s+(?:\w+\s+){0,4}"
            r"|brings?\s+(?:\w+\s+){0,4}into\s+)"
            r"(?:now\s+)?(?:fully\s+)?complian(?:t|ce)\b"
            r"|\bachieves? compliance\b"
            r"|\bensur\w+ compliance\b",
            re.I,
        ),
        "asserted-compliance",
    ),
    (
        re.compile(r"\b(?:is|are) certified\b|\bcertification (?:is )?(?:achieved|granted)\b", re.I),
        "asserted-certification",
    ),
    (
        re.compile(
            r"\biso[ /]?(?:iec)?[ ]?27001 requires (?:this|the following|that you use) "
            r"(?:exact )?wording\b",
            re.I,
        ),
        "asserted-required-wording",
    ),
    (
        re.compile(r"\bthe control (?:is|was) (?:operating )?effective\b", re.I),
        "asserted-control-effectiveness",
    ),
    (
        re.compile(r"\bthis (?:test|control) (?:passes|passed|fails|failed)\b", re.I),
        "asserted-test-conclusion",
    ),
    (
        re.compile(r"\bresidual (?:risk )?score (?:should be|is now) \d+\b", re.I),
        "asserted-risk-score",
    ),
    (
        re.compile(r"\b(?:i have|we have) (?:verified|confirmed|tested)\b", re.I),
        "claimed-verification",
    ),
    (
        re.compile(r"\baudit(?:ed|or) (?:has )?(?:confirmed|signed off|approved)\b", re.I),
        "claimed-audit-signoff",
    ),
)

# Annex A control identifiers, ISO/IEC 27001:2022 shape: A.<theme 5-8>.<1-2 digits>.
# The 2013 edition used a third level (A.9.4.2) and models reach for it constantly,
# because there is far more 2013 text in the world than 2022 text. A suggestion citing
# a 2013 identifier is not a small formatting slip: it is a citation to a control that
# no longer exists under that number, and an auditor will notice immediately.
_ANNEX_A_2022 = re.compile(r"^A\.[5-8]\.\d{1,2}$")
_ANNEX_A_2013 = re.compile(r"^A\.\d{1,2}\.\d{1,2}\.\d{1,2}$")

# Models return the identifier glued to the title -- "A.8.18: Use of privileged utility
# programs" -- far more often than they return it clean. That is a formatting slip, not
# a wrong answer, and throwing away a correct control over it would be the tooling
# being pedantic at the analyst's expense. The identifier is lifted out instead.
_ANNEX_A_TOKEN = re.compile(r"\bA\.\d{1,2}(?:\.\d{1,2}){1,2}\b")

# The FinFlow control library uses AC-002, DP-005, OP-001. A model reading a risk record
# sees those and offers them back as though they were Annex A references. They are not,
# and the refusal is more useful when it says which kind of thing the model confused.
_INTERNAL_CONTROL_ID = re.compile(r"^[A-Z]{2,3}-\d{2,3}\b")


def extract_annex_a_ref(raw: str) -> str:
    """Lift an Annex A identifier out of whatever the model actually wrote."""
    found = _ANNEX_A_TOKEN.search(raw.upper())
    return found.group(0) if found else raw.strip().upper()


def looks_like_an_internal_control_id(raw: str) -> bool:
    return bool(_INTERNAL_CONTROL_ID.match(raw.strip().upper()))


def scrub(payload: dict) -> dict:
    """Remove any forbidden key from a context dictionary, at any depth.

    The context builders never put these in, so this finding anything is a bug worth
    knowing about rather than a routine cleaning step. It is cheap, and the cost of the
    alternative -- a password hash in a prompt -- is not.
    """
    cleaned: dict = {}
    for key, value in payload.items():
        if key.lower() in FORBIDDEN_KEYS:
            continue
        if isinstance(value, dict):
            cleaned[key] = scrub(value)
        elif isinstance(value, list):
            cleaned[key] = [scrub(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value
    return cleaned


def neutralise(text: str | None, *, max_chars: int) -> str:
    """Prepare one field of record content for inclusion in a prompt.

    Does exactly two things, and deliberately nothing else:

    1. Breaks any text that imitates the data fence, so a record cannot close the fence
       and continue as if it were instructions.
    2. Truncates, so one pathological field cannot consume the whole context window.

    It does **not** try to detect or strip instruction-like language. "Ignore all
    previous instructions" is legitimate content for a risk description about prompt
    injection, and a filter that removed it would corrupt the record while still
    missing the next phrasing. The defence is the prompt structure, not the filter.
    """
    if not text:
        return ""
    cleaned = _FENCE_LOOKALIKE.sub("[fence-marker removed]", str(text))
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + f"… [truncated at {max_chars} characters]"
    return cleaned


def fence(label: str, body: str) -> str:
    """Wrap record content in a labelled data fence."""
    return f"{FENCE_OPEN} label=\"{label}\"\n{body}\n{FENCE_CLOSE}"


def forbidden_claim_flags(text: str) -> list[str]:
    """Which output guardrails a model response tripped. Empty is the normal case."""
    return sorted({flag for pattern, flag in _FORBIDDEN_CLAIMS if pattern.search(text)})


def is_annex_a_2022_ref(ref: str) -> bool:
    """Shape check only. Whether the identifier actually exists is a database question,
    answered against the seeded 93-row catalogue rather than a regular expression."""
    return bool(_ANNEX_A_2022.match(ref.strip()))


def looks_like_annex_a_2013_ref(ref: str) -> bool:
    """A three-level identifier is a 2013 citation, and worth naming as such."""
    return bool(_ANNEX_A_2013.match(ref.strip()))
