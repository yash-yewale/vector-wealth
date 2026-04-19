"""
Storage Service — JSON file-based persistence for portfolios and chat history.

Simple, reliable storage without external database dependencies.
Data stored in the vector_wealth_db/ directory alongside existing ChromaDB data.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("vector_wealth.storage")

DB_PATH = Path(os.getenv("VECTOR_WEALTH_DB_PATH", str(Path(__file__).resolve().parent / "vector_wealth_db")))
PORTFOLIO_PATH = DB_PATH / "portfolios.json"
CHAT_HISTORY_PATH = DB_PATH / "chat_history.json"

_lock = threading.Lock()

MAX_CHAT_MESSAGES_PER_SESSION = 100


# ─── Generic File I/O ────────────────────────────────────────────────────────

def _read_json(path: Path) -> Any:
    """Read JSON file, return empty dict on failure."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to read %s: %s", path, e)
    return {}


def _write_json(path: Path, data: Any) -> None:
    """Write JSON file atomically."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception as e:
        logger.error("Failed to write %s: %s", path, e)


# ─── Portfolio Storage ────────────────────────────────────────────────────────

def save_portfolio(user_id: str, goals: list[dict[str, Any]]) -> dict[str, Any]:
    """Save portfolio goals for a user."""
    with _lock:
        store = _read_json(PORTFOLIO_PATH)
        if not isinstance(store, dict):
            store = {}
        store[user_id] = {
            "goals": goals,
            "updated_at": _now_iso(),
        }
        _write_json(PORTFOLIO_PATH, store)
    return {"status": "saved", "goal_count": len(goals)}


def load_portfolio(user_id: str) -> dict[str, Any]:
    """Load portfolio goals for a user."""
    store = _read_json(PORTFOLIO_PATH)
    if isinstance(store, dict) and user_id in store:
        entry = store[user_id]
        return {
            "goals": entry.get("goals", []),
            "updated_at": entry.get("updated_at", ""),
        }
    return {"goals": [], "updated_at": ""}


# ─── Chat History Storage ─────────────────────────────────────────────────────

def save_chat_history(
    session_id: str, messages: list[dict[str, Any]]
) -> dict[str, Any]:
    """Save chat messages for a session."""
    with _lock:
        store = _read_json(CHAT_HISTORY_PATH)
        if not isinstance(store, dict):
            store = {}
        # Trim to max
        trimmed = messages[-MAX_CHAT_MESSAGES_PER_SESSION:]
        store[session_id] = {
            "messages": trimmed,
            "updated_at": _now_iso(),
        }
        # Limit total sessions stored (keep last 50)
        if len(store) > 50:
            sorted_sessions = sorted(
                store.items(),
                key=lambda x: x[1].get("updated_at", ""),
                reverse=True,
            )
            store = dict(sorted_sessions[:50])
        _write_json(CHAT_HISTORY_PATH, store)
    return {"status": "saved", "message_count": len(trimmed)}


def load_chat_history(session_id: str) -> dict[str, Any]:
    """Load chat messages for a session."""
    store = _read_json(CHAT_HISTORY_PATH)
    if isinstance(store, dict) and session_id in store:
        entry = store[session_id]
        return {
            "messages": entry.get("messages", []),
            "updated_at": entry.get("updated_at", ""),
        }
    return {"messages": [], "updated_at": ""}


def _now_iso() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
