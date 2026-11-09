---
name: paddock-crew
description: Set up and run a T3-native project crew with a coordinator, builder, code reviewer, and separate instruction/process adversary. Use for Paddock onboarding, new project setup, or tasks in a repo that has adopted Paddock. Single-company, approved-provider workflow; no herdr or local model required.
---

# Paddock crew

The current project session is the coordinator and owns integration. Roles are not
products: one approved provider can supply separate sessions for all roles. Qwen
and multi-company routing are optional extensions, disabled in this core package.

Resolve packaged paths relative to this skill. Python 3.11+ and Git are required.
The portable CLI is `scripts/paddock.py`; use `python` on Windows and `python3` on
macOS/Linux. It never starts models or edits T3's private settings/database.

## Setup or a new project

Read [onboarding](references/onboarding.md). Ask which company-approved resources
are available: Claude, ChatGPT/Codex, Gemini, LiteLLM, Cursor; allow other answers.
Distinguish available subscriptions from approved resources and working T3 adapters.
Use supported host capability tools, map explicit instances/models, and leave
unavailable resources unbound. Do not buy access, change credentials, enable a
provider, download a model, or select a different organization as a fallback.

Generate a local crew configuration and adopt/create the requested repo through
the CLI. Preview changes first; apply within the user's setup authorization without
asking again for routine reversible writes. Preserve existing project instructions
and verification commands. The new repo starts with verification **unconfigured**;
configure actual project checks, never substitute a passing scaffolding check.

T3 project registration uses supported project tools: reuse an existing registration
for the same canonical path, otherwise register the explicit existing folder. Do not
edit its database or launch a top-level thread unless the user asks for one. Set or
merge project actions only after reading existing actions. Users can also add the
folder through T3. Skill discovery is provider-specific; the project instruction
files supply the shared process even where the host cannot discover this skill.

## Every adopted task

Read `.paddock/RULES.md`, the repo's existing instructions, and
[orchestration](references/orchestration.md). Use this sequence proportionately:

1. Capture the original request and accepted contract (scope, exclusions, acceptance
   checks, authorization) using `task`. Run a fresh instruction adversary before
   implementing a substantial or ambiguous plan. Its remit is instruction quality,
   contradictions and evidence requirements, not redesigning the user's request.
2. Work directly for small tasks; otherwise use a bounded builder brief. Default to
   one builder; use host-created separate worktrees for concurrent edits. Explicitly
   account for uncommitted parent changes, which child worktrees do not inherit.
3. Integrate and execute the project's configured checks using `verify`. Preserve
   failures, skipped work, command output, and missing data. Never convert them to
   a green report. An exit code alone does not establish that any tests ran.
4. Freeze the source. Write `claims.md` as the proposed user-facing claims and
   `host.json` with observed controls plus references to actual host/tool receipts.
   Run `packet`. Give its paths and digest to a fresh code reviewer and a separate
   fresh process adversary. Read [review contracts](references/reviews.md).
5. Address findings with evidence. Source or policy changes invalidate final reviews;
   request new reviews of the new packet. At most two automatic repair/review rounds.
   Escalate unresolved findings with a concrete explanation. Never approve a worker's
   host permission request yourself or circumvent a rejected action.
6. Run `audit`. Report verification, code review, adversary review, and host controls
   separately. `evidence_complete` checks records/freshness; it is not proof that
   claims are true, controls are enforced, or changes are safe to merge. Report CI,
   deployment, and Windows results only when actually executed.

For trivial work, explain why a review is omitted and leave its state `pending` or
`not_run`; do not manufacture a fully audited completion. When delegation is absent,
work sequentially and provide review packets for a separate session or human. Never
impersonate an independent reviewer. Host routing instructions take precedence over
examples here; follow the current tool schemas and returned continuation instructions.

## Boundaries

Use only configured, approved, currently usable provider/model bindings; run `route`
against a fresh capability snapshot before a host dispatch. A provider label does
not prove account identity. This is a preflight policy check, not a host-wide block
on other tools. T3/provider permissions supply actual runtime controls.

No role receives extra authority to commit, publish, merge, deploy, send messages,
or change credentials simply because it is a worker or reviewer. Keep within the
user's authorization. Reviewers inspect, cite, and report; they do not fix code.

Records are local and editable, not signed attestations. Never claim that digests,
worktrees, review agreement or this skill enforce credential/security isolation.
Raw logs and prompts can contain company data: keep `.paddock/runs` local and inspect
any selected packet before sending it to an approved reviewer. Do not include these
records or local crew bindings in distributable ZIPs.
