"""Typed application settings, loaded once from the environment / `.env` file.

Every module that needs configuration imports `get_settings()` from here instead
of reading `os.environ` directly. That keeps all configuration in one validated
place, so a missing or malformed value fails loudly at startup rather than
surfacing as a confusing error deep inside a request.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration for the crew, validated when first instantiated.

    Field names map to environment variables case-insensitively, so the field
    ``openai_api_key`` is populated from the ``OPENAI_API_KEY`` variable (or the
    same key in a local ``.env`` file).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated env vars instead of raising
    )

    # --- LLM: what each agent calls internally ---
    # No default -> required. A missing key raises a clear ValidationError at startup.
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    # --- Networking: one shared host, one port per agent ---
    host: str = "127.0.0.1"
    orchestrator_port: int = 8000
    security_agent_port: int = 8001
    style_agent_port: int = 8002

    # --- Misc ---
    log_level: str = "INFO"

    # URLs are derived, never stored, so host/port stay the single source of truth.
    @property
    def orchestrator_url(self) -> str:
        return f"http://{self.host}:{self.orchestrator_port}"

    @property
    def security_agent_url(self) -> str:
        return f"http://{self.host}:{self.security_agent_port}"

    @property
    def style_agent_url(self) -> str:
        return f"http://{self.host}:{self.style_agent_port}"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide Settings singleton (built once, then cached).

    Using a function instead of a module-level instance makes loading *lazy*:
    importing this module never touches the environment, which keeps imports and
    unit tests cheap and side-effect free.
    """
    return Settings()
