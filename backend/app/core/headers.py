"""Response headers a browser acts on.

The API serves JSON to a single-page application on another origin, so most of these
are belt-and-braces: nothing here is rendered as a page. They exist because the
alternative -- "expected at the proxy" -- is a header that is not there until someone
remembers to add it, and SECURITY.md was listing their absence as a gap.

- ``Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`` on every API
  response. A JSON body has nothing to load, so the strictest policy is the right one.
  The interactive documentation is the exception: Swagger UI and ReDoc load their
  assets from a CDN, so ``/docs``, ``/redoc`` and ``/openapi.json`` get a policy that
  allows exactly that and nothing else.
- ``X-Content-Type-Options: nosniff`` and ``X-Frame-Options: DENY``: the former stops a
  browser second-guessing a content type, the latter is the pre-CSP spelling of
  ``frame-ancestors 'none'`` for browsers that still read it.
- ``Referrer-Policy: no-referrer``: a URL like ``/risks/RISK-004`` is a fact about the
  ISMS, and it should not leak to whatever the browser navigates to next.
- ``Cache-Control: no-store``: a register is not something a shared cache should keep.
- ``Strict-Transport-Security`` only outside development. Sending it over plain HTTP
  is meaningless, and sending it from a local demo would pin the developer's browser to
  HTTPS on localhost for a year.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

API_CSP = "default-src 'none'; frame-ancestors 'none'"
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, hsts: bool) -> None:
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        is_docs = request.url.path.startswith(_DOCS_PATHS)
        response.headers.setdefault("Content-Security-Policy", DOCS_CSP if is_docs else API_CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if not is_docs:
            response.headers.setdefault("Cache-Control", "no-store")
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response
