#!/usr/bin/env bash
# Start (or re-brief) a project lead: a Claude session under the COORDINATOR'S OWN login, in its
# own herdr Space, working in <project-dir>. The lead uses the crew skill for its workers and
# keeps <project-dir>/.handoffs/lead/status.md current; projects.sh reads those.
# Usage: project-up.sh <project-dir> <brief.md> [space-label]   (label default: folder name)
# If this account's lead for that Space is already live, the brief is sent to it as a new task.
# Env: CREW_LEAD_MODE (default auto) = the lead's --permission-mode.
set -euo pipefail

[ "${HERDR_ENV:-}" = 1 ] || { echo "project-up: run this from a herdr pane" >&2; exit 1; }
[ $# -ge 2 ] || { echo "usage: project-up.sh <project-dir> <brief.md> [space-label]" >&2; exit 2; }
PROJECT=$(cd "$1" && pwd); BRIEF=$2
[ -f "$BRIEF" ] || { echo "project-up: brief not found: $BRIEF" >&2; exit 2; }
LABEL=${3:-$(basename "$PROJECT")}
SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
. "$SKILL_DIR/scripts/crew-lib.sh"
jget() { python3 -I -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

# The lead runs under this coordinator's account, and that account must be allowed in the folder.
crew_env "$PROJECT" || { echo "project-up: the $(basename "$PROJECT") folder is not open to this coordinator's account" >&2; exit 1; }
CLAUDE_DIR=$(python3 -I "$CREW_PROFILES/llm_profile.py" resolve claude "$PROJECT" "$CREW_ACCOUNT") \
  || { echo "project-up: no usable $CREW_ACCOUNT Claude login for $PROJECT" >&2; exit 1; }

SLUG=$(echo "$LABEL" | tr 'A-Z' 'a-z' | sed -E 's/[^a-z0-9_-]+/-/g; s/^-+|-+$//g')
case "$SLUG" in ''|*coordinator*) echo "project-up: pick a project label, not a coordinator one" >&2; exit 2;; esac
NAME=$(echo "lead-$CREW_ACCOUNT-$SLUG" | cut -c1-32)

# Hand the brief over as a file: lead rules + the task. The prompt itself stays one line.
DIR="$PROJECT/.handoffs/lead"; mkdir -p "$DIR"
[ -d "$PROJECT/.git" ] && { grep -qx '.handoffs/' "$PROJECT/.git/info/exclude" 2>/dev/null || echo '.handoffs/' >> "$PROJECT/.git/info/exclude"; }
TS=$(date +%Y%m%d-%H%M%S); REL=".handoffs/lead/brief-$TS.md"
{ sed -e "s/{{ACCOUNT}}/$CREW_ACCOUNT/g" -e "s#{{PROJECT}}#$PROJECT#g" "$SKILL_DIR/lead-rules.md"
  echo; echo "# Task"; echo; cat "$BRIEF"; } > "$PROJECT/$REL"
MSG="Read $REL and do what it says. Keep .handoffs/lead/status.md current as it describes."

if herdr agent get "$NAME" >/dev/null 2>&1; then
  herdr agent prompt "$NAME" "$MSG" >/dev/null
  echo "$NAME: live; new brief sent ($REL)"; exit 0
fi

# Reuse the Space with this label, or create it. The lead goes in a "lead" tab.
WS=$(herdr workspace list | jget "next((w['workspace_id'] for w in d['result']['workspaces'] if (w.get('label') or '')=='$LABEL'), '')")
ENVS=(); [ "$CLAUDE_DIR" != default ] && ENVS=(--env "CLAUDE_CONFIG_DIR=$CLAUDE_DIR")
if [ -z "$WS" ]; then
  out=$(herdr workspace create --cwd "$PROJECT" --label "$LABEL" --no-focus ${ENVS[@]+"${ENVS[@]}"})
  WS=$(echo "$out" | jget 'd["result"]["workspace"]["workspace_id"]')
  herdr tab rename "$(echo "$out" | jget 'd["result"]["tab"]["tab_id"]')" lead >/dev/null 2>&1 || true
  PANE=$(echo "$out" | jget 'd["result"]["root_pane"]["pane_id"]'); echo "space '$LABEL' ($WS) created"
else
  out=$(herdr tab create --workspace "$WS" --cwd "$PROJECT" --label "lead-$CREW_ACCOUNT" --no-focus ${ENVS[@]+"${ENVS[@]}"})
  PANE=$(echo "$out" | jget 'd["result"]["root_pane"]["pane_id"]'); echo "space '$LABEL' ($WS) reused"
fi
sleep 1

# herdr types `claude ...` into the pane's zsh, so the folder-login wrapper checks it again
# (CLAUDE_CONFIG_DIR above selects this account where the folder allows several).
herdr agent start "$NAME" --kind claude --pane "$PANE" --timeout 90000 -- \
  --permission-mode "${CREW_LEAD_MODE:-auto}" -n "$NAME" >/dev/null \
  || { TABL=$(herdr pane get "$PANE" | jget 'd["result"]["pane"]["tab_id"]' 2>/dev/null); \
       TABL=$(herdr tab list --workspace "$WS" | jget "next((t['label'] for t in d['result']['tabs'] if t['tab_id']=='$TABL'), '?')" 2>/dev/null); \
       echo "$NAME: not ready in $PANE. Usually a first-run folder-trust or login prompt: the user answers it in Space '$LABEL', tab '$TABL', then re-run this." >&2; exit 4; }
herdr agent prompt "$NAME" "$MSG" >/dev/null
echo "$NAME: started in $PANE ($CREW_ACCOUNT login, $PROJECT); brief $REL"
echo "Check progress with: ~/.local/share/crew/scripts/projects.sh"
