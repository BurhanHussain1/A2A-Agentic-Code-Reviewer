"""The Security agent's executor: the code the A2A server runs on every request.

The A2A server owns the protocol -- HTTP, JSON-RPC, and the task lifecycle. When
a request arrives, it hands control to this ``AgentExecutor``. Our job is narrow:

    1. read the code diff out of the incoming message,
    2. ask the LLM to review it with a security-focused prompt,
    3. report the structured findings back through the task.

This is where the agent's collaborators meet: ``llm`` does the reasoning, the
``schemas`` define the result shape, and the ``TaskUpdater`` speaks A2A.
"""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part
from a2a.utils import new_task

from a2a_review.common import llm

logger = logging.getLogger(__name__)

# The system prompt is what turns the shared `llm.review` engine into a *security*
# reviewer specifically. Swapping this prompt is the entire difference between
# this agent and the style agent.
SECURITY_SYSTEM_PROMPT = """\
You are a meticulous application security reviewer.

Review the code diff the user provides and report only genuine security concerns:
injection (SQL, command, XSS), hardcoded secrets or credentials, unsafe
deserialization, weak or misused cryptography, path traversal, SSRF, and missing
authentication or authorization checks.

Rules:
- Report ONLY security issues. Ignore style, naming, and performance.
- If the diff has no security problems, return an empty findings list and say so
  in the summary. Never invent issues to look thorough.
- Set `agent_name` to "security".
- Identify the file and line from the diff whenever you can.
- Make every `suggestion` a concrete, minimal fix.
"""


class SecurityAgentExecutor(AgentExecutor):
    """Runs one security review per incoming A2A request."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # (1) The diff is simply the text the caller sent. get_user_input()
        # concatenates the text parts of the incoming A2A message for us.
        diff = context.get_user_input()

        # Every A2A interaction is tracked as a Task. Reuse the one the server
        # already created, or create + publish a fresh Task if this is new work.
        task = context.current_task
        if task is None:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        # The TaskUpdater is our handle for driving the task through its lifecycle
        # (working -> completed/failed) and attaching results.
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        if not diff.strip():
            await updater.failed(
                message=updater.new_agent_message(
                    [Part(root=DataPart(data={"error": "No diff was provided to review."}))]
                )
            )
            return

        # (2) Move the task to 'working', then do the slow LLM call.
        await updater.start_work()
        try:
            result = await llm.review(SECURITY_SYSTEM_PROMPT, diff)
        except Exception as exc:  # any failure becomes a clean A2A 'failed' state
            logger.exception("Security review failed")
            await updater.failed(
                message=updater.new_agent_message(
                    [Part(root=DataPart(data={"error": str(exc)}))]
                )
            )
            return

        # (3) Attach the findings as a structured JSON artifact, then complete.
        # model_dump(mode="json") turns the ReviewResult into a plain dict whose
        # values are all JSON-safe (e.g. the Severity enum becomes "high").
        await updater.add_artifact(
            [Part(root=DataPart(data=result.model_dump(mode="json")))],
            name="security-review",
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # A single review is short-lived, so there is nothing to cancel mid-flight.
        raise NotImplementedError("Security review does not support cancellation.")
