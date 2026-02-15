# Architecture Decision Records

## ADR-001: YAML as Source of Truth vs CMDB vs API

**Status:** Accepted

**Context:**
Escalation chain data needs to live somewhere. The typical options in large organizations are: (1) a CMDB like ServiceNow, (2) an internal API/microservice, or (3) flat files in version control. In regulated financial services environments, CMDBs are notoriously out of date — ownership fields go stale within weeks, and the friction of updating them means teams avoid doing it. Internal APIs add a network dependency at exactly the moment when the network may be the thing that is broken.

**Decision:**
Use YAML files stored in a git repository as the single source of truth for service ownership, team contacts, and escalation policies.

**Rationale:**
- **Versionable:** Every change to the escalation registry is a git commit with an author, a timestamp, and a diff. You can `git blame` to see who changed a contact and when. This is the audit trail that regulated environments require.
- **Auditable:** Pull requests provide a natural review process. Changes to on-call ownership go through the same code review workflow as code changes.
- **No infrastructure required:** No database to provision, no API to deploy, no credentials to manage. Clone the repo and you are ready.
- **Offline-capable:** YAML files work when the network is down. During a major incident, this matters.
- **In regulated environments, CMDBs are often unreliable.** Teams in large-scale financial infrastructure frequently maintain shadow spreadsheets because the CMDB does not reflect reality. YAML in git replaces the shadow spreadsheet with something that is actually version-controlled.

**Trade-offs:**
- No real-time updates — changes require a commit and pull. Acceptable because escalation chains do not change during an incident.
- No query language — you cannot run ad-hoc queries like you could against a database. Acceptable because the access patterns are simple and well-defined.
- Manual maintenance — someone has to keep the YAML files up to date. This is mitigated by validation in CI and the low friction of editing a YAML file vs updating a CMDB.

---

## ADR-002: CLI-First vs API-First

**Status:** Accepted

**Context:**
The tool needs an interface. The options are: (1) a REST/gRPC API that other systems call, (2) a web UI/dashboard, or (3) a CLI tool. The primary user is an on-call engineer who has just been paged at 3AM for a P1 incident.

**Decision:**
Build a CLI tool using Typer with Rich output formatting. No API, no web server.

**Rationale:**
- **At 3AM with a P1, you want a terminal, not a browser.** The on-call engineer is already in a terminal — they are SSH-ing into servers, tailing logs, checking metrics. A CLI command is the lowest-friction path to "who do I call."
- **Composable with Unix tools.** `escalation resolve-cmd payments-api --json | jq '.chain[0].contact'` works out of the box. Pipe it, grep it, feed it to other scripts. An API would require `curl` and JSON parsing just to get a phone number.
- **Zero deployment.** `pip install -e .` and you are running. No Docker, no Kubernetes, no port configuration, no service mesh, no load balancer. The tool runs on any machine with Python 3.11+.
- **Works offline.** No network required. No server to keep running. No health checks.

**Trade-offs:**
- Cannot be called programmatically from other services without shelling out. Acceptable because the primary consumer is a human, not a machine.
- No concurrent access or shared state. Acceptable because escalation lookups are stateless reads.

---

## ADR-003: JSONL for Audit vs Database

**Status:** Accepted

**Context:**
Every escalation query must be recorded for audit and compliance purposes. The options are: (1) a relational database, (2) a time-series database, (3) a log aggregation service, or (4) a local file.

**Decision:**
Write audit entries as JSONL (one JSON object per line) to a local file.

**Rationale:**
- **Zero dependencies.** No database to install, configure, or maintain. No connection strings, no migrations, no schema management.
- **Append-only.** JSONL is naturally append-only. Each entry is a self-contained JSON object on its own line. No risk of corrupting previous entries when writing new ones.
- **grep-friendly.** `grep "payments-api" audit.jsonl` finds every query for a service instantly. No query language needed for the common case.
- **Easy to ship to existing observability.** JSONL files can be tailed by Filebeat, Promtail, or Fluentd and shipped to ELK, Splunk, Loki, or any other log aggregation system the organization already runs. The audit system does not need to know about these integrations — it just writes a file.
- **Built-in export.** The `audit export` command can convert JSONL to JSON arrays or CSV for ad-hoc analysis.

**Trade-offs:**
- No built-in query capability beyond grep. Acceptable because the expected volume is low (human-initiated queries) and complex analysis can be done after shipping to an observability platform.
- No automatic rotation or retention. Acceptable because audit files grow slowly and standard log rotation tools (logrotate) can handle this externally.

---

## ADR-004: Pydantic for YAML Validation vs Raw Dict Access

**Status:** Accepted

**Context:**
YAML files parsed by PyYAML produce nested dictionaries. The options are: (1) access the dicts directly with `data["key"]`, (2) use a schema validation library like Cerberus or jsonschema, or (3) use Pydantic models.

**Decision:**
Define Pydantic `BaseModel` classes for all data structures and validate YAML data by parsing it into these models.

**Rationale:**
- **Fail fast.** If a YAML file is missing a required field, has the wrong type, or contains an invalid value (e.g., `tier: P4`), Pydantic raises a clear, human-readable error at load time — not at 3AM when the resolver tries to access a field that does not exist.
- **Type safety.** Every field on every model has a known type. IDEs provide autocomplete and type checking. Mypy catches type errors at lint time. No more `KeyError` or `TypeError` surprises at runtime.
- **Better error messages.** Pydantic validation errors tell you exactly which field failed, what value was provided, and what was expected. Compare this to a `KeyError: 'escalation_chain'` traceback that tells you nothing about where in the YAML the problem is.
- **Self-documenting.** The model definitions serve as living documentation of the YAML schema. You do not need a separate schema file — the Python code is the schema.

**Trade-offs:**
- Adds a dependency (pydantic). Acceptable because Pydantic is widely used, well-maintained, and the validation guarantees it provides far outweigh the cost of an additional dependency.
- Model definitions must be kept in sync with YAML structure. Acceptable because the models *define* the YAML structure — they are the source of truth, not a copy of it.
