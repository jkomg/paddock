#!/usr/bin/env bash
# Dispatch one bounded task to a crew worker and wait for its result file.
# Usage: delegate.sh <qwen|gemini|codex|litellm> <brief.md> [timeout-seconds] [max-lines]
# Prints: the result path and its first line (STATUS/MODEL). The lead reads result.md, nothing else.
set -euo pipefail

WORKER=$1; BRIEF=$2; TIMEOUT=${3:-300}; MAXLINES=${4:-60}
SKILL_DIR=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$BRIEF" ] || { echo "delegate: brief not found: $BRIEF" >&2; exit 2; }

# The crew runs under the coordinator's account; refuse workers that account does not have.
. "$SKILL_DIR/scripts/crew-lib.sh"
crew_env "$PWD" || { echo "delegate: no crew for this account in $PWD" >&2; exit 1; }
crew_has "$WORKER" || { echo "delegate: the $CREW_ACCOUNT crew has no '$WORKER' (workers: $CREW_WORKERS)" >&2; exit 2; }

# Run log: one JSON line per delegation in this account's usage ledger folder, joined to
# ledger events by worker source + project + time window. Read by `run.py report --profile`.
RUNS="$TF_PROFILES/$CREW_LEDGER/runs.jsonl"
mkdir -p "$(dirname "$RUNS")"
START=$(date -u +%Y-%m-%dT%H:%M:%SZ); RUN_ID=""; RUN_PROJECT=""
LEAD_SESSION=$(herdr pane current --current 2>/dev/null | python3 -I -c 'import json,sys; print((json.load(sys.stdin)["result"]["pane"].get("agent_session") or {}).get("value",""))' 2>/dev/null || true)
log_run() {
  local rc=$?; [ -n "$RUN_ID" ] || return 0
  python3 -I -c 'import json,sys; print(json.dumps(dict(zip(["run_id","worker","project","lead_session","start","end","account","exit"], sys.argv[1:8]+[int(sys.argv[8])]))))' \
    "$RUN_ID" "$WORKER" "$RUN_PROJECT" "$LEAD_SESSION" "$START" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CREW_ACCOUNT" "$rc" >> "$RUNS"
}
trap log_run EXIT

if [ "$WORKER" = litellm ]; then
  # Reviewer only: a bounded, budget-checked review command (CREW_REVIEW_CMD in crew/local.env).
  [ -n "${CREW_REVIEW_CMD:-}" ] || { echo "delegate: CREW_REVIEW_CMD is not set (crew/local.env)" >&2; exit 2; }
  ID=$(date +%Y%m%d-%H%M%S)-litellm; DIR="$PWD/.handoffs/$ID"; mkdir -p "$DIR"; cp "$BRIEF" "$DIR/task.md"
  RUN_ID=$ID; RUN_PROJECT=$(basename "$PWD")
  $CREW_REVIEW_CMD review ${CREW_REVIEW_ARGS:-} \
    --data-dir "$TF_PROFILES/$CREW_LEDGER/ledger" \
    --model "${CREW_LITELLM_MODEL:-claude-haiku-4-5}" --max-tokens "${CREW_LITELLM_MAX_TOKENS:-6000}" \
    --project "$RUN_PROJECT" --input "$DIR/task.md" > "$DIR/raw.json"
  # Reasoning models can spend the whole cap thinking: empty or cut-off text is PARTIAL, not DONE.
  python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); r=d.get("review") or ""
status = "PARTIAL" if not r.strip() or d.get("finish_reason") == "length" else "DONE"
print("STATUS: %s | reviewer: LiteLLM | finish=%s reasoning_tokens=%s usage_recorded=%s event=%s" % (
    status, d.get("finish_reason"), d.get("reasoning_tokens"), d.get("usage_recorded"), d.get("event_id")))
print(); print(r)' "$DIR/raw.json" > "$DIR/result.md"
  echo "$DIR/result.md ($(wc -l < "$DIR/result.md" | tr -d ' ') lines)"; exit 0
fi

[ "${HERDR_ENV:-}" = 1 ] || { echo "delegate: not inside a herdr pane" >&2; exit 1; }
AGENT=$(crew_name "$WORKER")   # herdr name of this account's worker in this Space
CWD=$(herdr agent get "$AGENT" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["result"]["agent"]["cwd"])') \
  || { echo "delegate: worker '$AGENT' not live; run crew-up.sh" >&2; exit 1; }

