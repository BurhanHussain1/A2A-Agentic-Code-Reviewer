"""The data contract for a code review.

These Pydantic models are the *shared language* every agent speaks. A specialist
agent produces a ``ReviewResult``; the orchestrator consumes many of them. Because
the models are typed:

* data is **validated** automatically when it crosses the A2A wire,
* it serializes to / from JSON with ``.model_dump_json()`` / ``.model_validate_json()``,
* and the JSON schema can be handed straight to the LLM to force it to answer in
  exactly this shape (see ``common/llm.py``).

Define the contract once here, and the whole crew stays consistent.
"""

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """How serious a finding is.

    Subclassing ``str`` means a Severity *is* a string ("high"), so it serializes
    cleanly to JSON while still being a closed set of allowed values — an agent
    can never invent a severity like "kinda bad".
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        """Numeric urgency (higher = worse), used to sort findings worst-first."""
        return {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.INFO: 0,
        }[self]


class Finding(BaseModel):
    """A single issue raised by a review agent.

    The ``description`` on each field is not just documentation: it is fed to the
    LLM as part of the JSON schema, so it doubles as an instruction for what to put
    there.
    """

    severity: Severity = Field(description="How serious the issue is.")
    title: str = Field(description="A short, one-line summary of the issue.")
    detail: str = Field(description="What the problem is and why it matters.")
    file: str | None = Field(default=None, description="File the issue is in, if known.")
    line: int | None = Field(default=None, description="1-based line number, if known.")
    suggestion: str | None = Field(default=None, description="A concrete fix, if there is one.")


class ReviewResult(BaseModel):
    """Everything one specialist agent reports about a diff."""

    agent_name: str = Field(description="Which agent produced this result, e.g. 'security'.")
    summary: str = Field(description="A one or two sentence overall assessment.")
    findings: list[Finding] = Field(default_factory=list)

    def sorted_findings(self) -> list[Finding]:
        """Return findings ordered worst-first (critical → info)."""
        return sorted(self.findings, key=lambda f: f.severity.rank, reverse=True)
