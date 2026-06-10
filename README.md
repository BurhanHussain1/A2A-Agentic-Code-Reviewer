# A2A Code Review Crew

> A crew of independent AI agents that review a code diff **in parallel** and return
> structured findings — built on **Google's open [Agent2Agent (A2A) protocol](https://a2a-protocol.org/)**.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![A2A](https://img.shields.io/badge/protocol-A2A%20v1-4285F4.svg)](https://a2a-protocol.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](#license)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

> 🚧 **Status: early development.** The foundation (project config, typed settings) is in
> place; the agents are being implemented one at a time. See the [Roadmap](#roadmap) for
> exactly what works today.

---

## What it does

Instead of one monolithic prompt trying to do everything, this project models code review
the way a real team does it — as **specialists working in parallel**:

- a **Security agent** hunts for injection, secrets, unsafe deserialization, authz gaps;
- a **Style/Quality agent** flags readability, naming, dead code, and complexity;
- an **Orchestrator agent** fans the diff out to every specialist, then merges their
  findings into a single, deduplicated report.

Each specialist is a **separate process** that speaks the **A2A protocol** over the wire.
The orchestrator doesn't import the specialists or know how they're built — it discovers
them through their **Agent Cards** and delegates work via standard A2A messages. That is
the whole point of A2A: agents built by different teams, in different frameworks, can
collaborate without sharing code.

## Why A2A (and how it's used here)

[A2A](https://a2a-protocol.org/) is an open protocol (originally from Google, now stewarded
by the Linux Foundation) that standardizes how autonomous agents **discover each other and
delegate tasks**. This project uses three of its core ideas:

| A2A concept | How this project uses it |
| --- | --- |
| **Agent Card** (`/.well-known/agent-card.json`) | Each specialist advertises its name, skills, and endpoint so the orchestrator can discover it. |
| **Task lifecycle** | A review is a *task* with states (`submitted → working → completed`), so long reviews can stream progress. |
| **JSON-RPC 2.0 transport** | All agent-to-agent calls go over A2A's standard JSON-RPC messages — no bespoke API glue. |

> **A2A vs. MCP:** A2A governs how agents talk to **each other**. The LLM each agent calls
> internally (OpenAI here) is a separate concern — that clean separation is exactly what the
> protocol is designed for.

## Architecture

```text
                       ┌─────────────────────────┐
   code diff  ───────► │     CLI  (review)       │
                       └────────────┬────────────┘
                                    │  A2A (JSON-RPC / HTTP)
                                    ▼
                       ┌─────────────────────────┐
                       │   Orchestrator Agent     │  discovers specialists via
                       │   :8000                  │  their Agent Cards, fans out,
                       └─────────┬───────┬────────┘  then merges the results
                       A2A       │       │      A2A
                    ┌────────────┘       └────────────┐
                    ▼                                 ▼
        ┌────────────────────┐            ┌────────────────────┐
        │  Security Agent     │            │  Style / Quality    │
        │  :8001              │            │  Agent  :8002       │
        └─────────┬───────────┘            └─────────┬───────────┘
                  │            OpenAI (internal)      │
                  └───────────────────┬───────────────┘
                                      ▼
                            structured Findings
```

## Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Agent protocol | [`a2a-sdk`](https://pypi.org/project/a2a-sdk/) `1.1` | Official A2A implementation: servers, client, typed messages |
| Reasoning | [`openai`](https://pypi.org/project/openai/) | The LLM each agent calls internally |
| Data models | [`pydantic`](https://docs.pydantic.dev/) v2 | Typed, validated findings exchanged between agents |
| Config | `pydantic-settings` | One validated `Settings` object from `.env` |
| Server | `uvicorn` | ASGI server that runs each agent |
| CLI | `typer` + `rich` | Clean command line + readable output |
| Tooling | `uv`, `ruff`, `pytest` | Fast installs, linting, tests |

## Getting started

### Prerequisites
- Python **3.11+**
- [`uv`](https://docs.astral.sh/uv/) (`pip install uv` or `winget install astral-sh.uv`)
- An OpenAI API key

### Setup
```bash
# 1. Clone
git clone https://github.com/BurhanHussain1/a2a-code-review-crew.git
cd a2a-code-review-crew

# 2. Install dependencies into a local virtualenv
uv sync --extra dev

# 3. Configure your environment
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
# then edit .env and set OPENAI_API_KEY
```

### Run a review
```bash
# Start each agent in its own terminal (or background process):
uv run python -m a2a_review.agents.security.server
uv run python -m a2a_review.agents.style.server
uv run python -m a2a_review.agents.orchestrator.server

# Then send a diff to be reviewed:
uv run review path/to/changes.diff
```
*(Commands reflect the target workflow; see the [Roadmap](#roadmap) for what is wired up today.)*

## Project structure

```text
src/a2a_review/
├── common/            # shared building blocks
│   ├── config.py      #   typed settings loaded from .env
│   ├── schemas.py     #   Finding / ReviewResult data contract
│   └── llm.py         #   thin OpenAI client wrapper
├── agents/
│   ├── security/      # security specialist (agent_card · executor · server)
│   ├── style/         # style / quality specialist
│   └── orchestrator/  # discovers specialists, fans out, merges findings
└── client/
    └── cli.py         # `review` command — sends a diff into the crew
```

## Roadmap

- [x] Project scaffold (`pyproject.toml`, `uv`, `ruff`)
- [x] Typed configuration (`common/config.py`)
- [x] Review data contract (`common/schemas.py`)
- [x] OpenAI client wrapper (`common/llm.py`)
- [x] Security agent (Agent Card + executor + A2A server)
- [x] Style / quality agent
- [x] Orchestrator agent (discovery + fan-out + merge)
- [ ] `review` CLI client
- [ ] Streaming progress over A2A Server-Sent Events
- [ ] GitHub integration (review real pull requests)
- [ ] Containerize + deploy (Cloud Run)
- [ ] Demo recording

## What this project demonstrates

- Designing a **multi-agent system** with clear separation of concerns
- Implementing the **A2A protocol** directly (Agent Cards, tasks, JSON-RPC) — not hidden
  behind a framework
- Correctly separating **inter-agent communication (A2A)** from **internal reasoning (LLM)**
- Production hygiene: typed config, validated data contracts, linting, a `src/` layout

## License

Licensed under the **MIT License**.

## Acknowledgements

- [A2A Protocol](https://a2a-protocol.org/) and the [`a2a-sdk`](https://github.com/a2aproject/a2a-python)
- Built as a portfolio project to explore agent interoperability.
