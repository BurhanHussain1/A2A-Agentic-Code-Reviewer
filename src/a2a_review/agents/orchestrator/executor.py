"""The Orchestrator's executor: fan out to the specialists, merge their results.

This is what makes the project *multi-agent*. When a diff arrives, the orchestrator
acts as an A2A **client** to each specialist (reusing ``request_review``), calls
them all **in parallel**, and merges whatever comes back into a single
``CrewReview`` -- staying honest about any specialist that failed.
"""

import asyncio
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part
from a2a.utils import new_task

from a2a_review.common.a2a_client import request_review
from a2a_review.common.config import get_settings
from a2a_review.common.schemas import CrewReview, ReviewResult

logger = logging.getLogger(__name__)


class OrchestratorExecutor(AgentExecutor):
    """Reviews a diff by delegating to a crew of specialist A2A agents."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        diff = context.get_user_input()

        task = context.current_task
        if task is None:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if not diff.strip():
            await updater.failed(
                message=updater.new_agent_message(
                    [Part(root=DataPart(data={"error": "No diff was provided to review."}))]
                )
            )
            return

        await updater.start_work()

        # The crew: a label -> A2A address for each specialist. Adding a third
        # specialist later is just another entry here.
        settings = get_settings()
        specialists = {
            "security": settings.security_agent_url,
            "style": settings.style_agent_url,
        }

        # Fan out: every specialist reviews the SAME diff at the SAME time. With
        # return_exceptions=True, one specialist failing (or being down) doesn't
        # abort the others -- gather collects whatever each call produced.
        logger.info("Delegating diff to %d specialists: %s", len(specialists), list(specialists))
        outcomes = await asyncio.gather(
            *(request_review(url, diff) for url in specialists.values()),
            return_exceptions=True,
        )

        # Merge: a ReviewResult goes into results[]; anything else is an error.
        crew = CrewReview()
        for name, outcome in zip(specialists, outcomes, strict=True):
            if isinstance(outcome, ReviewResult):
                crew.results.append(outcome)
            else:
                logger.warning("Specialist '%s' failed: %s", name, outcome)
                crew.errors[name] = str(outcome)

        # If every specialist failed, the whole review failed -- say so clearly.
        if not crew.results:
            payload = {"error": "All specialists failed.", "details": crew.errors}
            await updater.failed(
                message=updater.new_agent_message([Part(root=DataPart(data=payload))])
            )
            return

        # Otherwise complete with the merged report (possibly partial, which the
        # `errors` field makes explicit).
        logger.info(
            "Crew review done: %d succeeded, %d failed", len(crew.results), len(crew.errors)
        )
        await updater.add_artifact(
            [Part(root=DataPart(data=crew.model_dump(mode="json")))],
            name="code-review",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Code review does not support cancellation.")
