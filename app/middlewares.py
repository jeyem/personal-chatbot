import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# ── in-memory counters ────────────────────────────────────
# structure: { key: {"minute": [timestamps], "day": [timestamps]} }
_counters: dict[str, dict[str, list[float]]] = defaultdict(
    lambda: {"minute": [], "day": []}
)

LIMIT_PER_MINUTE = 5
LIMIT_PER_DAY    = 100

REQUIRED_HEADERS = {"user-agent", "accept", "accept-language"}
BLOCKED_AGENTS   = {"curl", "python-requests", "httpie", "wget"}


def _identify(request: Request) -> str | None:
    """Return identifier string or None if cant identify."""
    ip        = request.client.host if request.client else None
    user_hash = None

    # try to extract user_hash from body — cached by starlette after first read
    # we rely on it being set in request.state by the route, so here we use IP only
    # user_hash is checked in the route itself for chat-level identity
    return ip


def _is_browser(request: Request) -> bool:
    """Rough browser fingerprint check via headers."""
    headers     = {k.lower() for k in request.headers.keys()}
    user_agent  = request.headers.get("user-agent", "").lower()

    # must have basic browser headers
    if not REQUIRED_HEADERS.issubset(headers):
        return False

    # block known bot user agents
    if any(agent in user_agent for agent in BLOCKED_AGENTS):
        return False

    # must look like a real browser UA
    if not any(b in user_agent for b in ["mozilla", "chrome", "safari", "firefox", "edge"]):
        return False

    return True


def _is_rate_limited(key: str) -> tuple[bool, str]:
    now     = time.time()
    counter = _counters[key]

    # clean old timestamps
    counter["minute"] = [t for t in counter["minute"] if now - t < 60]
    counter["day"]    = [t for t in counter["day"]    if now - t < 86400]

    if len(counter["minute"]) >= LIMIT_PER_MINUTE:
        return True, "Too many requests — slow down."
    if len(counter["day"]) >= LIMIT_PER_DAY:
        return True, "Daily limit reached. Come back tomorrow."

    # record this request
    counter["minute"].append(now)
    counter["day"].append(now)
    return False, ""


class ProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # skip docs and health routes
        if request.url.path in {"/docs", "/redoc", "/openapi.json", "/health"}:
            return await call_next(request)

        # browser check
        if not _is_browser(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden."},
            )

        # rate limit by IP
        ip = _identify(request)
        if ip:
            limited, reason = _is_rate_limited(f"ip:{ip}")
            if limited:
                return JSONResponse(
                    status_code=429,
                    content={"detail": reason},
                )

        return await call_next(request)