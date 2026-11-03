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
| `llm-profiles/install.sh` | Adds the wrappers to `~/.zshrc` and the hook to each Claude config dir (`--uninstall` reverses it) |
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

## Limits

- The hook is a guard against mistakes, not a sandbox. It checks file-tool paths, the
  session folder, and paths it can see in Bash commands. A command that builds a path at
  run time can get past it. Bare folder names in commands can also trigger false denials.
- Claude asks for folder trust the first time a lead opens a folder. You answer that, and
  every approval prompt, yourself. The scripts never approve on your behalf.
- Every project lead is a full Claude session that spends that account's tokens.
