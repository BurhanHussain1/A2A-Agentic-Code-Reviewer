"""The Security agent's public identity on the A2A network: its Agent Card.

In A2A, discovery comes before communication. Before anything can send work to
this agent, it must be able to *find* it and learn what it does. That happens
through an **Agent Card** -- a small JSON document the agent serves at a
well-known URL (e.g. ``/.well-known/agent.json``) advertising its name, the
skills it offers, and the address to reach it.

This module builds that card. The A2A server (see ``server.py``) is what actually
publishes it.
"""

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

# A skill is one capability the agent advertises. id/name/description/tags are
# required; `examples` are optional hints that help a calling agent (or a human)
# decide when to route work to this skill.
SECURITY_SKILL = AgentSkill(
    id="security-review",
    name="Security Review",
    description=(
        "Reviews a code diff for security vulnerabilities: injection flaws, "
        "hardcoded secrets, unsafe deserialization, weak cryptography, and "
        "missing authorization checks."
    ),
    tags=["security", "code-review", "vulnerabilities"],
    examples=[
        "Review this diff for SQL injection.",
        "Does this change leak any credentials?",
    ],
)


def build_agent_card(url: str) -> AgentCard:
    """Build the Security agent's card for an agent reachable at ``url``.

    The URL is injected rather than hardcoded so the same builder works in local
    development, tests, and production without edits -- it comes from config.
    """
    return AgentCard(
        name="Security Reviewer",
        description="An A2A agent that reviews code diffs for security issues.",
        url=url,
        version="0.1.0",
        # Capabilities advertise *optional* protocol features. We don't stream
        # yet (it's on the roadmap), so we leave it off. Rule of thumb: never
        # advertise a capability you haven't implemented.
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],          # accepts a diff as text
        default_output_modes=["application/json"],   # returns structured findings
        skills=[SECURITY_SKILL],
    )
