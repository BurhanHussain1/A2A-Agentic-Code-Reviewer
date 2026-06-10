"""The ``review`` command: send a diff to the crew and print the merged report.

This is the human entry point and a thin A2A *client*. It calls no LLM and needs
no API key of its own -- it hands a diff to the orchestrator and renders whatever
``CrewReview`` comes back. The orchestrator (and its specialists) hold the key.
"""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from a2a_review.common.a2a_client import request_review
from a2a_review.common.schemas import CrewReview, Severity

console = Console()

DEFAULT_ORCHESTRATOR_URL = "http://127.0.0.1:8000"

# Terminal colours per severity, worst -> mildest.
_SEVERITY_STYLE = {
    Severity.CRITICAL: "bold white on red",
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}


def _render(review: CrewReview) -> None:
    """Print a CrewReview as colourful, human-readable output."""
    for result in review.results:
        console.print(f"[bold]{result.agent_name}[/bold]: {result.summary}")
    for name, error in review.errors.items():
        console.print(f"[bold red]{name} agent failed:[/bold red] {error}")

    findings = review.all_findings()
    if not findings:
        console.print("\n[bold green]No issues found. 🎉[/bold green]")
        return

    table = Table(title=f"\n{len(findings)} findings (worst first)", show_lines=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Where", no_wrap=True)
    table.add_column("Issue")

    for finding in findings:
        severity = f"[{_SEVERITY_STYLE[finding.severity]}]{finding.severity.value.upper()}[/]"
        where = finding.file or "-"
        if finding.line is not None:
            where += f":{finding.line}"
        issue = f"[bold]{finding.title}[/bold]\n{finding.detail}"
        if finding.suggestion:
            issue += f"\n[green]Fix:[/green] {finding.suggestion}"
        table.add_row(severity, where, issue)

    console.print(table)

    counts = {sev.value: n for sev, n in review.counts_by_severity().items() if n}
    console.print("\n[bold]Summary:[/bold] " + ", ".join(f"{n} {s}" for s, n in counts.items()))


def main(
    diff_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to a unified diff (or source file) to review.",
        ),
    ],
    url: Annotated[
        str, typer.Option(help="Orchestrator base URL.")
    ] = DEFAULT_ORCHESTRATOR_URL,
) -> None:
    """Review a code diff with the A2A code-review crew."""
    diff = diff_file.read_text(encoding="utf-8")
    if not diff.strip():
        console.print("[red]The diff file is empty.[/red]")
        raise typer.Exit(code=2)

    console.print(f"[dim]Sending {diff_file} to the crew at {url} ...[/dim]")
    try:
        review = asyncio.run(request_review(url, diff, result_model=CrewReview))
    except Exception as exc:
        console.print(f"[bold red]Review failed:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    _render(review)

    # Non-zero exit when serious issues exist -- lets this gate a CI pipeline later.
    counts = review.counts_by_severity()
    if counts[Severity.CRITICAL] or counts[Severity.HIGH]:
        raise typer.Exit(code=1)


def app() -> None:
    """Console-script entry point, wired up in pyproject ``[project.scripts]``."""
    typer.run(main)


if __name__ == "__main__":
    app()
