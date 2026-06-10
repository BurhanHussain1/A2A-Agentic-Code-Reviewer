"""Boots the Security agent as a running A2A web server.

This is the wiring that turns our parts into a live, reachable agent:

* ``InMemoryTaskStore``       -- remembers tasks while they run (in memory).
* ``SecurityAgentExecutor``   -- our review logic (the "brain").
* ``DefaultRequestHandler``   -- implements the A2A protocol methods and delegates
                                 the real work to the executor.
* ``A2AStarletteApplication`` -- the ASGI web app that publishes the Agent Card at
                                 ``/.well-known/agent-card.json`` and exposes the
                                 JSON-RPC endpoint at ``/``.

Run it with::

    uv run python -m a2a_review.agents.security.server
"""

import logging

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a_review.agents.security.agent_card import build_agent_card
from a2a_review.agents.security.executor import SecurityAgentExecutor
from a2a_review.common.config import get_settings


def build_asgi_app():
    """Assemble (but do not start) the Security agent's ASGI application.

    Kept separate from :func:`main` so tests can build the app and exercise it with
    an in-process HTTP client, without binding a real network port.
    """
    settings = get_settings()

    handler = DefaultRequestHandler(
        agent_executor=SecurityAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=build_agent_card(settings.security_agent_url),
        http_handler=handler,
    )
    # .build() returns the actual Starlette ASGI app with the A2A routes attached.
    return app.build()


def main() -> None:
    """Run the Security agent with uvicorn."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    uvicorn.run(build_asgi_app(), host=settings.host, port=settings.security_agent_port)


if __name__ == "__main__":
    main()
