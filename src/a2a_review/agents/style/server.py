"""Boots the Style agent as a running A2A web server.

Same wiring as the Security agent's server, pointed at the Style agent's card,
executor, and port. Run it with::

    uv run python -m a2a_review.agents.style.server
"""

import logging

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a_review.agents.style.agent_card import build_agent_card
from a2a_review.agents.style.executor import StyleAgentExecutor
from a2a_review.common.config import get_settings


def build_asgi_app():
    """Assemble (but do not start) the Style agent's ASGI application."""
    settings = get_settings()
    handler = DefaultRequestHandler(
        agent_executor=StyleAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=build_agent_card(settings.style_agent_url),
        http_handler=handler,
    )
    return app.build()


def main() -> None:
    """Run the Style agent with uvicorn."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    uvicorn.run(build_asgi_app(), host=settings.host, port=settings.style_agent_port)


if __name__ == "__main__":
    main()
