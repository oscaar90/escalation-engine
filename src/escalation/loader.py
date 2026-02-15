"""YAML registry loader and validator."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from escalation.models import (
    Policies,
    PoliciesRegistry,
    Service,
    ServicesRegistry,
    Team,
    TeamsRegistry,
)

_cache: dict[str, Registry] = {}

REQUIRED_FILES = ("services.yaml", "teams.yaml", "policies.yaml")


class RegistryError(Exception):
    """Exception raised for errors during registry loading or validation."""


class Registry:
    """Container for a fully loaded and validated registry."""

    def __init__(
        self, services: list[Service], teams: list[Team], policies: Policies
    ) -> None:
        self.services = {s.id: s for s in services}
        self.teams = {t.id: t for t in teams}
        self.policies = policies

    def get_service(self, service_id: str) -> Service | None:
        return self.services.get(service_id)

    def get_team(self, team_id: str) -> Team | None:
        return self.teams.get(team_id)


def load_registry(registry_path: Path = Path("registry")) -> Registry:
    """Load, parse, validate and cache the YAML registry.

    Args:
        registry_path: Path to the directory containing the registry YAML files.

    Returns:
        A fully loaded Registry instance.

    Raises:
        RegistryError: If files are missing or validation fails.
    """
    resolved = str(registry_path.resolve())

    if resolved in _cache:
        return _cache[resolved]

    # Check that all required files exist
    missing = [f for f in REQUIRED_FILES if not (registry_path / f).is_file()]
    if missing:
        raise RegistryError(
            f"Missing registry files in {registry_path}: {', '.join(missing)}"
        )

    # Load and validate each YAML file
    try:
        with open(registry_path / "services.yaml") as f:
            services_data = yaml.safe_load(f)
        services_reg = ServicesRegistry.model_validate(services_data)
    except ValidationError as e:
        raise RegistryError(f"Invalid services.yaml: {e}") from e

    try:
        with open(registry_path / "teams.yaml") as f:
            teams_data = yaml.safe_load(f)
        teams_reg = TeamsRegistry.model_validate(teams_data)
    except ValidationError as e:
        raise RegistryError(f"Invalid teams.yaml: {e}") from e

    try:
        with open(registry_path / "policies.yaml") as f:
            policies_data = yaml.safe_load(f)
        policies_reg = PoliciesRegistry.model_validate(policies_data)
    except ValidationError as e:
        raise RegistryError(f"Invalid policies.yaml: {e}") from e

    registry = Registry(
        services=services_reg.services,
        teams=teams_reg.teams,
        policies=policies_reg.policies,
    )

    _cache[resolved] = registry
    return registry


def clear_cache() -> None:
    """Clear the in-memory registry cache."""
    _cache.clear()


def validate_registry(registry: Registry) -> list[str]:
    """Validate cross-references within a loaded registry.

    Returns a list of error messages. An empty list means all references are valid.
    """
    errors: list[str] = []
    team_ids = set(registry.teams.keys())

    # Validate service references
    for service in registry.services.values():
        if service.owner_team not in team_ids:
            errors.append(
                f"Service '{service.id}': owner_team '{service.owner_team}' "
                f"not found in teams"
            )
        for team_id in service.escalation_chain:
            if team_id not in team_ids:
                errors.append(
                    f"Service '{service.id}': escalation_chain references "
                    f"unknown team '{team_id}'"
                )

    # Validate team contacts
    for team in registry.teams.values():
        if not team.contacts:
            errors.append(f"Team '{team.id}': has no contacts")
        elif not any(c.role == "primary" for c in team.contacts):
            errors.append(f"Team '{team.id}': has no contact with role 'primary'")

    # Validate policies references
    if registry.policies.fallback_team not in team_ids:
        errors.append(
            f"Policies: fallback_team '{registry.policies.fallback_team}' "
            f"not found in teams"
        )

    return errors
