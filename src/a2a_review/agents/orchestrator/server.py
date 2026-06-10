"""Boots the Orchestrator as a running A2A web server.

Same wiring as the specialists' servers, pointed at the orchestrator's card,
executor, and port. This agent is both a server (to the CLI) and -- via its
executor -- a client to the specialists. Run it with::

    uv run python -m a2a_review.agents.orchestrator.server

Note: the specialist agents must be running too, or the orchestrator will report
them as failed in the merged result.
"""

import logging

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a_review.agents.orchestrator.agent_card import build_agent_card
from a2a_review.agents.orchestrator.executor import OrchestratorExecutor
from a2a_review.common.config import get_settings


def build_asgi_app():
    """Assemble (but do not start) the Orchestrator's ASGI application."""
    settings = get_settings()
    handler = DefaultRequestHandler(
        agent_executor=OrchestratorExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(
        agent_card=build_agent_card(settings.orchestrator_url),
        http_handler=handler,
    )
    return app.build()


def main() -> None:
    """Run the Orchestrator with uvicorn."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    uvicorn.run(build_asgi_app(), host=settings.host, port=settings.orchestrator_port)


if __name__ == "__main__":
    main()
