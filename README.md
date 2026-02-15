# Incident Escalation Engine

> When a P1 hits at 3AM and the SLA is already ticking,
> you shouldn't be searching a spreadsheet for who to call.

## The Problem

In large organizations — especially in regulated environments like banking and financial services — incident response is only as fast as your ability to find the right person. CMDBs are outdated within weeks of deployment. Internal wikis go stale the moment someone changes teams. Slack channels fill with noise, and the on-call engineer scrolling through pinned messages at 3AM is burning SLA minutes before they even start troubleshooting.

When a critical payments service goes down in the middle of the night, the on-call engineer shouldn't have to wonder who owns it, who to escalate to, or what channel to use. They need a single command that resolves the full escalation chain — with names, phone numbers, and Slack handles — in under a second. Every minute spent searching is a minute not spent fixing.

This tool was born from real experience in Tier-1 banking environments, where the gap between "incident detected" and "right person engaged" was consistently the longest phase of incident response. Not because people were slow, but because the information was scattered across systems that were never designed for 3AM urgency. The Incident Escalation Engine replaces that chaos with a deterministic, version-controlled, CLI-first workflow that an on-call engineer can run from any terminal, anywhere, with zero network dependencies.

## What It Does

- **Resolve escalation chains** — Given a service ID, returns the full ordered escalation path with contacts, channels, and SLA countdown at each level.
- **Ownership lookup** — Instant `whois` for any service: who is the primary on-call, what team, and how to reach them.
- **Registry validation** — Validates all YAML configuration for structural integrity and cross-reference consistency before it can cause a problem at 3AM.
- **Audit trail** — Every query is logged to an append-only JSONL file with timestamp, user, hostname, and action — ready for compliance review or shipping to your observability stack.

## Quick Start

```bash
# Install in development mode
pip install -e .

# Resolve the full escalation chain for a service
escalation resolve-cmd payments-api

# Get JSON output for scripting / piping
escalation resolve-cmd payments-api --json

# Quick lookup: who owns this service right now?
escalation whois-cmd auth-service

# List all registered services
escalation list

# Validate registry integrity (run this in CI)
escalation validate

# View the audit trail
escalation audit show
```

## Architecture

```
CLI (Typer) → Resolver (core) → Loader (validate) → YAML Registry
     ↓               ↓
  Output (Rich)    Audit (JSONL)
```

1. **CLI** receives the command and parses arguments via Typer.
2. **Loader** reads the three YAML files (`services.yaml`, `teams.yaml`, `policies.yaml`), validates them against Pydantic models, and caches the result in memory.
3. **Resolver** looks up the service, builds the escalation chain by walking the team references, selects the appropriate contact channel based on service tier, and calculates SLA remaining at each escalation level.
4. **Output** renders the result as a Rich table (or JSON) to the terminal.
5. **Audit** appends a JSONL entry with the query metadata — non-blocking, append-only, zero external dependencies.

For a deeper dive, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Configuration

The registry consists of three YAML files in a single directory:

| File | Purpose |
|------|---------|
| `services.yaml` | Service definitions: ID, name, tier (P1/P2/P3), owner team, escalation chain, SLA |
| `teams.yaml` | Team definitions: ID, name, contacts with roles and channels |
| `policies.yaml` | Global policies: default SLA, escalation timeout, fallback team, audit settings |

A complete working example is available in [`examples/bank_scenario/`](examples/bank_scenario/).

**Channel selection logic:** The resolver automatically picks the best contact channel based on service tier:

- **P1 (critical)** → `phone` — When a payments service is down, you call someone.
- **P2 (high)** → `slack` — Fast but less intrusive for non-critical incidents.
- **P3 (medium)** → `slack` or `email` — Async channels for lower-priority issues.

You can point the CLI at any registry directory using `--registry`:

```bash
escalation resolve-cmd payments-api --registry examples/bank_scenario
```

## Design Decisions & Trade-offs

Every architectural choice in this project was made deliberately. The reasoning is documented as Architecture Decision Records in [docs/DECISIONS.md](docs/DECISIONS.md).

## What I Didn't Build — And Why

Equally important to what this tool does is what it deliberately does not do. Each exclusion is an intentional design choice, not a TODO. See [docs/WHAT_I_DID_NOT_BUILD.md](docs/WHAT_I_DID_NOT_BUILD.md).

## Development

```bash
# Install with dev dependencies (pytest, ruff, mypy)
make dev

# Run the test suite
make test

# Lint and type-check
make lint

# Auto-format code
make format
```

## License

MIT — see [LICENSE](LICENSE).
