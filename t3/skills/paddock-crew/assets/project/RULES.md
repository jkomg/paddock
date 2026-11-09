# Paddock project process

Read existing project instructions before these rules. Preserve the user's task and
existing authorization. This process does not grant publishing, deployment, credential
changes, or extra access. The current project thread owns coordination and integration.

- Use the installed `paddock-crew` skill when available. Otherwise follow these rules
  with the host's supported subagent tools; never invent tool availability or reviews.
- Single-company default. `.paddock/crew.json` maps roles to explicitly approved T3
  resources. Read live host capabilities and validate a binding before dispatch.
  Unbound/unavailable is blocked, not permission to switch account or provider.
- One builder by default. Small tasks stay with the coordinator. Concurrent edits
  require host-created isolated worktrees and an integration owner. Local models are off.
- Preserve the original request and accepted scope/acceptance contract. For substantial
  work, a fresh instruction adversary checks ambiguity, contradictions and evidence
  requirements before implementation. It must not replace the user's goal.
- Run the actual configured project checks, preserving outputs and failures. A command
  exit 0 does not prove any tests ran. No tests, all skipped, timeout, missing output or
  unavailable data cannot be reported as success. Do not invent token/cost figures.
- After integration, freeze source for fresh code review and a separate process
  adversary. Code review examines correctness. The adversary examines instruction
  adherence, factual claims, omissions, error reporting, and observed guardrail behavior.
  It needs original evidence, not only the builder's narrative; it does not infer intent.
- Reviews require distinct real sessions and inspectable host receipts. The coordinator
  counts as a builder when it edits. Never manufacture an independent review. If tools
  are unavailable, provide a packet for another session and report review pending.
- At most two automatic repair/review rounds. Changed source invalidates final review;
  changed instructions/contract invalidate instruction review. Unresolved findings are
  reported with evidence rather than hidden, repeatedly retried, or called approved.
- Follow host approvals and async lifecycle instructions. Do not poll when completion
  notifications are provided. A timeout is not proof that a child stopped; cancel through
  the host if abandoning it. Do not approve another agent's human approval request.
- Keep evidence in `.paddock/runs/TASK/`, ignored by Git. Review packets are local and may
  contain company data. Share only inspected relevant evidence with approved resources.
- Complete with separate states for checks, code review, adversary review, host controls,
  CI and deployment. Unknown is unknown. An evidence-completeness result is not proof
  of correctness, honest behavior, or enforcement. Files are editable, not attestations.

Use `python .paddock/paddock.py --help` (or python3) for local records/checks. Configure
`.paddock/project.json` with real commands before claiming verification. It starts empty
on purpose. The CLI cannot sign in providers, register T3 projects, dispatch agents or
prove host enforcement; the active T3 coordinator uses supported host tools for those.
