#!/usr/bin/env bash
# One-screen summary of this coordinator's project leads: Space, herdr state, and the first line
# of each lead's .handoffs/lead/status.md. Shows only leads of the coordinator's own account.
# Usage: projects.sh [--all]   (--all also lists this account's crew workers per Space)
set -uo pipefail
. "$(dirname "$0")/crew-lib.sh"
crew_env "$PWD" >/dev/null 2>&1 || { echo "projects: run from a folder your account works in (e.g. the coordinator's project root)" >&2; exit 1; }
herdr agent list | python3 -I -c '
import json, os, sys
acct, show_all = sys.argv[1], sys.argv[2] == "--all"
agents = json.load(sys.stdin)["result"]["agents"]
spaces = {}
import subprocess
for w in json.loads(subprocess.run(["herdr", "workspace", "list"], capture_output=True, text=True).stdout)["result"]["workspaces"]:
    spaces[w["workspace_id"]] = w.get("label") or w["workspace_id"]
leads = [a for a in agents if (a.get("name") or "").startswith("lead-%s-" % acct)]
if not leads:
    print("no %s project leads running (start one with project-up.sh)" % acct)
for a in sorted(leads, key=lambda a: a["name"]):
    ws = a["pane_id"].split(":")[0]
    st = os.path.join(a["cwd"], ".handoffs", "lead", "status.md")
    try:
        first = open(st).readline().strip() or "(empty status.md)"
    except OSError:
        first = "(no status.md yet)"
    flag = "  <- needs the user" if a["agent_status"] == "blocked" or "waiting-user" in first else ""
    print("%-30s %-16s %-8s %s%s" % (a["name"], spaces.get(ws, ws)[:16], a["agent_status"], first[:110], flag))
    if show_all:
        for w in agents:
            n = w.get("name") or ""
            if w["pane_id"].split(":")[0] == ws and n != a["name"] and ("-%s" % acct) in n:
                print("    %-26s %-8s" % (n, w["agent_status"]))
' "$CREW_ACCOUNT" "${1:-}"
