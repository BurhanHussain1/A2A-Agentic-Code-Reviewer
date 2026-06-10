"""The one and only place that talks to OpenAI.

Every agent calls :func:`review` with a system prompt (its personality / focus)
and a code diff, and gets back a validated :class:`ReviewResult`. The model is
*forced* to answer in that exact shape via OpenAI Structured Outputs, so there is
no fragile JSON parsing anywhere else in the codebase.

Because this is the only module that imports ``openai``, switching providers later
(Gemini, Anthropic, a local model, ...) means editing this single file.
"""

from functools import lru_cache

from openai import AsyncOpenAI

from a2a_review.common.config import get_settings
from a2a_review.common.schemas import ReviewResult


@lru_cache
def _client() -> AsyncOpenAI:
    """Build the async OpenAI client once and reuse it.

    The client is cheap to keep around and holds a connection pool, so we create
    it lazily on first use and cache it for the life of the process.
    """
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def review(system_prompt: str, diff: str) -> ReviewResult:
    """Run one code review with the LLM and return a validated result.

    Parameters
    ----------
    system_prompt:
        Defines the reviewer's focus (e.g. "you are a security reviewer ...").
        This is what makes the security agent behave differently from the style
        agent even though they share this same function.
    diff:
        The code change to review, as a unified diff or plain snippet.

    Returns
    -------
    ReviewResult
        Always conforms to the schema; the model cannot return a malformed shape.
    """
    settings = get_settings()

    completion = await _client().chat.completions.parse(
        model=settings.openai_model,
        # Low temperature -> consistent, repeatable reviews. (Some reasoning models
        # reject a custom temperature; if you switch to one, remove this line.)
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": diff},
        ],
        # Passing the Pydantic class turns on Structured Outputs: the SDK sends its
        # JSON schema and the model is constrained to match it exactly.
        response_format=ReviewResult,
    )

    message = completion.choices[0].message

    # Structured Outputs can still decline on safety grounds instead of answering.
    if message.refusal:
        raise RuntimeError(f"LLM refused to review the diff: {message.refusal}")

    if message.parsed is None:  # defensive: should not occur on a successful parse
        raise RuntimeError("LLM returned an empty result.")

    return message.parsed
