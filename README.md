# paddock

Paddock's new default is a **T3-native crew for one organisation**: coordinator, builder,
code reviewer, and a separate adversary auditing instructions, agent claims, missing
or contradictory evidence, and observed guardrail behavior. One approved provider
can fill all roles in fresh sessions. No herdr or local model is required.

## T3 crew — public preview

Start with [the installer and onboarding guide](t3/QUICKSTART.md). The initial interview
covers Claude, ChatGPT/Codex, Gemini, LiteLLM and Cursor; resources stay unbound until
mapped to approved available T3 instances. The portable project starter preserves
existing rules and adds real-check configuration, evidence recording and independent
review contracts. Verification starts unconfigured rather than falsely green.

[Shareable T3 workflow](t3/workflow.png) · [Editable vector](t3/workflow.svg)

Build the installer and skill ZIPs with `python3 scripts/build_release.py`; validate
and test the extracted package with `python3 scripts/check_release.py --test dist/*.zip`.
On PowerShell, pass the two ZIP paths explicitly or use `Get-ChildItem dist/*.zip` to
supply them. Releases contain an explicit allowlist and SHA-256 manifests; local
bindings, account files, credentials and run evidence are excluded. See
[the notice](t3/NOTICE.txt).

The preview's local records are editable, not authenticated attestations. A complete
audit record is not proof of model honesty or runtime enforcement. Native Windows and
real T3 host integration need their own executed validation; CI configuration alone
does not establish either. No release is published automatically.

## Legacy herdr crew and optional multi-account guards

