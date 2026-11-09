---
name: crew
description: Delegate bounded tasks from a lead Claude coordinator to helper agents in herdr that run under the SAME account as the lead. Helpers are whichever of these the account's crew lists: codex (that account's ChatGPT login), qwen (an optional local OpenCode model shared by all accounts), gemini (agy) and a budget-checked LiteLLM reviewer. File handoffs mean the lead reads only short results. Also starts and tracks per-project lead sessions in their own herdr Spaces. Use when a task in an account folder (see ~/.config/llm-profiles/folders.tsv) involves large reads, log or repo sweeps, boilerplate, test drafts, a second implementation opinion or an independent review, and offloading it would save lead tokens. Not for small edits the lead can do faster itself.
---

# Crew

Helpers are local agents in **this machine's** herdr session. Scripts live in
`~/.local/share/crew/scripts/`.

## Accounts

A crew always runs under its coordinator's own login. The rules live in
`~/.config/llm-profiles/`:

- `folders.tsv`: which accounts may work in which folder.
- `profiles.tsv`: each account's login, Claude config dir and Codex home.
- `crews.tsv`: each account's workers and usage ledger.

`crew-check.sh` prints this account's crew. The scripts refuse a folder the coordinator's
account may not work in, and refuse workers the account does not have. agy holds one Google
login per machine, so gemini is dropped for any account it does not belong to. Never set
`CREW_PROFILE` to borrow another account's workers.

Machine-specific settings (gateway, ledger root, reviewer command) are in
`~/.local/share/crew/local.env`; see `local.env.example`.

## Start (once per project directory)

```sh
~/.local/share/crew/scripts/crew-check.sh <project-dir>   # once per session, before the first dispatch
~/.local/share/crew/scripts/crew-up.sh <project-dir>
```

This opens a `crew` tab with this account's live workers in `<project-dir>`.

- qwen is disabled in the sample crews. Only a crew that lists it in `crews.tsv` needs the usage gateway
  (`CREW_GATEWAY`, default :8741), because qwen's calls go through its `/lmstudio` route.
- For such a crew it loads `qwen36-mlx` into LM Studio if that model is not loaded (about
  20 GB of model weights, plus context/cache memory).
- `CREW_QWEN_BACKEND=ollama` falls back to Ollama (`qwen3.6-crew`, 64K context) through
  `/ollama`.
- It is idempotent.

