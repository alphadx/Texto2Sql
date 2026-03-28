"""Two-agent LLM pipeline: query refiner + SQL generator.

Agent 1 (refiner)  – formalises the natural-language question into a clear
                     data-retrieval description, without producing SQL.
Agent 2 (sql_agent)– turns that description into a valid, read-only SQL
                     statement for the target database engine.

Both agents maintain conversational history so that follow-up queries inside
the same session continue the context established by previous turns.
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from openai import OpenAI

from app.llm.session_manager import SessionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI client (lazy singleton)
# ---------------------------------------------------------------------------

_clients: dict[tuple[str, str, str | None], OpenAI] = {}


@dataclass(frozen=True)
class LLMRuntimeConfig:
    provider: str
    api_key: str
    model: str
    base_url: str | None = None


def resolve_llm_config(llm_options: dict[str, Any] | None = None) -> LLMRuntimeConfig:
    options = llm_options or {}
    provider = str(options.get("provider") or os.getenv("LLM_PROVIDER") or "openai").strip()
    api_key = str(options.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    model = str(options.get("model") or os.getenv("OPENAI_MODEL") or "gpt-4").strip()
    base_url_raw = options.get("base_url") or os.getenv("OPENAI_BASE_URL")
    base_url = str(base_url_raw).strip() if base_url_raw else None

    if not api_key:
        raise RuntimeError("Missing LLM API key: set OPENAI_API_KEY or send llm_api_key in request")

    return LLMRuntimeConfig(provider=provider, api_key=api_key, model=model, base_url=base_url)


def _get_client(config: LLMRuntimeConfig) -> OpenAI:
    key = (config.provider, config.api_key, config.base_url)
    if key not in _clients:
        kwargs: dict[str, Any] = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        _clients[key] = OpenAI(**kwargs)
    return _clients[key]


# ---------------------------------------------------------------------------
# System-prompt templates
# ---------------------------------------------------------------------------

_REFINER_SYSTEM = """\
You are a query-refinement agent.  Your job is to analyse a natural-language
question about a relational database and produce a clear, formal description of
the data the user wants to retrieve.

Database schema:
{schema}

For each user question:
- Identify which tables and columns are involved.
- State any filters, conditions, aggregations, groupings, or sort orders.
- Be concise and precise.
- Do NOT write SQL.  Respond in plain English."""

_SQL_AGENT_SYSTEM = """\
You are a SQL-generation agent for {db_model} databases.  Your job is to
convert a formal query description into a valid, executable {db_model} SQL
statement.

Database schema:
{schema}

Rules:
- Return ONLY the raw SQL statement – no explanations, no markdown fences.
- Use correct {db_model} syntax and functions.
- Generate SELECT statements only (read-only)."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_sql(text: str) -> str:
    """Strip markdown code fences that LLMs sometimes wrap around SQL."""
    text = text.strip()
    text = re.sub(r"^```(?:sql)?\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _chat(messages: List[Dict[str, Any]], llm_options: dict[str, Any] | None = None) -> str:
    config = resolve_llm_config(llm_options)
    response = _get_client(config).chat.completions.create(
        model=config.model,
        messages=messages,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Agent 1 – query refiner
# ---------------------------------------------------------------------------


def refine_query(
    session_id: str,
    natural_query: str,
    schema: str,
    session_manager: SessionManager,
    llm_options: dict[str, Any] | None = None,
) -> str:
    """Formalise *natural_query* into a structured description (no SQL)."""
    history = session_manager.get_history(session_id, "refiner")

    if not history:
        history = [
            {
                "role": "system",
                "content": _REFINER_SYSTEM.format(schema=schema),
            }
        ]

    history.append({"role": "user", "content": natural_query})

    refined = _chat(history, llm_options=llm_options)

    history.append({"role": "assistant", "content": refined})
    session_manager.set_history(session_id, "refiner", history)

    logger.debug("Refined query for session %s: %s", session_id, refined)
    return refined


# ---------------------------------------------------------------------------
# Agent 2 – SQL generator
# ---------------------------------------------------------------------------


def generate_sql(
    session_id: str,
    refined_query: str,
    schema: str,
    db_model: str,
    session_manager: SessionManager,
    llm_options: dict[str, Any] | None = None,
) -> str:
    """Convert *refined_query* into an executable SQL statement."""
    history = session_manager.get_history(session_id, "sql_agent")

    if not history:
        history = [
            {
                "role": "system",
                "content": _SQL_AGENT_SYSTEM.format(
                    schema=schema, db_model=db_model
                ),
            }
        ]

    history.append({"role": "user", "content": refined_query})

    sql = _clean_sql(_chat(history, llm_options=llm_options))

    history.append({"role": "assistant", "content": sql})
    session_manager.set_history(session_id, "sql_agent", history)

    logger.debug("Generated SQL for session %s: %s", session_id, sql)
    return sql
