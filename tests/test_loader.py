"""Tests for the registry loader and validator."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from escalation.loader import (
    Registry,
    RegistryError,
    clear_cache,
    load_registry,
    validate_registry,
)

REGISTRY_PATH = Path(__file__).parent.parent / "registry"


@pytest.fixture(autouse=True)
def _clear_loader_cache():
    """Clear the registry cache before and after every test."""
    clear_cache()
    yield
    clear_cache()


# ── Success tests using the real registry ──────────────────────────────────


def test_load_registry_success():
    """Load the real registry and verify key services and teams exist."""
    registry = load_registry(REGISTRY_PATH)

    assert "payments-api" in registry.services
    assert "platform-core" in registry.teams


def test_load_registry_caching():
    """Loading the same path twice must return the exact same instance."""
    first = load_registry(REGISTRY_PATH)
    second = load_registry(REGISTRY_PATH)

    assert first is second


# ── Error tests using tmp_path ─────────────────────────────────────────────


def test_load_missing_directory(tmp_path: Path):
    """An empty directory must raise RegistryError about missing files."""
    with pytest.raises(RegistryError, match="Missing registry file"):
        load_registry(tmp_path)


def test_load_invalid_yaml(tmp_path: Path):
    """A service YAML with missing required fields must raise RegistryError."""
    # Write a services.yaml missing required fields
    (tmp_path / "services.yaml").write_text(
        yaml.dump({"services": [{"id": "bad-service"}]})
    )
    (tmp_path / "teams.yaml").write_text(yaml.dump({"teams": []}))
    (tmp_path / "policies.yaml").write_text(
        yaml.dump(
            {
                "policies": {
                    "audit": {"enabled": False, "output": "./audit/", "format": "jsonl"}
                }
            }
        )
    )

    with pytest.raises(RegistryError, match="Invalid services.yaml"):
        load_registry(tmp_path)


# ── Validation tests ───────────────────────────────────────────────────────


def test_validate_registry_ok():
    """The real registry should have no validation errors."""
    registry = load_registry(REGISTRY_PATH)
    errors = validate_registry(registry)

    assert errors == []


def test_validate_broken_owner_team(tmp_path: Path):
    """A service whose owner_team does not exist should produce an error."""
    services_data = {
        "services": [
            {
                "id": "svc-x",
                "name": "Service X",
                "tier": "P1",
                "owner_team": "ghost-team",
                "escalation_chain": ["team-a"],
                "sla_minutes": 15,
            }
        ]
    }
    teams_data = {
        "teams": [
            {
                "id": "team-a",
                "name": "Team A",
                "contacts": [
                    {
                        "name": "Alice",
                        "role": "primary",
                        "channels": {"email": "a@co.com"},
                    }
                ],
            }
        ]
    }
    policies_data = {
        "policies": {
            "fallback_team": "team-a",
            "audit": {"enabled": False, "output": "./audit/", "format": "jsonl"},
        }
    }

    (tmp_path / "services.yaml").write_text(yaml.dump(services_data))
    (tmp_path / "teams.yaml").write_text(yaml.dump(teams_data))
    (tmp_path / "policies.yaml").write_text(yaml.dump(policies_data))

    registry = load_registry(tmp_path)
    errors = validate_registry(registry)

    assert any("ghost-team" in e for e in errors)


def test_validate_missing_primary_contact(tmp_path: Path):
    """A team with no primary contact should produce a validation error."""
    services_data = {
        "services": [
            {
                "id": "svc-y",
                "name": "Service Y",
                "tier": "P2",
                "owner_team": "team-b",
                "escalation_chain": ["team-b"],
                "sla_minutes": 30,
            }
        ]
    }
    teams_data = {
        "teams": [
            {
                "id": "team-b",
                "name": "Team B",
                "contacts": [
                    {
                        "name": "Bob",
                        "role": "secondary",
                        "channels": {"email": "b@co.com"},
                    }
                ],
            }
        ]
    }
    policies_data = {
        "policies": {
            "fallback_team": "team-b",
            "audit": {"enabled": False, "output": "./audit/", "format": "jsonl"},
        }
    }

    (tmp_path / "services.yaml").write_text(yaml.dump(services_data))
    (tmp_path / "teams.yaml").write_text(yaml.dump(teams_data))
    (tmp_path / "policies.yaml").write_text(yaml.dump(policies_data))

    registry = load_registry(tmp_path)
    errors = validate_registry(registry)

    assert any("no contact with role 'primary'" in e for e in errors)
