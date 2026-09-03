"""The Ollama provider. The only module in the project that knows Ollama exists.

Ollama runs on the analyst's own machine, which is the reason it was chosen: an ISMS is
a catalogue of an organisation's weaknesses, and sending risk descriptions, failed
control tests and DPIA findings to a third-party inference API would be a processing
activity of its own — one that would need a lawful basis, a RoPA entry, a transfer
assessment and a supplier review. Keeping inference local removes the question rather
than answering it.

Local does not mean trusted. Ollama is treated as an external dependency throughout:
bounded timeouts, typed failures, no assumption that the answer is well-formed, and no
assumption that the server is even there.
"""

import json
from typing import Any

import httpx

from app.services.ai.provider import (
    AiProvider,
    AiTimeout,
    AiUnavailable,
    Completion,
    ProviderStatus,
)

# Deterministic-ish settings. This is not creative writing: two analysts asking about
# the same risk minutes apart should not get materially different framings, and a
# suggestion that changes every time is impossible to review.
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9

# The probe used by /ai/status. Cheap, and it answers both questions at once: is the
# server there, and is the configured model among the ones it holds.
_TAGS_PATH = "/api/tags"
_VERSION_PATH = "/api/version"
_CHAT_PATH = "/api/chat"

# Ollama reports models as "name:tag". A model configured without a tag means the
# default tag, which Ollama itself renders as ":latest".
def _normalise_model(name: str) -> str:
    return name if ":" in name else f"{name}:latest"


class OllamaProvider(AiProvider):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout: int,
        structured_output: bool = True,
        num_ctx: int = 8192,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._structured_output = structured_output
        self._num_ctx = num_ctx

    # --- Status ---------------------------------------------------------------

    def status(self) -> ProviderStatus:
        """Never raises. An unreachable provider is the answer, not an error.

        The status probe uses a short timeout of its own rather than the generation
        timeout: waiting sixty seconds to be told the server is down would make the
        indicator worse than useless.
        """
        try:
            with httpx.Client(base_url=self._base_url, timeout=5.0) as client:
                tags = client.get(_TAGS_PATH)
                tags.raise_for_status()
                payload = tags.json()
                version = None
                try:
                    version = client.get(_VERSION_PATH).json().get("version")
                except (httpx.HTTPError, ValueError):
                    # A build too old to expose /api/version is still a working build.
                    version = None
        except httpx.TimeoutException:
            return ProviderStatus(
                provider=self.name,
                configured_model=self._model,
                reachable=False,
                model_available=False,
                detail=(
                    f"Ollama at {self._base_url} did not respond within 5 seconds. "
                    "Core GRC functionality is unaffected."
                ),
            )
        except (httpx.HTTPError, ValueError):
            return ProviderStatus(
                provider=self.name,
                configured_model=self._model,
                reachable=False,
                model_available=False,
                detail=(
                    f"Ollama is not reachable at {self._base_url}. Start it with "
                    "'ollama serve'. Core GRC functionality is unaffected."
                ),
            )

        available = tuple(
            sorted(
                _normalise_model(str(entry.get("model") or entry.get("name") or ""))
                for entry in payload.get("models", [])
                if entry.get("model") or entry.get("name")
            )
        )
        wanted = _normalise_model(self._model)
        model_available = wanted in available

        if model_available:
            detail = f"Connected to Ollama at {self._base_url}. Model {wanted} is available."
        elif available:
            detail = (
                f"Ollama is running, but the configured model '{self._model}' is "
                f"unavailable. Pull it with 'ollama pull {self._model}', or set "
                f"OLLAMA_MODEL to one that is present: {', '.join(available)}."
            )
        else:
            detail = (
                "Ollama is running but holds no models. Pull one with "
                f"'ollama pull {self._model}'."
            )

        return ProviderStatus(
            provider=self.name,
            configured_model=self._model,
            reachable=True,
            model_available=model_available,
            detail=detail,
            available_models=available,
            version=version,
        )

    # --- Generation -----------------------------------------------------------

    def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any] | None = None,
    ) -> Completion:
        body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                # The system message is assembled entirely by this application. There
                # is no code path anywhere that lets a request body reach this field.
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": DEFAULT_TEMPERATURE,
                "top_p": DEFAULT_TOP_P,
                # Explicit, because Ollama's 4096-token default is applied whatever
                # the model supports and truncates a longer prompt in silence. An
                # answer built from a quietly clipped prompt is harder to catch than
                # an error.
                "num_ctx": self._num_ctx,
            },
        }
        if json_schema is not None:
            body["format"] = json_schema if self._structured_output else "json"

        try:
            payload = self._post(body)
        except _SchemaRejected:
            # An older Ollama rejects a JSON-schema 'format'. Plain JSON mode is the
            # documented predecessor and the response is validated again either way,
            # so degrade rather than fail.
            body["format"] = "json"
            payload = self._post(body)

        message = payload.get("message") or {}
        text = str(message.get("content") or "")
        # Thinking models return their scratchpad separately. It is not the answer, it
        # is not shown to anyone, and it is not stored.
        latency_ms = int(payload.get("total_duration", 0) / 1_000_000) or 0

        if not text.strip():
            raise AiUnavailable(
                f"Ollama returned an empty response for model '{self._model}'. "
                "The model may have been unloaded mid-request."
            )

        return Completion(
            text=text,
            model=str(payload.get("model") or self._model),
            latency_ms=latency_ms,
            metadata={
                "done_reason": payload.get("done_reason"),
                "eval_count": payload.get("eval_count"),
                "prompt_eval_count": payload.get("prompt_eval_count"),
            },
        )

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.post(_CHAT_PATH, json=body)
        except httpx.TimeoutException as exc:
            raise AiTimeout(
                f"Ollama did not answer within {self._timeout}s. A larger model on a "
                "cold start can exceed this; raise OLLAMA_TIMEOUT or choose a smaller "
                "model. Core GRC functionality is unaffected."
            ) from exc
        except httpx.HTTPError as exc:
            raise AiUnavailable(
                f"Could not reach Ollama at {self._base_url}: {type(exc).__name__}. "
                "Core GRC functionality is unaffected."
            ) from exc

        if response.status_code == 400 and isinstance(body.get("format"), dict):
            raise _SchemaRejected()

        if response.status_code == 404:
            raise AiUnavailable(
                f"Ollama does not have the model '{self._model}'. Pull it with "
                f"'ollama pull {self._model}' or set OLLAMA_MODEL to one it holds."
            )
        if response.status_code >= 400:
            raise AiUnavailable(
                f"Ollama returned HTTP {response.status_code}. Core GRC functionality "
                "is unaffected."
            )

        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise AiUnavailable(
                "Ollama returned a body that is not JSON. Something other than Ollama "
                f"may be listening on {self._base_url}."
            ) from exc

        if not isinstance(payload, dict):
            raise AiUnavailable("Ollama returned an unexpected response shape.")
        return payload


class _SchemaRejected(Exception):
    """Internal signal: this Ollama build will not accept a JSON schema as 'format'."""
