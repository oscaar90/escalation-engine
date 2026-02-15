"""Tests for the escalation resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from escalation.loader import clear_cache, load_registry
from escalation.resolver import ResolutionError, resolve, whois

REGISTRY_PATH = Path(__file__).parent.parent / "registry"


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.fixture(autouse=True)
def _isolate_audit(monkeypatch, tmp_path):
    """Redirect audit logs to tmp_path so tests leave no state."""
    monkeypatch.chdir(tmp_path)


# ── resolve() tests ────────────────────────────────────────────────────────


def test_resolve_payments_api():
    """Resolve payments-api: verify service fields and chain structure."""
    result = resolve("payments-api", registry_path=REGISTRY_PATH)

    assert result.service.id == "payments-api"
    assert result.service.tier == "P1"
    assert len(result.chain) >= 3
    assert result.chain[0].team.id == "platform-core"


def test_resolve_includes_sla_countdown():
    """SLA remaining should decrease along the escalation chain."""
    result = resolve("payments-api", registry_path=REGISTRY_PATH)
    sla_values = [step.sla_remaining for step in result.chain]

    for i in range(1, len(sla_values)):
        assert sla_values[i] < sla_values[i - 1]


def test_resolve_unknown_service():
    """Resolving an unknown service must raise ResolutionError."""
    with pytest.raises(ResolutionError, match="not found"):
        resolve("nonexistent-service", registry_path=REGISTRY_PATH)


def test_resolve_p1_uses_phone():
    """For a P1 service, the first channel should contain 'phone'."""
    result = resolve("payments-api", registry_path=REGISTRY_PATH)

    assert "phone" in result.chain[0].channel


def test_resolve_fallback_appended():
    """auth-service should have sre-oncall appended as fallback."""
    result = resolve("auth-service", registry_path=REGISTRY_PATH)
    team_ids = [step.team.id for step in result.chain]

    assert "sre-oncall" in team_ids


def test_resolve_no_duplicate_fallback():
    """payments-api already has sre-oncall; it should not appear twice."""
    result = resolve("payments-api", registry_path=REGISTRY_PATH)
    team_ids = [step.team.id for step in result.chain]

    assert team_ids.count("sre-oncall") == 1


# ── whois() tests ──────────────────────────────────────────────────────────


def test_whois_returns_primary():
    """whois for payments-api should return Ana García from Platform Core."""
    name, team, channels = whois("payments-api", registry_path=REGISTRY_PATH)

    assert name == "Ana García"
    assert team == "Platform Core"
    assert "email" in channels


def test_whois_unknown_service():
    """whois on an unknown service must raise ResolutionError."""
    with pytest.raises(ResolutionError):
        whois("nonexistent-service", registry_path=REGISTRY_PATH)


# ── pre-loaded registry test ──────────────────────────────────────────────


def test_resolve_with_preloaded_registry():
    """Passing a pre-loaded registry should work identically."""
    registry = load_registry(REGISTRY_PATH)
    result = resolve("payments-api", registry=registry)

    assert result.service.id == "payments-api"
    assert len(result.chain) >= 3
