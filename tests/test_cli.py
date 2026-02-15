"""Integration tests for the CLI interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from escalation.cli import app
from escalation.loader import clear_cache

runner = CliRunner()

REGISTRY_PATH = str(Path(__file__).parent.parent / "registry")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Run every CLI test inside tmp_path so audit logs don't leak."""
    clear_cache()
    monkeypatch.chdir(tmp_path)
    yield
    clear_cache()


# ── resolve-cmd ────────────────────────────────────────────────────────────


def test_resolve_table_output():
    """resolve-cmd with table output should succeed and show key data."""
    result = runner.invoke(app, ["resolve-cmd", "payments-api", "--registry", REGISTRY_PATH])

    assert result.exit_code == 0
    assert "Platform Core" in result.output
    assert "Escalation Chain" in result.output


def test_resolve_json_output():
    """resolve-cmd --json should produce parseable JSON with correct service."""
    result = runner.invoke(
        app, ["resolve-cmd", "payments-api", "--json", "--registry", REGISTRY_PATH]
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["service"]["id"] == "payments-api"


def test_resolve_with_level():
    """--level 1 with --json should return exactly one step at level 1."""
    result = runner.invoke(
        app,
        [
            "resolve-cmd",
            "payments-api",
            "--json",
            "--level",
            "1",
            "--registry",
            REGISTRY_PATH,
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["chain"]) == 1
    assert data["chain"][0]["level"] == 1


def test_resolve_unknown_service():
    """Resolving an unknown service should exit 1 and mention 'not found'."""
    result = runner.invoke(
        app, ["resolve-cmd", "nope", "--registry", REGISTRY_PATH]
    )

    assert result.exit_code == 1
    assert "not found" in result.output


# ── whois-cmd ──────────────────────────────────────────────────────────────


def test_whois():
    """whois-cmd should show the primary contact name."""
    result = runner.invoke(
        app, ["whois-cmd", "payments-api", "--registry", REGISTRY_PATH]
    )

    assert result.exit_code == 0
    assert "Ana García" in result.output


# ── list ───────────────────────────────────────────────────────────────────


def test_list():
    """list should display services with tiers."""
    result = runner.invoke(app, ["list", "--registry", REGISTRY_PATH])

    assert result.exit_code == 0
    assert "payments-api" in result.output
    assert "P1" in result.output


# ── validate ───────────────────────────────────────────────────────────────


def test_validate():
    """validate on the real registry should pass."""
    result = runner.invoke(app, ["validate", "--registry", REGISTRY_PATH])

    assert result.exit_code == 0
    assert "passed" in result.output


# ── audit ──────────────────────────────────────────────────────────────────


def test_audit_show_empty():
    """audit show with no prior entries should succeed with 'No audit entries'."""
    result = runner.invoke(app, ["audit", "show"])

    assert result.exit_code == 0
    assert "No audit entries" in result.output


def test_audit_show_after_resolve():
    """After a resolve, audit show should contain 'resolve'."""
    runner.invoke(
        app, ["resolve-cmd", "payments-api", "--registry", REGISTRY_PATH]
    )
    result = runner.invoke(app, ["audit", "show"])

    assert result.exit_code == 0
    assert "resolve" in result.output


def test_audit_export_json():
    """After a resolve, audit export --format json should produce valid JSON."""
    runner.invoke(
        app, ["resolve-cmd", "payments-api", "--registry", REGISTRY_PATH]
    )
    result = runner.invoke(app, ["audit", "export", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1
