# Sourced by crew-up.sh, delegate.sh and crew-check.sh.
#
# crew_env <dir>: sets CREW_ACCOUNT (a profile in profiles.tsv), CREW_WORKERS, CREW_LEDGER and
# CREW_CODEX_HOME from ~/.config/llm-profiles (folder rule + crews.tsv). A crew always runs under
# its coordinator's account; the call fails if that account may not work in <dir>.
#
# crew_name <role>: herdr agent names are global across Spaces and accounts, so a worker is
# "<role>-<account>" in a Space whose label contains "coordinator" (or is empty) and
# "<role>-<account>-<space label>" elsewhere (names: [a-z][a-z0-9_-], max 32 characters).
CREW_PROFILES="$HOME/.config/llm-profiles"
# Machine-specific settings (usage ledger root, reviewer command): crew/local.env, not in git.
_crew_local="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/local.env"
[ -f "$_crew_local" ] && . "$_crew_local"
# Usage ledgers, one folder per ledger profile (crews.tsv): <root>/<ledger>/runs.jsonl and
# <root>/<ledger>/ledger/usage.sqlite3, written by an OpenAI-compatible usage gateway.
TF_PROFILES="${CREW_USAGE_ROOT:-$HOME/.local/share/token-factory/profiles}"
CREW_GATEWAY="${CREW_GATEWAY:-http://127.0.0.1:8741}"

crew_env() {
  local vars
  vars=$(python3 -I "$CREW_PROFILES/llm_profile.py" crew-env "$1") || return 1
  eval "$vars"
}

crew_has() { [[ " $CREW_WORKERS " == *" $1 "* ]]; }

# CREW_QWEN_BACKEND=remote: LM Studio on CREW_LMSTUDIO_SSH (an ssh alias with key auth),
# reached through a tunnel on 127.0.0.1:CREW_LMSTUDIO_TUNNEL_PORT.
CREW_LMSTUDIO_TUNNEL_PORT="${CREW_LMSTUDIO_TUNNEL_PORT:-12340}"
crew_qwen_route() {   # gateway route prefix for the configured qwen backend
  case "${CREW_QWEN_BACKEND:-lmstudio}" in remote) echo lmstudio-remote;; ollama) echo ollama;; *) echo lmstudio;; esac
}
_crew_remote_host() {   # fail (not exit: crew-check keeps going) when no remote is configured
  [ -n "${CREW_LMSTUDIO_SSH:-}" ] && return 0
  echo "crew: CREW_LMSTUDIO_SSH not set (crew/local.env)" >&2; return 1
}
crew_remote_lms() {   # run lms on the remote machine
  _crew_remote_host || return 1
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$CREW_LMSTUDIO_SSH" '~/.lmstudio/bin/lms' "$@"
}
crew_remote_tunnel() {   # idempotent: reuse a working tunnel, else open one in the background
  local port="$CREW_LMSTUDIO_TUNNEL_PORT"
  _crew_remote_host || return 1
  curl -fsS -m 5 -o /dev/null "http://127.0.0.1:$port/v1/models" 2>/dev/null && return 0
  ssh -fN -o BatchMode=yes -o ConnectTimeout=10 -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
    -L "127.0.0.1:$port:127.0.0.1:1234" "$CREW_LMSTUDIO_SSH" \
    || { echo "crew: could not open the tunnel to $CREW_LMSTUDIO_SSH" >&2; return 1; }
  curl -fsS -m 10 -o /dev/null "http://127.0.0.1:$port/v1/models" 2>/dev/null \
    || { echo "crew: tunnel to $CREW_LMSTUDIO_SSH is up but LM Studio's server is not answering" >&2; return 1; }
}

crew_space() {
  herdr workspace get "${HERDR_WORKSPACE_ID:?not inside a herdr pane}" 2>/dev/null | python3 -I -c '
import json,re,sys
label = json.load(sys.stdin)["result"]["workspace"].get("label") or ""
s = re.sub(r"[^a-z0-9_-]+", "-", label.lower()).strip("-")
print("" if s == "" or "coordinator" in s else s)   # e.g. "Acme Coordinator"'
}

crew_name() {
  local s; s=$(crew_space)
  if [ -n "$s" ]; then echo "$1-${CREW_ACCOUNT:?crew_env first}-$s" | cut -c1-32
  else echo "$1-${CREW_ACCOUNT:?crew_env first}"; fi
}
