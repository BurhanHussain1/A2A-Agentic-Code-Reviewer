"""The Orchestrator's public identity: the crew's front door.

This is the card a *client* (our CLI) discovers. From the outside the crew looks
like a single agent that does "code review"; the fact that it delegates to a
security agent and a style agent behind the scenes is an implementation detail the
caller never has to know. That encapsulation is a core A2A idea: agents are opaque.
"""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

CODE_REVIEW_SKILL = AgentSkill(
    id="code-review",
    name="Code Review",
    description=(
        "Reviews a code diff by delegating to a crew of specialist agents "
        "(security and style) in parallel, then merges their findings into a "
        "single prioritized report."
    ),
    tags=["code-review", "orchestration", "multi-agent"],
    examples=[
        "Review this pull request diff.",
        "Run a full code review on this change.",
    ],
)


def build_agent_card(url: str) -> AgentCard:
    """Build the Orchestrator's card for an agent reachable at ``url``."""
    return AgentCard(
        name="Code Review Crew",
        description="An A2A agent that orchestrates a crew of reviewers over a code diff.",
        url=url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["application/json"],
        skills=[CODE_REVIEW_SKILL],
    )
