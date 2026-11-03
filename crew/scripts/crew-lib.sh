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
