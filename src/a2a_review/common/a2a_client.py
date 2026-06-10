"""Client side of A2A: call a remote review agent and get a ReviewResult back.

The specialist agents are A2A *servers* -- they receive work. The orchestrator
(and our tests) act as A2A *clients* to them. This module wraps the SDK client
flow behind one async function, ``request_review``:

    1. discover the agent by fetching its Agent Card,
    2. build a client for it,
    3. send the diff as a user message,
    4. wait for the task to finish and pull the ReviewResult out of its artifact.

That is the exact mirror of what the executor (server side) does, viewed from the
caller's end.
"""

from typing import TypeVar

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.client.helpers import create_text_message_object
from a2a.types import Role, Task, TaskState
from a2a.utils import get_data_parts, get_text_parts
from pydantic import BaseModel

from a2a_review.common.schemas import ReviewResult

# The result artifact is validated into whichever model the caller asks for:
# specialists return a ReviewResult, the orchestrator returns a CrewReview.
T = TypeVar("T", bound=BaseModel)


async def request_review(
    base_url: str,
    diff: str,
    *,
    result_model: type[T] = ReviewResult,
    timeout: float = 120.0,
) -> T:
    """Ask the A2A agent at ``base_url`` to review ``diff`` and return its result.

    ``result_model`` is the Pydantic type the result artifact is validated into.
    Specialists return a ``ReviewResult`` (the default); the orchestrator returns a
    ``CrewReview``, so the CLI passes ``result_model=CrewReview``.

    Raises ``RuntimeError`` if the agent cannot be reached, the task fails, or the
    completed task carries no review data.
    """
    async with httpx.AsyncClient(timeout=timeout) as http:
        # (1) Discovery: fetch the agent card from /.well-known/agent-card.json.
        # This is the same document we curled earlier -- the SDK just parses it
        # into an AgentCard for us.
        card = await A2ACardResolver(http, base_url=base_url).get_agent_card()

        # (2) Build a client bound to that agent. streaming=False because our
        # agents don't advertise streaming yet, so send_message blocks until the
        # task reaches a terminal state and returns the final Task.
        client = ClientFactory(ClientConfig(httpx_client=http, streaming=False)).create(card)

        # (3) Send the diff as a user message.
        message = create_text_message_object(role=Role.user, content=diff)

        # Non-streaming responses arrive as (Task, update) tuples; we keep the
        # latest Task seen, whose final form carries the result.
        final_task: Task | None = None
        async for event in client.send_message(message):
            if isinstance(event, tuple):
                final_task = event[0]

    if final_task is None:
        raise RuntimeError(f"Agent at {base_url} returned no task.")

    if final_task.status.state != TaskState.completed:
        raise RuntimeError(
            f"Review at {base_url} ended as '{final_task.status.state.value}': "
            f"{_status_detail(final_task)}"
        )

    # (4) Extract the structured findings from the completed task's artifact.
    for artifact in final_task.artifacts or []:
        data_parts = get_data_parts(artifact.parts)
        if data_parts:
            return result_model.model_validate(data_parts[0])

    raise RuntimeError(f"Completed task from {base_url} contained no review data.")


def _status_detail(task: Task) -> str:
    """Best-effort human-readable reason from a non-completed task's status message."""
    message = task.status.message
    if message is None:
        return "no detail provided"
    for data in get_data_parts(message.parts):
        if "error" in data:
            return str(data["error"])
    texts = get_text_parts(message.parts)
    return " ".join(texts) if texts else "no detail provided"
