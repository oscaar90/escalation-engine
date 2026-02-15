"""Rich output formatting for CLI results."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from escalation.models import EscalationResult, Service

console = Console()

TIER_COLORS: dict[str, str] = {
    "P1": "red bold",
    "P2": "yellow",
    "P3": "green",
}


def render_escalation(
    result: EscalationResult, level: int | None = None
) -> None:
    """Render the escalation chain as a Rich table.

    Args:
        result: The resolved escalation result.
        level: If provided, show only this escalation level.
    """
    service = result.service
    tier_style = TIER_COLORS.get(service.tier, "white")

    # Build header text
    header_text = Text()
    header_text.append("Escalation Chain: ")
    header_text.append(service.name)
    header_text.append(" [")
    header_text.append(service.tier, style=tier_style)
    header_text.append("]")

    # Filter chain if level is specified
    steps = result.chain
    if level is not None:
        steps = [s for s in steps if s.level == level]

    # Build table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Level", justify="center", width=7)
    table.add_column("Team", min_width=20)
    table.add_column("Contact", min_width=18)
    table.add_column("Role", width=10)
    table.add_column("Channel", min_width=25)
    table.add_column("SLA Left", justify="right", width=10)

    for step in steps:
        # Color SLA remaining
        sla = step.sla_remaining
        if sla <= 0:
            sla_style = "red"
        elif sla <= 5:
            sla_style = "yellow"
        else:
            sla_style = "green"

        sla_text = Text(f"{sla} min", style=sla_style)

        table.add_row(
            str(step.level),
            step.team.name,
            step.contact.name,
            step.contact.role,
            step.channel,
            sla_text,
        )

    # Render panel with table inside
    panel = Panel(table, title=header_text, border_style="blue")
    console.print(panel)

    # Footer with timestamp
    console.print(
        Text(f"  Timestamp: {result.timestamp}", style="dim"),
    )


def render_escalation_json(
    result: EscalationResult, level: int | None = None
) -> None:
    """Output the escalation result as formatted JSON.

    Args:
        result: The resolved escalation result.
        level: If provided, filter the chain to only this level.
    """
    data = result.model_dump()
    if level is not None:
        data["chain"] = [s for s in data["chain"] if s["level"] == level]
    console.print_json(json.dumps(data))


def render_service_list(services: list[Service]) -> None:
    """Render a table of registered services.

    Args:
        services: List of Service models to display.
    """
    # Sort by tier then id
    sorted_services = sorted(services, key=lambda s: (s.tier, s.id))

    table = Table(title="Registered Services", show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Tier")
    table.add_column("Owner Team")
    table.add_column("SLA (min)")

    for svc in sorted_services:
        tier_style = TIER_COLORS.get(svc.tier, "white")
        tier_text = Text(svc.tier, style=tier_style)
        table.add_row(
            svc.id,
            svc.name,
            tier_text,
            svc.owner_team,
            str(svc.sla_minutes),
        )

    console.print(table)


def render_whois(
    contact_name: str, team_name: str, channels: dict[str, str]
) -> None:
    """Render a whois panel for a primary contact.

    Args:
        contact_name: Name of the primary contact.
        team_name: Name of the owning team.
        channels: Dictionary of channel type to channel value.
    """
    content = Text()
    content.append(contact_name, style="bold")
    content.append(f"  ({team_name})\n")

    for ch_type, ch_value in channels.items():
        content.append(f"  {ch_type}", style="dim")
        content.append(f"  {ch_value}\n")

    panel = Panel(content, title="Primary Owner", border_style="cyan")
    console.print(panel)


def render_validation_errors(errors: list[str]) -> None:
    """Render registry validation results.

    Args:
        errors: List of validation error messages. Empty means success.
    """
    if not errors:
        console.print(
            Text(
                "Registry validation passed — no errors found.",
                style="green bold",
            )
        )
        return

    console.print(
        Text(f"Validation failed with {len(errors)} error(s):", style="red bold")
    )
    for error in errors:
        console.print(Text(f"  • {error}", style="red"))


def render_audit_entries(entries: list[dict]) -> None:
    """Render audit log entries as a Rich table.

    Args:
        entries: List of audit entry dictionaries.
    """
    if not entries:
        console.print(Text("No audit entries found.", style="dim"))
        return

    table = Table(title="Audit Log", show_header=True, header_style="bold")
    table.add_column("Timestamp")
    table.add_column("Action")
    table.add_column("Query")
    table.add_column("Result Levels")
    table.add_column("User")
    table.add_column("Hostname")

    for entry in entries:
        table.add_row(
            str(entry.get("timestamp", "")),
            str(entry.get("action", "")),
            str(entry.get("query", "")),
            str(entry.get("result_levels", "")),
            str(entry.get("user", "")),
            str(entry.get("hostname", "")),
        )

    console.print(table)