paddock keeps each of your accounts' AI coding agents in its own field. It is
built for people who use Claude Code, Codex and Gemini (agy) under several logins, such as two
employers and a personal account, and run them side by side in the
[herdr](https://herdr.dev) terminal workspace.

It has two parts:

1. **A login guard (`llm-profiles/`).** Each folder says which accounts may work in it.
   - The zsh wrappers `claude`, `codex` and `agy` pick the right login from the folder you
     start them in, and refuse a login the folder does not allow.
   - A Claude Code hook (SessionStart and PreToolUse) denies tool calls that touch a
     folder the session's login may not use.
2. **A Claude skill, `crew` (`crew/`).** Each account gets a coordinator that delegates to
   helper agents under the **same** login:
   - that account's Codex
   - optionally qwen (a local OpenCode model shared by all accounts), Gemini, and a
     budget-checked LiteLLM reviewer

   Work is handed off through small files, so the coordinator reads only short results.
   For big projects the coordinator starts a project lead in its own herdr Space and tracks
   it through a one-line status file. You talk to the coordinators, not to every agent.

```
Space "Acme Coordinator"     you <-> coordinator (Claude, acme login)
Space "billing"              lead-acme-billing + crew tab: qwen-acme-billing, codex-acme-billing
Space "Globex Coordinator"   you <-> coordinator (Claude, globex login)
Space "audit"                lead-globex-audit + its crew (qwen, gemini, codex)
```

## Layout

| Path | What it is |
|---|---|
| `llm-profiles/llm_profile.py` | Folder rules, login detection, the hook, crew settings |
| `llm-profiles/llm-profile.zsh` | `claude` / `codex` / `agy` wrappers |
| `llm-profiles/install.py`, `install.sh` | Portable Claude hook installer; optional zsh routing on macOS/Linux. `--uninstall` removes Paddock hooks and routing. |
| `llm-profiles/t3-codex`, `codex_guard.py` | Folder guard for Codex inside T3 Code (set as the instance's binary path) |
| `llm-profiles/tests/` | `python3 -m unittest discover -s llm-profiles/tests` |
| `llm-profiles/*.tsv.example` | Accounts (`profiles`), folder rules (`folders`), helper workers (`crews`), optional app launchers (`wrappers`) |
| `crew/SKILL.md` | The `crew` skill the coordinators follow |
| `crew/scripts/` | `crew-check`, `crew-up` and `delegate` handle workers; `project-up` and `projects` handle project leads |
| `crew/worker-rules.md`, `crew/lead-rules.md` | Standing rules sent with every brief |
| `crew/local.env.example` | Machine settings: usage gateway, ledger root, reviewer command |

## Setup

For the full terminal crew: macOS/Linux, zsh, Python 3.9+, herdr, Claude Code, and the
workers you enable. The guard does not require herdr or a local model. For native Windows,
see the separate instructions below.

```sh
git clone https://github.com/jkomg/paddock ~/src/paddock
cd ~/src/paddock
for f in profiles folders crews; do cp llm-profiles/$f.tsv.example llm-profiles/$f.tsv; done
cp crew/local.env.example crew/local.env
$EDITOR llm-profiles/*.tsv crew/local.env        # your accounts, folders and workers

mkdir -p ~/.config ~/.local/share
ln -s "$PWD/llm-profiles" ~/.config/llm-profiles
ln -s "$PWD/crew" ~/.local/share/crew
while IFS= read -r d; do
  mkdir -p "$d/skills"
  ln -sfn ~/.local/share/crew "$d/skills/crew"
done < <(python3 llm-profiles/llm_profile.py claude-dirs)
bash llm-profiles/install.sh                     # writes backups (*.llm-profiles-bak) first
```

Sign in each account once in its own config dir, for example
`CLAUDE_CONFIG_DIR=~/.claude-globex claude` and then `/login`. Do the same for Codex with
`CODEX_HOME`. After that, `cd` into an account folder and run `claude`: the wrapper picks
the login. Start a coordinator per account in a herdr Space whose label contains
"coordinator", then run `~/.local/share/crew/scripts/crew-check.sh` in it.

qwen is opt-in and omitted from every sample crew. On a machine without the memory for a local model, leave it out of
`crews.tsv`: the crew then runs with Codex (and Gemini or LiteLLM if listed), and no
gateway, LM Studio or Ollama is needed. Where you do use it, qwen's calls go through a usage
gateway (`CREW_GATEWAY`). This is an OpenAI-compatible proxy
that records tokens per account and project from `X-TF-Profile` / `X-TF-Project` headers.
Without one, leave `qwen` out of `crews.tsv`, or point `CREW_GATEWAY` at a plain proxy.

When qwen is disabled, startup does not inspect/load a model, generate its configuration,
or create its OpenCode state directories. Retained optional settings include a 128K LM Studio
context default (`CREW_QWEN_CTX` overrides it) and a brief limit of 45 lines, four recognised
existing files, or 60 KiB. Paths are measured relative to the worker's directory; this is a
heuristic, not a complete estimate of every file the worker may open. `CREW_QWEN_FORCE=1`
bypasses that check. Model weights **plus context cache** consume RAM; 128K is not a safe
capacity promise for every machine. Reducing the setting does not resize an already loaded
model; reload it separately if you change the context. No local model is needed for Codex.

## Native Windows installation and testing

The Python installer supports a hooks-only installation without Bash, zsh, symlinks, or
administrator privileges. Keep the checkout at a permanent path: installed hooks quote the
absolute Python executable and script path, including spaces. Re-run installation after
moving the checkout or changing Python. Configuration files are UTF-8 (a BOM is accepted).

From PowerShell in the checkout, copy **only files that do not already exist**:

```powershell
foreach ($name in 'profiles', 'folders', 'crews') {
  $dest = "llm-profiles/$name.tsv"
  if (!(Test-Path $dest)) { Copy-Item "$dest.example" $dest }
}
# Edit profiles.tsv and folders.tsv for this Windows user's accounts and repo paths.
# Paths can use ~/Projects/acme or C:/Users/you/Projects/acme; columns are TAB-separated.
python llm-profiles/install.py --shell none
python llm-profiles/llm_profile.py t3-check
python -m unittest discover -s llm-profiles/tests -p test_install_portable.py -v
# To remove these hooks later:
# python llm-profiles/install.py --shell none --uninstall
```

Select the account's Claude home in T3, or set `$env:CLAUDE_CONFIG_DIR` before launching
Claude from PowerShell. Native PowerShell does **not** get the zsh automatic account router.
The installer discovers Claude homes from `~/.t3/userdata/settings.json`; set
`$env:LLM_PROFILES_T3_DIR` if T3 stores its data elsewhere. Extra Claude directories in
`LLM_PROFILES_EXTRA_CLAUDE_DIRS` use `;` on Windows and `:` on Unix.

The native Windows test job exercises installation, uninstall, hook execution with spaces
in paths, and Windows path matching. It still needs to run on Windows; local verification
was on macOS. Confirm that the real Claude/T3 host invokes the installed hook by attempting
a file read with the wrong account in a test repo and checking that it is denied.

**Platform boundary:** `t3-codex` is currently a POSIX shell launcher, and herdr crew scripts
are Bash scripts. They are not native Windows launchers. A Windows T3 Codex instance using
the ordinary Codex binary remains unguarded; native Windows launcher integration is not
claimed here. WSL can use the Unix setup with providers and configuration inside WSL;
a native T3 process does not automatically inherit that installation. Test those integrations
separately before relying on them for account routing.

## Using paddock with T3 Code

[T3 Code](https://t3.codes) runs Claude and Codex for you, so the zsh wrappers never run.
The herdr crew is optional: the guard works without herdr.

1. **One provider instance per account.** In T3's settings, add a Claude instance and a Codex
   instance for each account, and set each one's home path to that account's dir from
   `profiles.tsv` (the Claude config dir and the Codex home; leave it empty for a profile whose
   Claude dir is `default`). Sign each one in. If T3 must point at a different Claude dir than
   the wrapper uses, list both in `profiles.tsv`, comma-separated, wrapper's first:
   `globex  @globex.example  ~/.claude-globex,~/t3/claude-globex  ~/.codex-globex`.
2. **Guard Codex.** Set every Codex instance's binary path to `~/.config/llm-profiles/t3-codex`.
   That works directly: it finds the real `codex` on `PATH`, then in `~/.local/bin`,
   `/opt/homebrew/bin` and `/usr/local/bin`, which matters because GUI apps often lack
   `~/.local/bin` on `PATH`. Only for an unusual install, point `PADDOCK_CODEX_BIN` at the
   real binary, for example from a small launcher script that sets it and execs `t3-codex`.
   `t3-check` recognises such a launcher as guarded.
3. **Install.** Run `bash llm-profiles/install.sh` again. It also puts the hook into every
   Claude dir T3's settings name, and prints them.
4. **Check.** `python3 llm-profiles/llm_profile.py t3-check` is read-only. For each instance it
   shows which profile its dir maps to, its login, whether it is guarded, and the T3 projects
   whose folder rule does not allow it. It exits 1 for an enabled-instance warning or incomplete
   project/worktree coverage. Unknown or unrecognised logins are warnings, not healthy accounts.
   `crew-check.sh` prints a one-line summary.

What is guarded:

- **Claude**: T3 runs `claude` with the instance's dir as `CLAUDE_CONFIG_DIR` and loads that
  dir's settings, so the same SessionStart / PreToolUse hook applies as in a terminal.
- **Codex** (with `t3-codex`): T3 keeps one `codex app-server` per instance and sends each
  thread's folder over JSON-RPC. `t3-codex` sits on that stdio. It refuses to open or resume
  a thread in a folder the instance's login may not use, refuses requests that name such
  paths (file reads and writes, commands, roots), and fails closed on a thread whose folder it
  has not seen. `codex exec` (titles, commit messages) is checked against its folder.
  Everything else passes through unchanged.
- **Worktrees**: T3 keeps worktrees under `~/.t3/worktrees/`. A linked git worktree anywhere
  gets the rule of its main repo's folder, and must also satisfy its own folder's rule.

What is not guarded:

- `t3-codex` checks the folder a thread works in, not every command a turn runs: a
  full-access Codex turn can still run a command that reaches another folder. Claude's hook
  sees only paths it can read in tool calls. Neither is a sandbox.
- A Codex instance whose binary path is not `t3-codex` is unguarded. Keep the instances of
  accounts you are not using disabled, or use only one account's Codex per T3.
- **Cursor** is unguarded and unmapped. T3 runs Cursor's agent inside its own process through
  the Cursor SDK, signed in through the keychain or `CURSOR_API_KEY`. There is no binary or
  config dir per instance, so paddock can neither tell which account it uses nor see its
  folders. Safe practice: sign Cursor in to one account, and open only that account's
  projects in a Cursor thread. `t3-check` warns while an enabled Cursor instance can see
  T3 projects that have a folder rule.
- **Antigravity** is unguarded and unmapped. T3 runs it as its own ACP child process, signed
  in through T3's per-instance profile rather than agy's login, so paddock cannot tell its
  account. Use the same practice as for Cursor.
- **OpenCode** has no paddock guard either. `t3-check` reports an OpenCode
  instance as unmapped and unmetered unless its binary path is a per-account wrapper listed in
  the optional `llm-profiles/wrappers.tsv` (see `wrappers.tsv.example`). Then it lists the
  projects that account may not use. Listing a wrapper maps it; it does not guard it.
- `t3-codex` was tested against Codex 0.166.0. A later protocol change could make it refuse
  more (it fails closed), but rerun the tests after upgrading Codex.

## From a query to completed work

[Shareable workflow diagram](docs/paddock-workflow.png) · [Editable vector](docs/paddock-workflow.svg)

Start by placing the new repo under an account folder, or adding a rule for it. A repo outside
all rules is unrestricted; Paddock does not infer an employer from the prompt. In a terminal,
the zsh wrapper selects the account; in T3, you select the provider instance. Claude's hook
and the configured Codex proxy check the applicable folder rules. Linked worktrees inherit
the main repo's rule as well as their own location's rule.

Work can stay in that session. The optional herdr crew adds a coordinator/project lead that
writes bounded briefs, dispatches only enabled workers for its account, reads their result
files, and verifies the changes. Qwen is an optional small-task branch, not a prerequisite.
T3's own delegation is separate from these herdr scripts. A user review completes the loop.

## Verification

`python3 -m unittest discover -s llm-profiles/tests -v` runs the Unix suite, including mock
herdr dispatch checks and an installed-Codex round trip when available. CI runs the full
suite on macOS/Linux and the native installer suite on Windows. Tests never load a local
model or dispatch paid work.

## Limits

- The hook is a guard against mistakes, not a sandbox. It checks file-tool paths, the
  session folder, and paths it can see in Bash commands. A command that builds a path at
  run time can get past it. Bare folder names in commands can also trigger false denials.
- Claude asks for folder trust the first time a lead opens a folder. You answer that, and
  every approval prompt, yourself. The scripts never approve on your behalf.
- Every project lead is a full Claude session that spends that account's tokens.
- A linked git worktree follows its main repo's folder rule (see the T3 Code section). A
  plain copy of a repo does not.

## License

MIT. See [LICENSE](LICENSE).
