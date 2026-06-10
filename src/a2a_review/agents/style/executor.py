"""The Style agent's executor.

Structurally identical to the Security agent's executor -- read the diff, call the
LLM, attach the findings, complete the task. The ONLY meaningful difference is the
system prompt, which focuses the same ``llm.review`` engine on code quality instead
of security. (This near-duplication is the refactor opportunity noted in the
roadmap: a shared base executor parameterised by prompt + name.)
"""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part
from a2a.utils import new_task

from a2a_review.common import llm

logger = logging.getLogger(__name__)

STYLE_SYSTEM_PROMPT = """\
You are an experienced senior engineer reviewing code for quality and readability.

Review the code diff the user provides and report maintainability concerns:
unclear or misleading names, overly complex or deeply nested logic, functions that
do too much, duplicated code, dead or unreachable code, magic numbers, and missing
error handling.

Rules:
- Focus on readability, maintainability, and clarity. Do NOT report security
  vulnerabilities -- a separate agent handles those.
- If the code is already clean, return an empty findings list and say so. Do not
  nitpick for the sake of looking thorough.
- Set `agent_name` to "style".
- Identify the file and line from the diff whenever you can.
- Make every `suggestion` a concrete, minimal improvement.
"""


class StyleAgentExecutor(AgentExecutor):
    """Runs one style/quality review per incoming A2A request."""

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
        try:
            result = await llm.review(STYLE_SYSTEM_PROMPT, diff)
        except Exception as exc:
            logger.exception("Style review failed")
            await updater.failed(
                message=updater.new_agent_message(
                    [Part(root=DataPart(data={"error": str(exc)}))]
                )
            )
            return

        await updater.add_artifact(
            [Part(root=DataPart(data=result.model_dump(mode="json")))],
            name="style-review",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Style review does not support cancellation.")
