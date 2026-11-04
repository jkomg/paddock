#!/usr/bin/env bash
# Verify this folder's crew before dispatch: the coordinator's account, each worker's login, and
# shared services. Prints identities only; never prints secrets.
# Usage: crew-check.sh [project-dir]   (default: current directory)
set -uo pipefail
DIR=$(cd "${1:-$PWD}" && pwd)
. "$(dirname "$0")/crew-lib.sh"

printf 'lead    : '; claude auth status 2>/dev/null | python3 -I -c 'import json,sys; d=json.load(sys.stdin); print(d.get("email"), "|", d.get("orgName"))' || echo unknown
RULES=$(python3 -I "$CREW_PROFILES/llm_profile.py" check "$DIR")
if crew_env "$DIR"; then
  crew_has gemini || RULES=$(printf '%s\n' "$RULES" | grep -v '^gemini')   # agy is not in this crew
  printf '%s\n' "$RULES" | sed 's/^/  rule  /'
else
  printf '%s\n' "$RULES" | sed 's/^/  rule  /'
  echo "=> no crew may run here for this coordinator: do not dispatch"; exit 3
fi
echo "crew    : $CREW_ACCOUNT ($CREW_WORKERS), usage ledger profile '$CREW_LEDGER'"

if crew_has codex; then
  printf 'codex   : '; python3 -I -c '
import json,base64,sys
t=(json.load(open(sys.argv[1])).get("tokens") or {}).get("id_token","")
p=t.split(".")[1]; p+="="*(-len(p)%4); c=json.loads(base64.urlsafe_b64decode(p))
print(c.get("email"), "|", c.get("https://api.openai.com/auth",{}).get("chatgpt_plan_type"))' "$CREW_CODEX_HOME/auth.json" 2>/dev/null || echo "NOT SIGNED IN ($CREW_CODEX_HOME)"
fi
if crew_has gemini; then
  printf 'gemini  : '; python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1])).get("active"))' "$HOME/.gemini/google_accounts.json" 2>/dev/null || echo unknown
fi
if crew_has qwen; then
  printf 'qwen    : '; curl -fsS http://127.0.0.1:8741/lmstudio/v1/models 2>/dev/null | python3 -I -c 'import json,sys; ids=[m["id"] for m in json.load(sys.stdin)["data"]]; print("gateway up; LM Studio", "qwen36-mlx loaded" if "qwen36-mlx" in ids else "qwen36-mlx NOT loaded (crew-up loads it)")' 2>/dev/null || echo "gateway or LM Studio DOWN (fallback: CREW_QWEN_BACKEND=ollama)"
fi
if crew_has litellm; then
  printf 'litellm : '
  if [ -n "${CREW_REVIEW_CMD:-}" ]; then $CREW_REVIEW_CMD status ${CREW_REVIEW_ARGS:-} --data-dir "$TF_PROFILES/$CREW_LEDGER/ledger" 2>&1 | tail -1
  else echo "CREW_REVIEW_CMD not set (crew/local.env)"; fi
fi

# T3 Code, if installed: one line (details: llm_profile.py t3-check). Informational only.
python3 -I "$CREW_PROFILES/llm_profile.py" t3-check --summary 2>/dev/null || true

echo; echo "Expected: every login above belongs to the $CREW_ACCOUNT account (qwen is local). Anything else -> do not dispatch."
