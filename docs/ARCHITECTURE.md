# Architecture

## Overview

The Incident Escalation Engine is a CLI tool that resolves on-call escalation chains from a YAML-based service registry. It is designed to be fast, deterministic, and entirely offline — no network calls, no database, no external services. The entire system runs from a single `escalation` command backed by validated YAML files that live in version control alongside the code they describe.

The architecture follows a layered pipeline: CLI parses input, the Loader reads and validates the registry, the Resolver builds the escalation chain, Output formats the result for the terminal, and Audit logs the query for compliance.

## Components

### CLI (`src/escalation/cli.py`)

The entry point. Built on Typer, it exposes five commands (`resolve-cmd`, `whois-cmd`, `list`, `validate`, `audit show/export`). The CLI layer handles argument parsing, error display, and exit codes. It contains no business logic — it delegates everything to the Resolver and Loader, then passes results to the Output layer.

### Models (`src/escalation/models.py`)

Pydantic models that define the schema for all data structures: `Service`, `Team`, `Contact`, `Policies`, `EscalationStep`, and `EscalationResult`. These models serve as both validation schemas (when loading YAML) and typed data containers (when passing data between components). The models enforce invariants like valid tier values (`P1`/`P2`/`P3`), positive SLA minutes, and contact role constraints.

### Loader (`src/escalation/loader.py`)

Responsible for reading the three YAML files (`services.yaml`, `teams.yaml`, `policies.yaml`), parsing them, and validating them against the Pydantic models. The Loader also performs cross-reference validation: checking that every team referenced in a service's escalation chain exists, that every team has a primary contact, and that the fallback team is defined. Results are cached in memory by resolved path, so repeated calls within the same process reuse the validated registry.

### Resolver (`src/escalation/resolver.py`)

The core business logic. Given a service ID, the Resolver looks up the service, walks its escalation chain, appends the fallback team if not already present, and builds an ordered list of `EscalationStep` objects. For each step, it selects the primary contact, picks the appropriate communication channel based on service tier (P1 → phone, P2/P3 → slack/email), and calculates the remaining SLA budget. The Resolver has no side effects beyond triggering an audit entry.

### Output (`src/escalation/output.py`)

Formatting layer built on Rich. Renders escalation chains as color-coded tables with SLA warnings (red when SLA is breached, yellow when close), service lists, whois panels, and validation results. Also supports JSON output for scripting and piping to other tools. The Output layer is purely presentational — it receives finished data structures and renders them.

### Audit (`src/escalation/audit.py`)

Append-only JSONL logging. Every `resolve` and `whois` query is recorded with timestamp, action, query, result count, username, and hostname. The audit system is non-blocking — if it fails (permissions, disk full), the main operation still completes. Entries can be viewed with `audit show` or exported to JSON/CSV with `audit export` for shipping to observability platforms.

## Data Flow

```
User runs command
        │
        ▼
   ┌─────────┐
   │   CLI    │  Parse args, route to handler
   └────┬─────┘
        │
        ▼
   ┌─────────┐    ┌──────────────────┐
   │ Loader   │───▶│ YAML Registry    │
   │          │    │ (services.yaml,  │
   │ validate │    │  teams.yaml,     │
   │ + cache  │    │  policies.yaml)  │
   └────┬─────┘    └──────────────────┘
        │
        ▼
   ┌──────────┐
   │ Resolver  │  Build chain, pick contacts/channels, calc SLA
   └──┬────┬──┘
      │    │
      ▼    ▼
┌────────┐ ┌───────┐
│ Output │ │ Audit │
│ (Rich) │ │(JSONL)│
└────────┘ └───────┘
```

## Key Invariants

- **Registry is read-only at runtime.** Once loaded and validated, the registry is never mutated. It is cached as an immutable snapshot. To pick up changes, the cache must be explicitly cleared (which the CLI does on every invocation).
- **Validation before use.** YAML is validated against Pydantic models at load time. Cross-reference checks (team existence, primary contacts, fallback team) run before the data is used. Malformed registries fail fast with clear error messages — never at 3AM during a real incident.
- **Audit is non-blocking.** The audit subsystem must never prevent the primary operation from completing. If audit logging fails for any reason, the escalation chain is still resolved and displayed.
- **No network dependencies.** The entire system operates from local YAML files. No API calls, no database connections, no DNS resolution. This is a deliberate choice for environments where network access may be degraded during the very incidents you are trying to respond to.
