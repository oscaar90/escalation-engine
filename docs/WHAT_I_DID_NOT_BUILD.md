# What I Didn't Build — And Why

Every feature listed below was considered and deliberately excluded. These are not items on a roadmap — they are conscious design decisions to keep the tool focused, reliable, and simple enough to trust at 3AM.

---

## 1. No PagerDuty / OpsGenie Integration

The Incident Escalation Engine does not send notifications. It does not page anyone. It does not integrate with PagerDuty, OpsGenie, or any other alerting platform.

This is intentional. The problem this tool solves is not "how do I notify someone" — that problem is already well-solved by mature, battle-tested products. The actual problem in large-scale financial infrastructure is knowing *who* to notify. When the on-call engineer gets paged for a service they have never touched, the first question is not "how do I send an alert" — it is "who owns this, and who do I escalate to?"

This tool answers that question. It resolves the escalation chain and gives you names, phone numbers, and Slack handles. What you do with that information — call them manually, trigger a PagerDuty incident, send a Slack message — is up to you and your organization's existing workflows. Coupling notification into this tool would mean taking on the complexity of delivery guarantees, retry logic, and vendor API authentication, all for a problem that is already solved elsewhere.

---

## 2. No ML / AI-Powered Routing

There is no machine learning model predicting who should be paged. There is no NLP analyzing incident descriptions to route to the right team. There is no AI suggesting escalation paths based on historical patterns.

This is intentional. During a P1 incident, you need deterministic behavior. When the on-call engineer runs `escalation resolve-cmd payments-api`, they need to get the same answer every time — not a probabilistic recommendation that might vary depending on training data drift. A well-maintained YAML file with explicit ownership mappings is more reliable than any model, and it is auditable in a way that ML predictions are not.

In regulated financial services environments, "the model thought this person was the right contact" is not an acceptable answer in a post-incident review. "The registry says platform-core owns payments-api, and Ana Garcia is the primary on-call" is.

---

## 3. No Web UI

There is no dashboard. There is no browser-based interface. There is no React frontend.

At 3AM, nobody opens a browser to look up an escalation chain. The on-call engineer is in a terminal — they are already SSH-ed into a jump host, tailing logs, and running diagnostic commands. A CLI command that returns the answer in under a second is the fastest possible path. Adding a web UI would mean deploying and maintaining a web server, managing authentication, handling browser compatibility, and adding a network dependency that may not be available during the incident you are trying to resolve.

The CLI also composes naturally with existing tools. Pipe to `jq` for JSON filtering, pipe to `grep` for searching, pipe to `pbcopy` for quick clipboard access. A web UI provides none of these affordances.

---

## 4. No Auto-Remediation

The tool resolves escalation chains. It does not restart services, roll back deployments, toggle feature flags, or execute runbooks.

This is a deliberate scope boundary. Escalation and remediation are fundamentally different concerns with different blast radii, different ownership models, and different rates of change. An escalation chain changes when someone goes on vacation. A remediation runbook changes when the architecture changes. Coupling them into the same tool means a change to one can break the other.

Auto-remediation also requires deep integration with deployment systems, infrastructure APIs, and service-specific knowledge. It is a much harder problem with much higher risk — a bad escalation lookup wastes a few minutes; a bad auto-remediation can take down production. Keeping these concerns separate means each tool can be simple, focused, and independently trusted.

---

## 5. No Real-Time / WebSocket Updates

The registry is read from YAML files at invocation time. There is no live-updating dashboard, no WebSocket feed of ownership changes, no event stream.

Escalation chains do not change during an incident. The ownership of `payments-api` at 3:00 AM is the same as at 3:05 AM. There is no user story where an on-call engineer needs to see an escalation chain update in real-time while they are staring at the terminal. The data changes when someone pushes a commit to update the registry — at that point, the next invocation of the CLI picks up the new data.

Real-time infrastructure (WebSocket servers, pub/sub systems, state synchronization) adds operational complexity that provides no value for this use case. `git pull && escalation resolve-cmd payments-api` is the update mechanism, and it is sufficient.

---

## 6. No Multi-Tenancy

This tool is not a SaaS product. There is no concept of organizations, workspaces, tenants, or access control. There are no user accounts.

Each team or organization that wants to use this tool clones the repository, populates their own registry YAML files, and runs the CLI. The "isolation boundary" is the git repository. If two teams need different registries, they have two repositories (or two directories within a monorepo). This is simpler, more secure, and more aligned with how infrastructure teams actually work than building a multi-tenant platform.

Multi-tenancy would require authentication, authorization, data isolation, rate limiting, and a deployment model — transforming a focused CLI tool into an infrastructure product. That is a different project with a different set of trade-offs, and it is not the problem this tool set out to solve.
