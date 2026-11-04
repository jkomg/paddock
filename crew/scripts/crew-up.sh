#!/usr/bin/env bash
# Start this account's crew in a herdr tab. The account is the coordinator's own login
# (see crew-lib.sh); its workers come from ~/.config/llm-profiles/crews.tsv:
# codex (the account's CODEX_HOME), qwen (optional local OpenCode on LM Studio MLX, shared and
# queued), gemini (agy; only for the account its single Google login belongs to).
# Usage: crew-up.sh [project-dir]   (default: current directory)
# Idempotent: agents that are already live are left alone.
set -euo pipefail

[ "${HERDR_ENV:-}" = 1 ] || { echo "crew-up: not inside a herdr pane" >&2; exit 1; }
PROJECT=$(cd "${1:-$PWD}" && pwd)
. "$(dirname "$0")/crew-lib.sh"
crew_env "$PROJECT" || { echo "crew-up: no crew for this account in $PROJECT" >&2; exit 1; }
echo "crew-up: $CREW_ACCOUNT crew ($CREW_WORKERS) for $PROJECT"

GATEWAY="$CREW_GATEWAY"
# *-crew models are Ollama variants with num_ctx 65536. Ollama's default 32768 is smaller
# than OpenCode's working context (~20K prompt + tool output) and silently truncates the
# oldest text, including the tool-call instructions.
QWEN_MODEL="${CREW_QWEN_MODEL:-ollama/qwen3.6-crew}"
QWEN_CTX=65536; QWEN_OUT=16384

# Only qwen talks to the usage gateway; a crew without a local model does not need it.
if crew_has qwen; then
  curl -fsS -o /dev/null "$GATEWAY/" || { echo "crew-up: usage gateway not reachable at $GATEWAY (CREW_GATEWAY); start it first" >&2; exit 1; }
fi

