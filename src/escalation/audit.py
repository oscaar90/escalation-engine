"""Audit logging for escalation events."""

from __future__ import annotations

import csv
import getpass
import io
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_AUDIT_PATH = Path("./audit_logs/audit.jsonl")


def record_query(
    service_id: str,
    action: str,
    result: str,
    *,
    path: Path = DEFAULT_AUDIT_PATH,
) -> None:
    """Append an audit entry to the JSONL log file.

    Args:
        service_id: The service that was queried.
        action: The action performed (e.g. ``resolve``, ``whois``).
        result: Outcome of the action (e.g. ``success``).
        path: Path to the audit log file.
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "query": service_id,
        "levels": "",
        "result": result,
        "user": getpass.getuser(),
        "hostname": socket.gethostname(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_audit_log(path: Path = DEFAULT_AUDIT_PATH) -> list[dict]:
    """Read all entries from a JSONL audit log file.

    Args:
        path: Path to the audit log file.

    Returns:
        A list of audit entry dictionaries.
    """
    if not path.is_file():
        return []

    entries: list[dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def export_audit_log(entries: list[dict], fmt: str = "json") -> str:
    """Export audit entries to a string in the given format.

    Args:
        entries: List of audit entry dictionaries.
        fmt: Output format — ``"json"`` or ``"csv"``.

    Returns:
        The formatted string.
    """
    if fmt == "json":
        return json.dumps(entries, indent=2)

    # CSV format
    if not entries:
        return ""
    fieldnames = list(entries[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(entries)
    return output.getvalue()
