# paddock

paddock keeps each of your accounts' AI coding agents in its own field on one Mac. It is
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
   - qwen (a local OpenCode model shared by all accounts)
   - that account's Codex
   - optionally Gemini and a budget-checked LiteLLM reviewer

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
| `llm-profiles/install.sh` | Adds the wrappers to `~/.zshrc` and the hook to each Claude config dir, including T3 Code's (`--uninstall` reverses it) |
| `llm-profiles/t3-codex`, `codex_guard.py` | Folder guard for Codex inside T3 Code (set as the instance's binary path) |
| `llm-profiles/tests/` | `python3 -m unittest discover -s llm-profiles/tests` |
| `llm-profiles/*.tsv.example` | Accounts (`profiles`), folder rules (`folders`), helper workers (`crews`) |
| `crew/SKILL.md` | The `crew` skill the coordinators follow |
| `crew/scripts/` | `crew-check`, `crew-up` and `delegate` handle workers; `project-up` and `projects` handle project leads |
| `crew/worker-rules.md`, `crew/lead-rules.md` | Standing rules sent with every brief |
| `crew/local.env.example` | Machine settings: usage gateway, ledger root, reviewer command |

## Setup

Requirements: macOS or Linux, zsh, python3, herdr, Claude Code, and whichever of Codex, agy,
OpenCode and LM Studio/Ollama you use.

```sh
git clone https://github.com/jkomg/paddock ~/src/paddock
cd ~/src/paddock
for f in profiles folders crews; do cp llm-profiles/$f.tsv.example llm-profiles/$f.tsv; done
cp crew/local.env.example crew/local.env
$EDITOR llm-profiles/*.tsv crew/local.env        # your accounts, folders and workers

ln -s "$PWD/llm-profiles" ~/.config/llm-profiles
ln -s "$PWD/crew" ~/.local/share/crew
for d in $(python3 llm-profiles/llm_profile.py claude-dirs); do mkdir -p "$d/skills"; ln -sfn ~/.local/share/crew "$d/skills/crew"; done
bash llm-profiles/install.sh                     # writes backups (*.llm-profiles-bak) first
```

Sign in each account once in its own config dir, for example
`CLAUDE_CONFIG_DIR=~/.claude-globex claude` and then `/login`. Do the same for Codex with
`CODEX_HOME`. After that, `cd` into an account folder and run `claude`: the wrapper picks
the login. Start a coordinator per account in a herdr Space whose label contains
"coordinator", then run `~/.local/share/crew/scripts/crew-check.sh` in it.

qwen's calls go through a usage gateway (`CREW_GATEWAY`). This is an OpenAI-compatible proxy
that records tokens per account and project from `X-TF-Profile` / `X-TF-Project` headers.
Without one, leave `qwen` out of `crews.tsv`, or point `CREW_GATEWAY` at a plain proxy.

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
   It finds the real `codex` on `PATH` (or `PADDOCK_CODEX_BIN`).
3. **Install.** Run `bash llm-profiles/install.sh` again. It also puts the hook into every
   Claude dir T3's settings name, and prints them.
4. **Check.** `python3 llm-profiles/llm_profile.py t3-check` is read-only. For each instance it
   shows which profile its dir maps to, its login, whether it is guarded, and the T3 projects
   whose folder rule does not allow it. It exits 1 if an enabled instance has a warning.
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
- A Codex instance whose binary path is not `t3-codex` is unguarded. So is any other T3
  provider (OpenCode, Cursor, Antigravity). Keep the instances of accounts you are not using
  disabled, or use only one account's Codex per T3.
- `t3-codex` was tested against Codex 0.166.0. A later protocol change could make it refuse
  more (it fails closed), but rerun the tests after upgrading Codex.

## Limits

- The hook is a guard against mistakes, not a sandbox. It checks file-tool paths, the
  session folder, and paths it can see in Bash commands. A command that builds a path at
  run time can get past it. Bare folder names in commands can also trigger false denials.
- Claude asks for folder trust the first time a lead opens a folder. You answer that, and
  every approval prompt, yourself. The scripts never approve on your behalf.
- Every project lead is a full Claude session that spends that account's tokens.
- A linked git worktree follows its main repo's folder rule (see the T3 Code section). A
  plain copy of a repo does not.
