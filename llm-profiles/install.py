#!/usr/bin/env python3
"""Install Claude hooks on macOS/Linux/Windows, plus optional zsh routing.

Run from a permanent checkout; no symlinks or administrator privileges required.
Configuration stays alongside llm_profile.py, or in LLM_PROFILES_DIR.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_profile as lp


def save(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = Path(str(path) + ".llm-profiles-bak")
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--shell", choices=("zsh", "none"),
                        default="none" if os.name == "nt" else "zsh")
    args = parser.parse_args(argv)
    # Read and validate all inputs before modifying anything.
    dirs = [lp.claude_dir_path(d) for p in lp.profiles().values() for d in p["claude_dirs"]]
    list(lp.folders())
    for _, tool, inst in lp.t3_instances() or []:
        if tool == "claude":
            d = lp.claude_dir_path(lp.t3_home(tool, inst))
            dirs.append(d)
            print("T3 Code : Claude dir " + d)
    dirs += [os.path.expanduser(d) for d in os.environ.get(
        "LLM_PROFILES_EXTRA_CLAUDE_DIRS", "").split(os.pathsep) if d]
    changes = []
    seen = set()
    for directory in dirs:
        path = Path(directory).resolve() / "settings.json"
        key = os.path.normcase(str(path))
        if key in seen or (args.uninstall and not path.exists()):
            continue
        seen.add(key)
        data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
        hooks = data.setdefault("hooks", {})
        for event, matcher in (("SessionStart", "^(startup|resume|clear|compact|fork)$"),
                               ("PreToolUse", "Bash|Read|Edit|Write|NotebookEdit|Glob|Grep")):
            entries = []
            for entry in hooks.get(event, []):
                # Preserve other hooks sharing a matcher with a previous paddock hook.
                # Any earlier Paddock form counts, e.g. one naming an interpreter since upgraded away.
                kept = [h for h in entry.get("hooks", []) if not lp.hook_command_parts(h.get("command"))]
                if kept:
                    entries.append(dict(entry, hooks=kept))
            if not args.uninstall:
                entries.append({"matcher": matcher, "hooks": [
                    {"type": "command", "command": lp.HOOK_CMD, "timeout": 10}]})
            if entries:
                hooks[event] = entries
            else:
                hooks.pop(event, None)
        if not hooks:
            data.pop("hooks", None)
        changes.append((path, json.dumps(data, indent=2) + "\n"))

    if args.shell == "zsh":
        zsh = shutil.which("zsh")
        if not zsh:
            parser.error("zsh is not installed; use --shell none for hooks only")
        rc = Path(lp.HOME) / ".zshrc"
        text = rc.read_text(encoding="utf-8") if rc.exists() else ""
        text = "".join(line for line in text.splitlines(keepends=True)
                       if not line.rstrip().endswith("# llm-profiles"))
        if not args.uninstall:
            # Guarded, so a moved or deleted checkout does not break every new shell.
            source = shlex.quote(lp.stable_path("llm-profile.zsh"))
            text = text.rstrip("\n") + "\n[[ -f %s ]] && source %s  # llm-profiles\n" % (source, source)
        subprocess.run([zsh, "-n"], input=text, text=True, check=True)
        if rc.exists() or not args.uninstall:
            changes.insert(0, (rc, text))
    for path, text in changes:
        save(path, text)
        print(("removed : " if args.uninstall else "installed: ") + str(path))
    if not args.uninstall:
        # Say which path the hook names: a checkout path breaks the guard if the checkout moves.
        script = lp.HOOK_ARGS[2]
        print("hook    : " + lp.HOOK_CMD)
        if not script.startswith(lp.STABLE_DIR + os.sep):
            if os.path.lexists(lp.STABLE_DIR):
                print("WARN    : %s does not lead to this checkout (it resolves to %s); the hook names "
                      "the checkout path instead" % (lp.STABLE_DIR, os.path.realpath(lp.STABLE_DIR)))
            print("note    : rerun install after moving this checkout, or the guard cannot start")
    print("Done. Restart affected sessions. " + (
        "Open a new zsh terminal for routing." if args.shell == "zsh" else
        "Hooks only; shell routing and herdr crew are separate."))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as e:
        print("paddock install: " + str(e), file=sys.stderr)
        sys.exit(1)
