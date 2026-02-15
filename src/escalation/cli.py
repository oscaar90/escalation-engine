"""CLI interface for the escalation engine."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

from escalation.audit import export_audit_log, read_audit_log
from escalation.loader import RegistryError, clear_cache, load_registry, validate_registry
from escalation.output import (
    render_audit_entries,
    render_escalation,
    render_escalation_json,
    render_service_list,
    render_validation_errors,
    render_whois,
)
from escalation.resolver import ResolutionError, resolve, whois

console = Console()

app = typer.Typer(
    name="escalation",
    help="Incident Escalation Engine — resolve on-call chains fast.",
    no_args_is_help=True,
)

audit_app = typer.Typer(help="Audit trail commands.")
app.add_typer(audit_app, name="audit")

RegistryOption = Annotated[
    Path, typer.Option("--registry", "-r", help="Path to registry directory.")
]


@app.command("resolve-cmd")
def resolve_cmd(
    service_id: Annotated[str, typer.Argument(help="Service ID to resolve.")],
    registry: RegistryOption = Path("registry"),
    as_json: Annotated[
        bool, typer.Option("--json", help="Output as JSON.")
    ] = False,
    level: Annotated[
        Optional[int], typer.Option("--level", help="Show only this escalation level.")
    ] = None,
) -> None:
    """Resolve the escalation chain for a service."""
    try:
        clear_cache()
        result = resolve(service_id, registry_path=registry)
        if as_json:
            render_escalation_json(result, level=level)
        else:
            render_escalation(result, level=level)
    except (RegistryError, ResolutionError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("whois-cmd")
def whois_cmd(
    service_id: Annotated[str, typer.Argument(help="Service ID to look up.")],
    registry: RegistryOption = Path("registry"),
) -> None:
    """Look up the primary on-call owner for a service."""
    try:
        contact_name, team_name, channels = whois(
            service_id, registry_path=registry
        )
        render_whois(contact_name, team_name, channels)
    except (RegistryError, ResolutionError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("list")
def list_cmd(
    registry: RegistryOption = Path("registry"),
) -> None:
    """List all registered services."""
    try:
        reg = load_registry(registry)
        render_service_list(list(reg.services.values()))
    except RegistryError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command("validate")
def validate_cmd(
    registry: RegistryOption = Path("registry"),
) -> None:
    """Validate the registry for consistency errors."""
    try:
        reg = load_registry(registry)
        errors = validate_registry(reg)
        render_validation_errors(errors)
        if errors:
            raise typer.Exit(code=1)
    except RegistryError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)


@audit_app.command("show")
def audit_show(
    path: Annotated[
        Path, typer.Option("--path", help="Path to audit log file.")
    ] = Path("./audit_logs/audit.jsonl"),
) -> None:
    """Show audit log entries."""
    entries = read_audit_log(audit_path=path)
    render_audit_entries(entries)


@audit_app.command("export")
def audit_export(
    fmt: Annotated[
        str, typer.Option("--format", "-f", help="Export format: json or csv.")
    ] = "json",
    path: Annotated[
        Path, typer.Option("--path", help="Path to audit log file.")
    ] = Path("./audit_logs/audit.jsonl"),
) -> None:
    """Export audit log entries in JSON or CSV format."""
    entries = read_audit_log(audit_path=path)
    if not entries:
        console.print("[dim]No audit entries to export.[/dim]")
        raise typer.Exit(code=0)
    output = export_audit_log(entries, fmt=fmt)
    console.print(output)
