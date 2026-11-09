# Paddock T3 Crew — public preview

One company, one or more approved AI resources, one coordinator, a builder, fresh
code review, and an independent instruction/process adversary. No herdr, Make,
local model, account-switching setup, or mandatory second provider is required.

See NOTICE.txt. The package contains no credentials, provider logins, company-specific
bindings, or model runtimes.

## Install

Requirements: Python 3.11+, Git, T3 with a signed-in approved provider. Skill discovery
is provider-specific; installation does not prove the T3 host loaded it.

Extract the installer ZIP to a normal folder. Preview and then apply to the provider's
actual skills directory. For a default Codex home from native PowerShell:

```powershell
python install.py --skills-dir "$HOME/.codex/skills"
python install.py --skills-dir "$HOME/.codex/skills" --apply
```

For macOS (use the actual CODEX_HOME if customized):

```sh
python3 install.py --skills-dir "$HOME/.codex/skills"
python3 install.py --skills-dir "$HOME/.codex/skills" --apply
```

Claude users select the `skills` directory under their actual Claude configuration
home instead. For other providers, follow the host's supported skill-discovery
mechanism or use the generated project instructions. Do not assume a universal T3
skill-import directory. `install.ps1` and `install.sh` forward the same arguments.

The skill-only ZIP can be unpacked into a supported skills directory manually. Manual
installs have no installer manifest: do not use managed upgrade/uninstall on them.

The managed installer is repeatable with `--upgrade --apply` and removable with
`--uninstall --apply`. It refuses to overwrite/remove locally modified installations.
It does not edit global credentials, T3 settings, other skills, or existing projects.

## First T3 conversation

Start in the desired repo and ask:

> Use Paddock Crew to set up this project. Interview me about company-approved Claude,
> ChatGPT/Codex, Gemini, LiteLLM or Cursor access. Keep local models off. Discover T3's
> actual providers, map the four roles to approved instances, preserve this project's
> existing instructions and tests, and establish the verification command. Keep the
> process adversary separate from code review. Do not publish or deploy anything.

One approved provider can fill every role in separate sessions. Interview responses
start unbound; the coordinator checks actual T3 capabilities and gets your mapping
where it is ambiguous. It does not infer approval from a visible provider label.

For a new project, give its path and purpose. The coordinator creates the folder/Git
repo and `.paddock` process files, then registers that exact folder through supported
T3 project tools (or you add it in the app). Creating another top-level thread is a
separate user action. No session needs a permanently running crew pane.

The CLI alternative uses the installed skill's `scripts/paddock.py`:

```sh
python scripts/paddock.py interview --output crew.json --apply
python scripts/paddock.py project /path/to/new-repo --crew crew.json --new
python scripts/paddock.py project /path/to/new-repo --crew crew.json --new --apply
```

Use the full script path when not in the skill folder. The project starts with no
verification commands; configure its actual tests/build/lint, not a dummy success.
Local crew bindings and run evidence stay Git-ignored. Commit shared rules and checks
through the project's normal process. New machines must supply local crew bindings.

## What the adversary does

Before substantial work it reviews instructions and acceptance criteria. After work,
a fresh secondary reviewer audits the agent's claims against original instructions,
raw outputs and host receipts: hallucinated facts, omissions, errors/no data called
success, and assertions that a rail worked without observations. It reports unsupported
or contradicted claims, not an accusation about intent. Code review remains separate.

Final output distinguishes command/test verification, code review, adversary review,
host controls, CI and deployment. Unknown/missing data stays unknown. Hashes and local
records detect accidental staleness, not malicious forgery or model truthfulness.

See [the preview validation record](VALIDATION.md) for what has and has not actually run.

## Validate before rollout

```sh
python -m unittest discover -s tests -v
```

These exercise installation and negative paths without paid models. Passing them does
not prove native T3 integration. In a scratch repo on each target OS, complete a small
real task with fresh code and adversary reviews; inspect actual provider/model/workspace
and approval receipts. Run Windows tests natively, not only under WSL. The included
workflow diagram describes the intended process, not an assertion that all host
controls have been verified. The legacy multi-company guards remain a separate package.