# qwen is a local model at ~40-50 tok/s that averages ~600 output tokens a call. Every
# qwen failure after the LM Studio switch (Oct-Nov 2026) was an oversized task: a ~20-doc
# read, and a 52-line brief to edit 3 files and write a test suite, which needed far more
# output than fits a 5-minute budget. Refuse those up front (exit 6) so the lead routes
# them to gemini (large reads) or codex (multi-file work). CREW_QWEN_FORCE=1 overrides.
if [ "$WORKER" = qwen ] && [ "${CREW_QWEN_FORCE:-0}" != 1 ]; then
  SIZE=$(python3 -I - "$BRIEF" "$CWD" <<'PY'
import os, re, sys
brief, root = open(sys.argv[1]).read(), sys.argv[2]
paths = {p.rstrip('.,:;)`') for p in re.findall(r'[\w./~-]+\.[A-Za-z]{1,5}\b|[\w-]+/[\w./-]+', brief)}
files = [p for p in paths if os.path.isfile(os.path.join(root, os.path.expanduser(p)))]
print(len(brief.splitlines()), len(files), sum(os.path.getsize(os.path.join(root, os.path.expanduser(p))) for p in files))
PY
)
  read -r B_LINES B_FILES B_BYTES <<< "$SIZE"
  if [ "$B_LINES" -gt 45 ] || [ "$B_FILES" -gt 4 ] || [ "$B_BYTES" -gt 61440 ]; then
    echo "delegate: brief too big for qwen ($B_LINES lines, $B_FILES files, $((B_BYTES/1024)) KB to read;" \
         "limits 45 / 4 / 60 KB). Split it, or send large reads to gemini and multi-file work to codex." \
         "CREW_QWEN_FORCE=1 overrides." >&2
    exit 6
  fi
fi


ID=$(date +%Y%m%d-%H%M%S)-$AGENT; REL=".handoffs/$ID"; DIR="$CWD/$REL"; mkdir -p "$DIR"
RUN_ID=$ID; RUN_PROJECT=$(basename "$CWD")
[ -d "$CWD/.git" ] && { grep -qx '.handoffs/' "$CWD/.git/info/exclude" 2>/dev/null || echo '.handoffs/' >> "$CWD/.git/info/exclude"; }
{ sed "s/{{ACCOUNT}}/$CREW_ACCOUNT/g" "$SKILL_DIR/worker-rules.md"; echo; echo "# Task"; echo; cat "$BRIEF"; echo
  echo "# Output"; echo; echo "Write your result to \`$REL/result.md\` (max $MAXLINES lines). Time budget: $TIMEOUT seconds."; } > "$DIR/task.md"

# Fresh context per task keeps worker tokens bounded (no accumulated history).
# Wait for the reset to settle; a prompt sent mid-reset is silently dropped.
# Codex: /new detaches herdr's session tracking and later prompts are silently lost
# (Codex 0.165 + herdr 0.9.3), so restart its pane instead; crew-up recreates only it.
case "$WORKER" in
  qwen)  herdr agent prompt "$AGENT" "/new" >/dev/null 2>&1 || true; sleep 4;;
  codex) herdr pane close "$(herdr agent get "$AGENT" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["result"]["agent"]["pane_id"])')" >/dev/null
         sleep 2; "$SKILL_DIR/scripts/crew-up.sh" "$CWD" >/dev/null;;
esac

T0=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# A prompt can be dropped while a fresh session is still drawing; herdr reports that as
# agent_prompt_stalled (no activity within 5s). Resend once in that case.
MSG="Read $REL/task.md and do exactly what it says. When result.md is written, reply only: DONE"
for attempt in 1 2; do
  out=$(herdr agent prompt "$AGENT" "$MSG" --wait --timeout 15000 2>&1 || true)
  echo "$out" | grep -q agent_prompt_stalled || break
  [ $attempt = 2 ] && { echo "delegate: $WORKER did not start the task (prompt stalled twice)" >&2; exit 5; }
  sleep 4
done

# herdr's idle/done can fire between retries, so the result file is the completion signal.
state() { herdr agent get "$AGENT" | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["result"]["agent"]["agent_status"])'; }
# herdr does not flag every approval UI as blocked (agy shows "idle"), so also match the screen.
approval() { herdr agent read "$AGENT" --lines 25 2>/dev/null | grep -qE 'Requesting permission|Run this command\?|Allow (once|always)|Do you want to|approve' ; }
END=$((SECONDS + TIMEOUT))
while [ $SECONDS -lt $END ]; do
  [ -s "$DIR/result.md" ] && { sleep 2; break; }        # let the writer finish
  if [ "$(state)" = blocked ] || approval; then
    echo "delegate: $WORKER is waiting for approval; show the user this prompt (never approve for them):" >&2
    herdr agent read "$AGENT" --lines 20 >&2; exit 4
  fi
  sleep 5
done

if [ -s "$DIR/result.md" ]; then
  echo "$DIR/result.md ($(wc -l < "$DIR/result.md" | tr -d ' ') lines)"; head -1 "$DIR/result.md"
  if [ "$WORKER" = qwen ]; then   # actual model + usage from the gateway ledger, not the worker's self-report
    PROJ_SQL=$(basename "$CWD"); PROJ_SQL=${PROJ_SQL//\'/\'\'}   # SQL-quote the folder name
    sqlite3 "$TF_PROFILES/$CREW_LEDGER/ledger/usage.sqlite3" "select 'gateway: '||json_extract(data,'$.model')||' calls='||count(*)||' in='||sum(json_extract(data,'$.input_tokens'))||' out='||sum(json_extract(data,'$.output_tokens')) from events where source in ('lmstudio-gateway','ollama-gateway') and json_extract(data,'$.project')='${PROJ_SQL}' and timestamp >= '$T0' group by json_extract(data,'$.model')"
  fi
else
  STATE=$(state)
  echo "delegate: no result.md from $WORKER (state: $STATE). If blocked, inspect with: herdr agent read $AGENT --lines 30" >&2; exit 3
fi
