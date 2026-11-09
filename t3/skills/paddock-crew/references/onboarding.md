# Initial interview and project setup

Ask short questions, using known host context rather than asking for it again:

1. Which resources does the company approve for this work? Claude, ChatGPT/Codex,
   Gemini, LiteLLM, Cursor, or another resource? Which are signed in through T3?
2. Which should coordinate, build, review code, and act as the process adversary?
   Default to the same approved provider in fresh sessions; do not require a second
   subscription. The adversary must be a different session from the builder and
   code reviewer. Ask about models only among live available options.
3. New or existing repo, and what folder? What constitutes completion? Discover
   existing tests/build/lint and deployment rules before asking users to repeat them.

The terminal alternative is:

    python scripts/paddock.py interview --output /path/to/crew.json --apply

Without `--apply` it only prints the interview result. Resources start unbound. A
subscription is not a confirmed account or a working T3 adapter. Gemini/LiteLLM may
be exposed through different drivers; do not infer account ownership from a label.

Inside T3, discover `orchestrator_capabilities` (tool prefixes vary) and save its
structured response as a local JSON file. Only read capabilities; do not dispatch a
smoke task until it falls within the user's approved setup/test scope. Confirm the
specific company instance when ambiguous. Bind each resource using:

    python scripts/paddock.py bind --crew crew.json --provider codex --instance INSTANCE --model MODEL --catalog capabilities.json --confirm-approved-instance --apply

The CLI checks availability/model membership; the confirmation records the user's
approval of that specific instance, not proof of its authenticated identity. Expand
the host model search if the model is omitted from the short catalog. Do not guess.
Refresh the catalog and revalidate bindings before use.

Create/adopt a repo (preview first; repeat with `--apply`):

    python scripts/paddock.py project /path/to/repo --crew crew.json --new
    python scripts/paddock.py project /path/to/existing-repo --crew crew.json

`--new` creates a Git repository only on apply. Existing repos must already have Git.
Project creation adds `.paddock` configuration, rules and a self-contained Python
runner; it appends a marked link to AGENTS.md and CLAUDE.md, preserving prior content.
If core scaffold files already exist, it refuses rather than overwriting local work.

Configure `.paddock/project.json` checks as argv arrays. `{python}` uses the active
interpreter; no shell is implied. For npm on native Windows use the appropriate
executable/launcher explicitly and test it there. Never substitute a shell expression
for an argv array. Each check has id, kind (`command` or `test`), argv and timeout.

A unittest adapter is included:

    {"id":"tests","kind":"test","argv":["{python}",".paddock/unittest_receipt.py","-s","tests"],"timeout":120}

Test adapters must write fresh completion/count data to `PADDOCK_CHECK_RECEIPT`.
See [evidence](evidence.md) for the format. Existing pytest/JUnit/etc. need a real
adapter; do not turn their exit code into a test receipt. A command check proves only
that command exited successfully. Set verification_mode to `commands` explicitly
for projects where tests do not apply; keep limitations in the final report.

T3 installation/sign-in remains external. Use supported project-list/create/read
operations to register the exact repo path. Optionally add a manual Verify action:
`python .paddock/paddock.py verify --project . --task TASK_ID` (python3 on macOS where
needed); never overwrite existing actions. No default model changes or hidden
threads are required by the installer. Before claiming host integration works,
run a bounded real task plus independent reviews in T3 and inspect actual receipts.
