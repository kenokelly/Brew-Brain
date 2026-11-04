"""
Autopilot journal: a timestamped log of what the system noticed and did.

Written by every alert path (via send_telegram_message), by the schedule/phase
tracker, and by manual actions. Read by the beta dashboard's journal card.

Stored as JSON in DATA_DIR so the web app, celery-worker and celery-beat
(separate processes sharing the /data volume) all see the same log; writes
take an flock and replace the file atomically.
"""

import fcntl
import json
import logging
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)

MAX_ENTRIES = 300
DEDUPE_MINUTES = 30


def _paths() -> tuple[str, str]:
    from core.config import DATA_DIR
    # Override lets the test suite keep journal writes out of the real data dir
    base = os.environ.get("BREW_BRAIN_JOURNAL_DIR") or DATA_DIR
    return os.path.join(base, "journal.json"), os.path.join(base, "journal.lock")


@contextmanager
def _locked() -> Iterator[None]:
    _, lock_path = _paths()
    with open(lock_path, "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _read() -> Dict[str, Any]:
    path, _ = _paths()
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("entries", [])
            data.setdefault("state", {})
            return data
    except (OSError, ValueError):
        pass
    return {"entries": [], "state": {}}


def _write(data: Dict[str, Any]) -> None:
    path, _ = _paths()
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix="journal_tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


_MD = re.compile(r"[*_`]")


def _clean(text: str) -> str:
    """Telegram markdown -> one plain line."""
    return " ".join(_MD.sub("", text).split())


def add_entry(text: str, kind: str = "info", level: str = "info",
              dedupe_minutes: int = DEDUPE_MINUTES) -> Optional[Dict[str, Any]]:
    """Append an entry. Returns it, or None if an identical one was logged
    within `dedupe_minutes` (keeps repeat alerts from flooding the log)."""
    text = _clean(text)
    if not text:
        return None
    now = datetime.now(timezone.utc)
    try:
        with _locked():
            data = _read()
            for e in data["entries"][:20]:
                if e.get("text") == text:
                    age = (now - datetime.fromisoformat(e["ts"])).total_seconds() / 60
                    if age < dedupe_minutes:
                        return None
                    break
            entry = {"id": uuid.uuid4().hex[:12], "ts": now.isoformat(),
                     "kind": kind, "level": level, "text": text}
            data["entries"] = [entry] + data["entries"][:MAX_ENTRIES - 1]
            _write(data)
            return entry
    except Exception as e:
        logger.warning(f"Journal write failed: {e}")
        return None


def list_entries(limit: int = 50) -> List[Dict[str, Any]]:
    return _read()["entries"][:max(1, min(limit, MAX_ENTRIES))]


def get_state(key: str) -> Any:
    return _read()["state"].get(key)


def set_state(key: str, value: Any) -> None:
    try:
        with _locked():
            data = _read()
            data["state"][key] = value
            _write(data)
    except Exception as e:
        logger.warning(f"Journal state write failed: {e}")


def level_for_message(text: str) -> str:
    """Rough severity from the alert text so the UI can colour it."""
    t = text.upper()
    if any(k in t for k in ("STALL", "RUNAWAY", "SIGNAL LOSS", "ANOMALY", "CRITICAL", "OFFLINE")):
        return "critical"
    if any(k in t for k in ("TEMP", "WARM", "COLD", "DRIFT", "HIGH", "LOW", "⚠")):
        return "warning"
    return "info"
