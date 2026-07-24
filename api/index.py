"""
Vercel serverless entrypoint for Cassandra.

Vercel serves the whole site from this one Python function (see vercel.json),
so `app` below answers /, /health and /mcp exactly as `python server.py` does
locally. Same reasoning engine, same on-chain evidence, no second code path.

The one subtlety: FastMCP starts its StreamableHTTPSessionManager inside the
ASGI *lifespan*. A serverless adapter that never emits lifespan events leaves
that task group uninitialised, and then /mcp raises "Task group is not
initialized" on every call while /health still returns 200 — a green health
check in front of a dead service. Verified: without lifespan, GET /health is
200 and POST /mcp is a 500.

So the middleware below enters the lifespan lazily on the first request, once
per instance, and stands down if the platform emits lifespan itself.
"""
from __future__ import annotations

import asyncio
import os
import sys

# server.py lives one level up; keep it importable wherever Vercel unpacks us.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import mcp  # noqa: E402

_app = mcp.http_app(path="/mcp", stateless_http=True)

_state: dict[str, object] = {"platform_lifespan": False, "ready": None}


async def _boot() -> None:
    """Enter the router's lifespan once per instance and hold it open."""
    ready = _state.get("ready")
    if isinstance(ready, asyncio.Event):
        await ready.wait()
        return

    ready = asyncio.Event()
    _state["ready"] = ready

    async def hold() -> None:
        try:
            async with _app.router.lifespan_context(_app):
                ready.set()
                await asyncio.Event().wait()   # keep the session manager alive
        except Exception:
            ready.set()                        # never hang a request on this

    asyncio.create_task(hold())
    await ready.wait()


class LifespanBoot:
    """Pure-ASGI middleware: guarantees the session manager is initialised."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            _state["platform_lifespan"] = True
            await self.app(scope, receive, send)
            return
        if not _state["platform_lifespan"]:
            await _boot()
        await self.app(scope, receive, send)


_app.add_middleware(LifespanBoot)

# Vercel looks for `app`. A real Starlette instance leaves no ambiguity about
# whether this is ASGI or WSGI.
app = _app