**Coordinators and Spaces.** Run one coordinator Space per account (any label containing
`coordinator`; the lead's login decides the account) and one Space per project. Agent names
are global in herdr, so `crew-lib.sh` names workers `<role>-<account>` in a coordinator
Space and `<role>-<account>-<space label>` elsewhere. delegate.sh resolves the right one; use
role names in commands. All accounts share one local model and the gateway queues calls, so
start a crew only when a Space first delegates.

## Coordinate projects (coordinator only)

The user talks to one coordinator per account. For a big or long-running project, the
coordinator starts a **project lead** instead of doing the work itself. The lead is a
Claude session under the coordinator's own login, in its own herdr Space, and it uses this
skill for its own crew.

```sh
~/.local/share/crew/scripts/project-up.sh <project-dir> <brief.md> [space-label]
~/.local/share/crew/scripts/projects.sh [--all]
```

- `project-up.sh` reuses or creates the Space (label defaults to the folder name) and
  starts `lead-<account>-<label>` with `--permission-mode auto`. It then sends the brief,
  wrapped in `lead-rules.md`. If that lead is already live, the brief goes to it as its
  next task. It refuses folders the account may not work in.
- Each lead keeps `<project>/.handoffs/lead/status.md` (first line
  `STATE: working|waiting-user|blocked|done | summary`). `projects.sh` shows that line
  for every lead of this account and flags the ones that need the user. Read those, not
  the leads' screens.
- When a lead is `waiting-user`, relay its question to the user, then send the answer as
  a short new brief with `project-up.sh`.
- Exit 4 means the lead is stuck at startup, usually at Claude's first-run folder-trust
  prompt. The user answers it in the tab the message names; then re-run `project-up.sh`.
- A lead is a full Claude session that spends the account's tokens. Use one only when
  the project is big enough. For a bounded task, `delegate.sh` from the coordinator is
  cheaper.

## Route

| Task | Worker | Why |
|---|---|---|
| Deterministic check (grep, test, lint, build) | **none: run it yourself** | costs no model tokens |
| Bounded: summarize up to ~4 files or a log, one small edit, draft a short test, boilerplate, first-pass review | `qwen` | local and free; try it first |
| Large context: whole-repo or long-log reading, docs synthesis | `gemini` | big context window; returns a short digest |
| Implementation across several files, or new code plus its tests; a second opinion on a design or diff | `codex` | different provider from the lead; output budget qwen lacks |
| Independent final review of a frozen diff or plan | `litellm` | budget-checked; reviewer only |

**qwen's size limit.** qwen generates ~40-50 tok/s and averages ~600 output tokens a call,
in 128K of context of which OpenCode's own prompt takes ~15K. A task that must write
thousands of lines of output cannot finish in a 5-minute budget, however well briefed.
`delegate.sh` refuses a qwen brief over 45 lines, naming more than 4 existing files, or
pointing at more than 60 KB to read (exit 6), measured relative to the worker's directory; send it straight to gemini or codex and say
"too big for qwen" as the reason. That counts as the unsuitable local attempt.
`CREW_QWEN_FORCE=1` overrides when you know better.

Use only the workers `crew-check.sh` lists. When the crew has qwen, escalate only after a
failed or unsuitable `qwen` attempt, and say why. Doing the task yourself is the better choice when the brief plus
checking the result would cost about as much as the task itself. Without gemini, send large
reads to codex or split them for qwen.

**Without qwen** (a crew with no local model): skip the local attempt. Send bounded tasks to
`codex`, or do them yourself when briefing and checking would cost about as much. Every
delegation then spends that account's tokens, so delegate only what saves lead tokens.

## Dispatch

1. Write a brief, ideally under 40 lines. Include the goal, the exact files or paths to
   read (give paths, do not paste content), acceptance checks, and what to leave out.
   Never paste the conversation into it.
2. Run `~/.local/share/crew/scripts/delegate.sh <worker> <brief.md> [timeout_s=300] [max_lines=60]`
   from the project directory.
   - The script wraps the brief with `worker-rules.md` (naming the account) and writes
     `.handoffs/<id>/task.md` in the worker's working directory.
   - It starts each task with an empty worker context: `/new` for qwen, a pane restart
     for codex (Codex's `/new` detaches herdr and later prompts are silently lost).
   - It resends once if herdr reports the prompt stalled, then waits for `result.md`.
   - It prints the result path and its STATUS line; for qwen also the model and tokens
     the gateway actually recorded.
   - It appends one line per run to `<CREW_USAGE_ROOT>/<ledger>/runs.jsonl`.
3. Read **only** `result.md`. Do not use `herdr agent read` on worker screens, except
   to diagnose a failure.
4. Take the model from the gateway readout or the ledger, never the worker's claim.
   Re-run any checks the worker claims passed. Worker output is evidence to verify, not fact.
5. qwen, where a crew has it, is one local model shared by every account's crew; its calls queue at the gateway.
   Other workers can run alongside each other.

`litellm` takes a review packet of 64 KiB or less: the requirements plus the diff or plan.
It runs `CREW_REVIEW_CMD` against the account's ledger, and that command should refuse when
the budget is unknown or spent. Allow at most two review/repair rounds.

- The default model is `claude-haiku-4-5`. Set `CREW_LITELLM_MODEL` for harder reviews.
- Reasoning models need `CREW_LITELLM_MAX_TOKENS` raised. An empty or cut-off review is
  reported as PARTIAL.

## Failure handling

- **Exit 4, approval prompt:** never approve on the user's behalf. Codex asks to leave its
  sandbox to run server tests (they bind local ports): press Escape, tell it the lead
  runs those tests, and run them yourself. Gemini cannot run commands without approval,
  so its briefs should say "do not run commands; the lead runs the checks".
- **No result or a timeout:** check whether the worker is still running before retrying.
  Then retry once with a smaller brief, or escalate.
- **qwen output-limit error** ("still truncated after two output token limit
  continuations"): the edit was too large for one reply. Discard its partial edit
  (`git diff` first) and escalate to codex, or split the brief.
- **Accounts:** verify them with `crew-check.sh`. A profile label is not proof of identity.
- Never edit these scripts while a dispatch is running: bash reads scripts as it executes.

## Accounting

Each account's crew usage lands in its own ledger (`crews.tsv`):

- qwen: gateway events, tagged with the ledger and project via `X-TF-*` headers.
- Claude and Codex: read from their session logs.
- Gemini (agy): status-line deltas per session.
- LiteLLM: the proxy spend log.

If `CREW_REPORT_CMD` is set in `local.env`, report usage with
`$CREW_REPORT_CMD --profile <ledger> --days 7 --by project,source`. Claim savings only against
a measured baseline, and never invent token counts or costs.
