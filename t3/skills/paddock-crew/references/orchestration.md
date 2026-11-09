# Host adapter: T3

Use live tool discovery. Current T3 offers capability discovery, child tasks,
provider/model selection, worktree isolation, cancellation and completion results.
These capabilities are not guaranteed in every T3 release or provider adapter.

Read `.paddock/crew.json`. `route --role ROLE --crew FILE --catalog FILE` validates
one approved binding and prints the target. If it refuses, report the exact reason;
do not silently switch providers, accounts, models, or transport.

The host's own routing instructions decide whether to use a native subagent or
T3 delegation. In hosts matching the current T3 contract:
- Same-provider child with inherited settings: native subagent where supported.
- Another provider, explicit model/options, or separate checkout: T3 `delegate_task`.
- Pass only the bounded task brief; do not assume parent history is inherited.
- Use host-created `isolation: worktree` for concurrent builders. Do not create a
  shell worktree and assume it binds a child thread.
- Reviews are new tasks with fresh context. Never recycle a builder as its reviewer.
- Preserve returned task/session IDs, actual provider/model/options, workspace and
  terminal outcome. Requested model selection alone is not evidence it was applied.
- Follow returned continuation instructions. Async completion wakes the parent;
  do not poll running tasks, sleep-loop, or start substitute workers while they run.
- Cancel abandoned tasks through the supported cancellation tool. A timeout or
  interrupted parent does not establish that the child stopped.
- Human approvals/questions remain human. Completion is not inferred from an idle
  screen or an absent result.

The coordinator is the current project thread. Child workers are bounded tasks,
not permanently running panes. The default is one builder and up to two repair
rounds. The model roles may share a provider, but reviews require fresh sessions.
A separate top-level coordinator/project thread is created only when requested.

A worktree child does not see uncommitted parent changes or local ignored run files.
Give reviewers explicit accessible packet/source paths in the parent checkout or
transfer an inspected snapshot through supported host mechanisms. Verify the exact
reviewed digest. Keep source frozen while reviewing; merge workers before verifying.

## Builder brief

Goal; original request/contract paths; allowed scope; relevant files; exact acceptance
checks; permitted actions; exclusions; workspace/base state; time/output bound.
Return changed paths, actual checks and outcomes, blockers, and evidence references.
Do not ask workers to report invented usage, host identity, or costs. Read host data.

No script here creates provider sessions by shelling out to paid CLIs. The skill
coordinates through tools in the active T3 session. Capability snapshots and local
route checks do not prevent an agent from bypassing the skill; runtime enforcement
belongs to the host and provider permissions.
