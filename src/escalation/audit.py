"""Audit logging for escalation events."""

from __future__ import annotations

import csv
import getpass
import io
import json
import socket
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_AUDIT_PATH = Path("./audit_logs/audit.jsonl")


def _get_user() -> str:
    """Return the current username, or 'unknown' on failure."""
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def _get_hostname() -> str:
    """Return the current hostname, or 'unknown' on failure."""
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def record_query(
    action: str,
    query: str,
    result_levels: int,
    policies: dict,
) -> None:
    """Append an audit entry to the JSONL log file.

    Args:
        action: The action performed (e.g. ``resolve``, ``whois``).
        query: The service that was queried.
        result_levels: Number of escalation levels in the result.
        policies: The policies dict (must contain ``audit`` key).
    """
    audit_cfg = policies.get("audit", {})
    if not audit_cfg.get("enabled", False):
        return

    output_dir = Path(audit_cfg.get("output", "./audit_logs/"))
    output_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "query": query,
        "result_levels": result_levels,
        "user": _get_user(),
        "hostname": _get_hostname(),
    }

    audit_file = output_dir / "audit.jsonl"
    with open(audit_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_audit_log(audit_path: Path | None = None) -> list[dict]:
    """Read all entries from a JSONL audit log file.

    Args:
        audit_path: Path to the audit log file. Defaults to ``./audit_logs/audit.jsonl``.

    Returns:
        A list of audit entry dictionaries.
    """
    if audit_path is None:
        audit_path = DEFAULT_AUDIT_PATH

    if not audit_path.is_file():
        return []

    entries: list[dict] = []
    with open(audit_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def export_audit_log(entries: list[dict], fmt: str = "json") -> str:
    """Export audit entries to a string in the given format.

    Args:
        entries: List of audit entry dictionaries.
        fmt: Output format — ``"json"``, ``"csv"``, or anything else for JSONL.

    Returns:
        The formatted string.
    """
    if fmt == "json":
        return json.dumps(entries, indent=2)

    if fmt == "csv":
        if not entries:
            return ""
        fieldnames = list(entries[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(entries)
        return output.getvalue()

    # Fallback: JSONL (one JSON line per entry)
    return "\n".join(json.dumps(e) for e in entries)