live() { herdr agent list | python3 -I -c 'import json,sys; print(" ".join(a.get("name") or "" for a in json.load(sys.stdin)["result"]["agents"]))'; }
jget() { python3 -I -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
LIVE=" $(live) "

# OpenCode config for qwen, routed through the usage gateway so every call is recorded.
# Default backend: LM Studio's MLX engine (qwen3.6 35B-A3B), measured 2026-10-31 at ~1.3x
# prompt and ~1.5x generation speed of Ollama on this M5, with the same tool-call accuracy.
# CREW_QWEN_BACKEND=ollama uses the Ollama *-crew variant instead. Declared limits let
# OpenCode compact before the window overflows; X-TF-* headers attribute gateway events to
# this account's ledger and this project.
QWEN_BACKEND="${CREW_QWEN_BACKEND:-lmstudio}"
if [ "$QWEN_BACKEND" = lmstudio ]; then
  QWEN_MODEL="${CREW_QWEN_MODEL:-lmstudio/qwen36-mlx}"
  QWEN_URL="$GATEWAY/lmstudio/v1"
  # Load explicitly: an on-demand (JIT) load would use LM Studio's small default context.
  if crew_has qwen && ! lms ps 2>/dev/null | grep -q "^${QWEN_MODEL#*/} "; then
    echo "qwen: loading ${CREW_LMSTUDIO_SOURCE:-qwen/qwen3.6-35b-a3b} into LM Studio as ${QWEN_MODEL#*/}"
    lms server status >/dev/null 2>&1 || lms server start --port 1234 >/dev/null
    lms load "${CREW_LMSTUDIO_SOURCE:-qwen/qwen3.6-35b-a3b}" --identifier "${QWEN_MODEL#*/}" \
      --context-length "$QWEN_CTX" -y >/dev/null || { echo "crew-up: LM Studio load failed; retry with CREW_QWEN_BACKEND=ollama" >&2; exit 1; }
  fi
else
  QWEN_URL="$GATEWAY/ollama/v1"
fi
QWEN_CFG=$(python3 -I -c 'import json,sys,os
provider, m = sys.argv[1].split("/",1)
p = {"settings": {"baseURL": sys.argv[2]},
     "models": {m: {"name": m, "limit": {"context": int(sys.argv[4]), "output": int(sys.argv[5])}}}}
p["settings"]["headers"] = {"X-TF-Profile": sys.argv[6], "X-TF-Project": os.path.basename(sys.argv[3])}
if provider == "lmstudio":
    p.update(name="LM Studio (MLX)", package="@opencode/ai/providers/openai-compatible")
print(json.dumps({"model": sys.argv[1], "share": "disabled", "providers": {provider: p},
 "policies": [{"action":"provider.use","resource":"*","effect":"deny"},
              {"action":"provider.use","resource":provider,"effect":"allow"}]}))' "$QWEN_MODEL" "$QWEN_URL" "$PROJECT" "$QWEN_CTX" "$QWEN_OUT" "$CREW_LEDGER")

# Reuse an existing "crew" tab in this workspace; ROOT is its first pane.
TAB=$(herdr tab list --workspace "$HERDR_WORKSPACE_ID" | jget 'next((t["tab_id"] for t in d["result"]["tabs"] if t.get("label")=="crew"), "")')
ROOT=""; [ -n "$TAB" ] && ROOT=$(herdr pane list --workspace "$HERDR_WORKSPACE_ID" | jget "next((p['pane_id'] for p in d['result']['panes'] if p['tab_id']=='$TAB'), '')")

start() { # name kind direction env... -- agent-args...
  local name=$1 kind=$2 dir=$3; shift 3
  if [[ "$LIVE" == *" $name "* ]]; then echo "$name: already live"; return; fi
  local envs=() ; while [ $# -gt 0 ] && [ "$1" != -- ]; do envs+=(--env "$1"); shift; done; [ "${1:-}" = -- ] && shift
  local pane out
  if [ -z "$ROOT" ]; then   # not in a subshell, so TAB/ROOT persist for the next agent
    out=$(herdr tab create --workspace "$HERDR_WORKSPACE_ID" --cwd "$PROJECT" --label crew --no-focus ${envs[@]+"${envs[@]}"})
    TAB=$(echo "$out" | jget 'd["result"]["tab"]["tab_id"]'); ROOT=$(echo "$out" | jget 'd["result"]["root_pane"]["pane_id"]'); pane=$ROOT
  else
    pane=$(herdr pane split --pane "$ROOT" --direction "$dir" --cwd "$PROJECT" --no-focus ${envs[@]+"${envs[@]}"} | jget 'd["result"]["pane"]["pane_id"]')
  fi
  sleep 1
  herdr agent start "$name" --kind "$kind" --pane "$pane" --timeout 60000 -- "$@" >/dev/null && echo "$name: started in $pane ($PROJECT)" || echo "$name: start returned non-ready; check with: herdr agent get $name"
}

# --standalone + own data/state dirs: OpenCode v2 otherwise attaches to the shared background
# service, which reuses the last model from its shared DB (ignoring
# QWEN_CFG) and mixes crew sessions with other orgs' history. Each account gets its own data
# and state dirs so session history never crosses accounts. Config dir stays shared so the
# herdr state plugin in ~/.config/opencode/plugins still loads.
CREW_OC="${CREW_OPENCODE_ROOT:-$HOME/.local/share/token-factory/opencode-crew}/$CREW_ACCOUNT"; mkdir -p "$CREW_OC/data" "$CREW_OC/state"
crew_has qwen   && start "$(crew_name qwen)"   opencode right "OPENCODE_CONFIG_CONTENT=$QWEN_CFG" "XDG_DATA_HOME=$CREW_OC/data" "XDG_STATE_HOME=$CREW_OC/state" -- --standalone
crew_has gemini && start "$(crew_name gemini)" agy      right -- --mode accept-edits
crew_has codex  && start "$(crew_name codex)"  codex    down  "CODEX_HOME=$CREW_CODEX_HOME" -- --sandbox workspace-write --ask-for-approval on-request
herdr agent list | python3 -I -c 'import json,sys
for a in json.load(sys.stdin)["result"]["agents"]:
  if a["pane_id"].split(":")[0] == sys.argv[1]: print("  %-28s %-9s %-8s %s  %s" % (a.get("name") or "-", a["agent"], a["agent_status"], a["pane_id"], a["cwd"]))' "$HERDR_WORKSPACE_ID"
echo "A 'blocked' agent is usually a first-run folder-trust prompt: the user answers it in the crew tab."
