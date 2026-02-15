"""Tests for the audit logging module."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from escalation.audit import export_audit_log, read_audit_log, record_query


def _make_policies(tmp_path: Path, *, enabled: bool = True) -> dict:
    """Build a policies dict with audit output pointing at tmp_path."""
    return {
        "audit": {
            "enabled": enabled,
            "output": str(tmp_path / "audit_logs"),
            "format": "jsonl",
        }
    }


def _audit_file(tmp_path: Path) -> Path:
    return tmp_path / "audit_logs" / "audit.jsonl"


# ── record / read tests ───────────────────────────────────────────────────


def test_record_and_read(tmp_path: Path):
    """Writing 2 entries then reading should return exactly 2 entries."""
    policies = _make_policies(tmp_path)

    record_query("resolve", "svc-a", 3, policies)
    record_query("whois", "svc-b", 1, policies)

    entries = read_audit_log(_audit_file(tmp_path))

    assert len(entries) == 2
    assert entries[0]["action"] == "resolve"
    assert entries[0]["query"] == "svc-a"
    assert entries[1]["action"] == "whois"
    assert entries[1]["query"] == "svc-b"


def test_record_disabled(tmp_path: Path):
    """When audit is disabled, no file should be created."""
    policies = _make_policies(tmp_path, enabled=False)

    record_query("resolve", "svc-a", 3, policies)

    assert not _audit_file(tmp_path).exists()


def test_read_empty_log(tmp_path: Path):
    """Reading a non-existent log file should return an empty list."""
    entries = read_audit_log(tmp_path / "does_not_exist.jsonl")

    assert entries == []


# ── export tests ───────────────────────────────────────────────────────────


def test_export_json(tmp_path: Path):
    """Export to JSON: output should be parseable and contain the entry."""
    policies = _make_policies(tmp_path)
    record_query("resolve", "payments-api", 3, policies)

    entries = read_audit_log(_audit_file(tmp_path))
    output = export_audit_log(entries, fmt="json")

    parsed = json.loads(output)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["query"] == "payments-api"


def test_export_csv(tmp_path: Path):
    """Export to CSV: output should contain headers and data rows."""
    policies = _make_policies(tmp_path)
    record_query("resolve", "payments-api", 3, policies)

    entries = read_audit_log(_audit_file(tmp_path))
    output = export_audit_log(entries, fmt="csv")

    reader = csv.reader(io.StringIO(output))
    rows = list(reader)

    # First row is the header
    assert "action" in rows[0]
    assert "query" in rows[0]
    # Second row contains the data
    assert "payments-api" in rows[1]


def test_audit_entry_has_expected_fields(tmp_path: Path):
    """Each audit entry must contain timestamp, user, hostname, result_levels."""
    policies = _make_policies(tmp_path)
    record_query("resolve", "svc-z", 5, policies)

    entries = read_audit_log(_audit_file(tmp_path))
    entry = entries[0]

    assert "timestamp" in entry
    assert "user" in entry
    assert "hostname" in entry
    assert "result_levels" in entry
    assert entry["result_levels"] == 5
