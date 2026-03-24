"""Shared state utilities for Recall memory persistence hooks.

All functions use stdlib only and handle missing files gracefully.
State files are stored in the project working directory.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

STATE_FILE = ".recall-session-state.json"
HANDOFF_FILE = ".recall-session-handoff.json"
BREADCRUMBS_FILE = ".recall-breadcrumbs.jsonl"


def _safe_read_json(path: str) -> dict[str, Any]:
    """Read a JSON file, returning empty dict on any error."""
    try:
        with open(path) as f:
            result: dict[str, Any] = json.load(f)
            return result
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _atomic_write_json(path: str, data: dict[str, Any]) -> None:
    """Write JSON atomically using tempfile + rename."""
    dir_name = os.path.dirname(path) or "."
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except OSError:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def read_state(working_dir: str) -> dict[str, Any]:
    """Read session state file."""
    return _safe_read_json(os.path.join(working_dir, STATE_FILE))


def write_state(working_dir: str, state: dict[str, Any]) -> None:
    """Write session state file atomically."""
    _atomic_write_json(os.path.join(working_dir, STATE_FILE), state)


def read_handoff(working_dir: str) -> dict[str, Any]:
    """Read previous session handoff. Returns empty dict if none."""
    return _safe_read_json(os.path.join(working_dir, HANDOFF_FILE))


def write_handoff(working_dir: str, data: dict[str, Any]) -> None:
    """Write session handoff file atomically."""
    _atomic_write_json(os.path.join(working_dir, HANDOFF_FILE), data)


def append_breadcrumb(working_dir: str, event: dict[str, Any]) -> None:
    """Append a milestone breadcrumb to the JSONL log."""
    path = os.path.join(working_dir, BREADCRUMBS_FILE)
    try:
        try:
            if os.path.getsize(path) > 100_000:
                _truncate_breadcrumbs(path)
        except OSError:
            pass
        with open(path, "a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        pass


def read_breadcrumbs(working_dir: str) -> list[dict[str, Any]]:
    """Read all breadcrumbs from JSONL log."""
    path = os.path.join(working_dir, BREADCRUMBS_FILE)
    breadcrumbs: list[dict[str, Any]] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        breadcrumbs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (FileNotFoundError, OSError):
        pass
    return breadcrumbs


def clear_breadcrumbs(working_dir: str) -> None:
    """Clear the breadcrumbs file."""
    path = os.path.join(working_dir, BREADCRUMBS_FILE)
    try:
        open(path, "w").close()  # noqa: SIM115
    except OSError:
        pass


def _truncate_breadcrumbs(path: str) -> None:
    """Keep only the last 50 breadcrumbs when file gets too large."""
    try:
        with open(path) as f:
            lines = f.readlines()
        with open(path, "w") as f:
            f.writelines(lines[-50:])
    except OSError:
        pass


def now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()
