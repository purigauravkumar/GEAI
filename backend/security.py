import hashlib
import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse


PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/redoc"}


def _configured_key() -> str:
    return os.getenv("GEAI_API_KEY", "").strip()


async def api_key_middleware(request: Request, call_next):
    """Require GEAI_API_KEY for API access, except harmless documentation routes."""
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    configured = _configured_key()
    supplied = request.headers.get("X-GEAI-API-Key", "").strip()

    if not configured:
        return JSONResponse(
            status_code=503,
            content={"error": "GEAI_API_KEY is not configured"},
        )

    if not supplied or not hmac.compare_digest(
        hashlib.sha256(supplied.encode()).digest(),
        hashlib.sha256(configured.encode()).digest(),
    ):
        return JSONResponse(status_code=401, content={"error": "unauthorized"})

    return await call_next(request)
