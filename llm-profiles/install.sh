#!/usr/bin/env bash
# Install (or --uninstall) the folder-to-login guard.
#   Layer 1: ~/.zshrc sources llm-profile.zsh (folder-aware claude / codex / agy wrappers).
#   Layer 2: Claude Code SessionStart + PreToolUse hook in every Claude config dir.
# Backups: <file>.llm-profiles-bak (written once, never overwritten).
set -euo pipefail
HERE="$HOME/.config/llm-profiles"
MODE=${1:-install}
# Every profile's Claude config dir (profiles.tsv), plus any extra dirs in LLM_PROFILES_EXTRA_CLAUDE_DIRS
# (colon-separated) that should get the hook too.
SETTINGS=()
while IFS= read -r d; do SETTINGS+=("$d/settings.json"); done < <(python3 -I "$HERE/llm_profile.py" claude-dirs)
IFS=: read -ra EXTRA <<< "${LLM_PROFILES_EXTRA_CLAUDE_DIRS:-}"
for d in ${EXTRA[@]+"${EXTRA[@]}"}; do [ -n "$d" ] && SETTINGS+=("$d/settings.json"); done

backup() { [ -e "$1" ] && [ ! -e "$1.llm-profiles-bak" ] && cp -p "$1" "$1.llm-profiles-bak"; return 0; }

# ---- Layer 1: ~/.zshrc
backup "$HOME/.zshrc"
python3 -I - "$HOME/.zshrc" "$MODE" <<'EOF'
import sys
p, mode = sys.argv[1], sys.argv[2]
s = open(p).read()
line = "[[ -f ~/.config/llm-profiles/llm-profile.zsh ]] && source ~/.config/llm-profiles/llm-profile.zsh  # llm-profiles\n"
old_start = "# claude work|personal [any other claude args]"
if mode == "install":
    if old_start in s:   # retire the old claude() wrapper; llm-profile.zsh replaces it
        a = s.index(old_start); b = s.index("\n}\n", a) + 3
        s = s[:a] + line + s[b:]
    elif line not in s:
        s += "\n" + line
    print("zshrc   : wrapper installed")
else:
    if line in s:
        s = s.replace(line, "")
        print("zshrc   : wrapper line removed (restore the old claude() from ~/.zshrc.llm-profiles-bak if you want it)")
open(p, "w").write(s)
EOF
zsh -n "$HOME/.zshrc"

# ---- Layer 2: Claude Code hooks
for f in "${SETTINGS[@]}"; do
  [ -d "$(dirname "$f")" ] || continue
  backup "$f"
  python3 -I - "$f" "$MODE" <<'EOF'
import json, os, sys
p, mode = sys.argv[1], sys.argv[2]
cmd = "python3 -I $HOME/.config/llm-profiles/llm_profile.py hook"
d = json.load(open(p)) if os.path.exists(p) else {}
hooks = d.setdefault("hooks", {})
want = {
    "SessionStart": {"matcher": "^(startup|resume|clear|compact|fork)$"},
    "PreToolUse": {"matcher": "Bash|Read|Edit|Write|NotebookEdit|Glob|Grep"},
}
for event, base in want.items():
    entries = [e for e in hooks.get(event, []) if not any(h.get("command") == cmd for h in e.get("hooks", []))]
    if mode == "install":
        entries.append(dict(base, hooks=[{"type": "command", "command": cmd, "timeout": 10}]))
    if entries: hooks[event] = entries
    else: hooks.pop(event, None)
if not hooks: d.pop("hooks")
json.dump(d, open(p, "w"), indent=2); open(p, "a").write("\n")
print("hooks   : %s %s" % ("installed in" if mode == "install" else "removed from", p.replace(os.path.expanduser("~"), "~")))
EOF
done
echo "Done. Open a new terminal (or: source ~/.zshrc). Running Claude sessions pick up hooks on their next tool call or restart."
