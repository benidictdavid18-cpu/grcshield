"""The provider boundary.

Everything above this line knows it is talking to "a model". Nothing above this line
knows the model is served by Ollama, or that Ollama speaks HTTP, or that its chat
endpoint is ``/api/chat``. That is the whole point of the boundary: swapping in a
different local runtime, or a hosted API if the privacy position ever changes, should
be one new class and one line of wiring, not a search across the codebase.

Failures are typed rather than left as whatever the HTTP client happens to raise,
because the API layer has to distinguish them. "The model server is not running" is a
503 and a calm message; "the model returned something that is not valid JSON" is a 502
and a different message; both are ordinary, and neither is a 500.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class AiError(Exception):
    """Base class for every failure the AI layer raises deliberately."""


class AiUnavailable(AiError):
    """The provider could not be reached, or refused the request.

    Covers a stopped Ollama, a wrong base URL, a model that is not pulled, and a
    connection reset. All of them mean the same thing to a caller: no suggestion is
    available right now, and the rest of the application is unaffected.
    """


class AiTimeout(AiUnavailable):
    """The provider was reachable but did not answer inside the configured timeout.

    A subclass of AiUnavailable so callers that only care about "no answer" need one
    except clause, while the interaction log can still record which of the two it was.
    """


class AiDisabled(AiError):
    """The assistant is switched off by configuration.

    Distinct from unavailable. "Nobody turned it on" and "it is broken" call for
    different messages, and an operator told the wrong one will go looking in the
    wrong place.
    """


class InvalidAiResponse(AiError):
    """The provider answered, but the answer was not the structure we asked for.

    Raised rather than papered over. A model that returns prose where a schema was
    requested has not answered the question, and pretending otherwise would put
    unvalidated text in front of an analyst wearing the same styling as validated text.
    """


@dataclass(frozen=True)
class ProviderStatus:
    """What ``GET /ai/status`` renders.

    ``reachable`` and ``model_available`` are separate because the two failures need
    different fixes: start the server, or pull the model. Collapsing them into one
    boolean produces the unhelpful "AI is broken" that tells an operator nothing.
    """

    provider: str
    configured_model: str
    reachable: bool
    model_available: bool
    detail: str
    available_models: tuple[str, ...] = ()
    version: str | None = None

    @property
    def ready(self) -> bool:
        return self.reachable and self.model_available


@dataclass(frozen=True)
class Completion:
    """One model answer, plus what it cost."""

    text: str
    model: str
    latency_ms: int
    # Whatever the provider reported about its own work. Recorded, never trusted, and
    # never shown to a user as if it meant confidence in the content.
    metadata: dict[str, Any] = field(default_factory=dict)


class AiProvider(ABC):
    """The contract the rest of the application depends on.

    Two methods, because two things are needed: ask the model something, and find out
    whether asking would work at all.
    """

    name: str = "unknown"

    @abstractmethod
    def status(self) -> ProviderStatus:
        """Probe the provider. Must not raise: an unreachable provider is a status,
        not an exception, because this is exactly the call made to find that out."""

    @abstractmethod
    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        """Ask for one completion.

        ``system_prompt`` is always supplied by this application and never by a user.
        ``json_schema``, when given, asks the provider to constrain generation to that
        shape; a provider that cannot do so should fall back to plain JSON mode rather
        than fail, because the response is validated again on the way back regardless.
        """
