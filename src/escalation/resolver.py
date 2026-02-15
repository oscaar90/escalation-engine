"""Escalation chain resolver logic."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from escalation.loader import Registry, load_registry
from escalation.models import (
    Contact,
    EscalationResult,
    EscalationStep,
    Policies,
)


class ResolutionError(Exception):
    """Exception raised for errors during escalation resolution."""


def _pick_channel(tier: str, channels: dict[str, str]) -> str:
    """Select the recommended contact channel based on service tier.

    - P1 → phone (critical incident, immediate human contact)
    - P2/P3 → slack if available, otherwise email
    - Fallback: first available channel
    """
    if tier == "P1":
        if "phone" in channels:
            return f"phone: {channels['phone']}"
    else:
        if "slack" in channels:
            return f"slack: {channels['slack']}"
        if "email" in channels:
            return f"email: {channels['email']}"

    # Fallback: first available channel
    key = next(iter(channels))
    return f"{key}: {channels[key]}"


def _pick_primary(contacts: list[Contact]) -> Contact:
    """Select the primary contact, or the first contact if none is primary."""
    for c in contacts:
        if c.role == "primary":
            return c
    return contacts[0]


def _load_registry(
    registry: Registry | None, registry_path: Path | None
) -> Registry:
    """Load registry if not already provided."""
    if registry is not None:
        return registry
    return load_registry(registry_path or Path("registry"))


def _record_audit(
    action: str, query: str, result_levels: int, policies: Policies
) -> None:
    """Attempt to record an audit entry, silently ignoring if audit is unavailable."""
    try:
        from escalation.audit import record_query

        policies_dict = {
            "audit": {
                "enabled": policies.audit.get("enabled", False),
                "output": policies.audit.get("output", "./audit_logs/"),
                "format": policies.audit.get("format", "jsonl"),
            }
        }
        record_query(action, query, result_levels, policies_dict)
    except (ImportError, AttributeError):
        pass


def resolve(
    service_id: str,
    registry: Registry | None = None,
    registry_path: Path | None = None,
) -> EscalationResult:
    """Resolve the full escalation chain for a service.

    Args:
        service_id: The ID of the service to resolve.
        registry: An optional pre-loaded Registry instance.
        registry_path: Path to the registry directory (default: ``Path("registry")``).

    Returns:
        An ``EscalationResult`` containing the ordered escalation chain.

    Raises:
        ResolutionError: If the service or any referenced team is not found.
    """
    reg = _load_registry(registry, registry_path)

    # Look up the service
    service = reg.get_service(service_id)
    if service is None:
        available = ", ".join(sorted(reg.services.keys()))
        raise ResolutionError(
            f"Service '{service_id}' not found. "
            f"Available services: {available}"
        )

    timeout = reg.policies.escalation_timeout_minutes

    # Build escalation chain
    chain_team_ids = list(service.escalation_chain)

    # Append fallback team if not already in the chain
    fallback_id = reg.policies.fallback_team
    if fallback_id not in chain_team_ids:
        chain_team_ids.append(fallback_id)

    steps: list[EscalationStep] = []
    for idx, team_id in enumerate(chain_team_ids):
        team = reg.get_team(team_id)
        if team is None:
            raise ResolutionError(
                f"Team '{team_id}' referenced in escalation chain "
                f"for service '{service_id}' not found"
            )

        contact = _pick_primary(team.contacts)
        channel = _pick_channel(service.tier, contact.channels)
        sla_remaining = service.sla_minutes - (timeout * idx)

        steps.append(
            EscalationStep(
                level=idx + 1,
                team=team,
                contact=contact,
                channel=channel,
                sla_remaining=sla_remaining,
            )
        )

    result = EscalationResult(
        service=service,
        chain=steps,
        timestamp=datetime.now(UTC).isoformat(),
        query=service_id,
    )

    _record_audit("resolve", service_id, len(steps), reg.policies)

    return result


def whois(
    service_id: str,
    registry: Registry | None = None,
    registry_path: Path | None = None,
) -> tuple[str, str, dict[str, str]]:
    """Quick lookup of the primary contact for a service's owner team.

    Args:
        service_id: The ID of the service to look up.
        registry: An optional pre-loaded Registry instance.
        registry_path: Path to the registry directory (default: ``Path("registry")``).

    Returns:
        A tuple of ``(contact_name, team_name, channels)``.

    Raises:
        ResolutionError: If the service or owner team is not found.
    """
    reg = _load_registry(registry, registry_path)

    service = reg.get_service(service_id)
    if service is None:
        available = ", ".join(sorted(reg.services.keys()))
        raise ResolutionError(
            f"Service '{service_id}' not found. "
            f"Available services: {available}"
        )

    team = reg.get_team(service.owner_team)
    if team is None:
        raise ResolutionError(
            f"Owner team '{service.owner_team}' for service "
            f"'{service_id}' not found"
        )

    contact = _pick_primary(team.contacts)

    _record_audit("whois", service_id, 1, reg.policies)

    return (contact.name, team.name, dict(contact.channels))
