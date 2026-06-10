"""The Style agent's public identity on the A2A network: its Agent Card.

Identical in shape to the Security agent's card (see that file for the full
explanation of what an Agent Card is) -- only the identity and the advertised
skill differ, because this agent does a different job.
"""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

STYLE_SKILL = AgentSkill(
    id="style-review",
    name="Style & Quality Review",
    description=(
        "Reviews a code diff for readability and maintainability: unclear naming, "
        "excessive complexity, long functions, duplicated or dead code, magic "
        "numbers, and missing error handling."
    ),
    tags=["style", "code-quality", "readability", "maintainability"],
    examples=[
        "Is this function too complex?",
        "Are the names in this change clear?",
    ],
)


def build_agent_card(url: str) -> AgentCard:
    """Build the Style agent's card for an agent reachable at ``url``."""
    return AgentCard(
        name="Style Reviewer",
        description="An A2A agent that reviews code diffs for quality and readability.",
        url=url,
        version="0.1.0",
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["application/json"],
        skills=[STYLE_SKILL],
    )
