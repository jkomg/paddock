#!/usr/bin/env python3
"""Keep each LLM login inside the folders it is allowed to work in.

Rules live next to this file: profiles.tsv (logins) and folders.tsv (folder -> allowed logins).

  llm_profile.py resolve <claude|codex> <dir> [profile]   print the config dir to use, or refuse (exit 3)
  llm_profile.py check-gemini <dir>                        refuse (exit 3) if the active Gemini login is not allowed
  llm_profile.py check <dir>                               report every login against the folder's rule
  llm_profile.py crew-env <dir>                            shell vars for this folder's crew (crews.tsv)
  llm_profile.py hook                                      Claude Code SessionStart / PreToolUse hook (JSON on stdin)
  llm_profile.py names | claude-dirs                       helpers for llm-profile.zsh and install.sh

The hook is a guard against mistakes, not a sandbox: it checks file-tool paths, the session
folder, and paths it can see in Bash commands. It never prints tokens or secrets.
"""
import base64
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, "Projects")


def _rows(name):
    with open(os.path.join(HERE, name)) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.strip() and not line.lstrip().startswith("#"):
                yield [c.strip() for c in line.split("\t")]


def profiles():
    out = {}
    for row in _rows("profiles.tsv"):
        name, match, claude_dir, codex_home = row[:4]
        out[name] = {
            "match": [m for m in match.split(",") if m],
            "claude": claude_dir if claude_dir == "default" else os.path.expanduser(claude_dir),
            "codex": os.path.expanduser(codex_home),
            "aliases": [a for a in (row[4] if len(row) > 4 else "").split(",") if a],
        }
    return out


def cmd_names():
    """name=profile lines for the shell wrappers: each profile, plus its optional aliases."""
    for name, p in profiles().items():
        for n in [name] + p["aliases"]:
            print("%s=%s" % (n, name))
    return 0


def cmd_claude_dirs():
    """Every profile's Claude config dir ("default" = ~/.claude), for install.sh."""
    seen = []
    for p in profiles().values():
        d = os.path.join(HOME, ".claude") if p["claude"] == "default" else p["claude"]
        if d not in seen:
            seen.append(d)
            print(d)
    return 0


def folders():
    rows = []
    for folder, allowed, default in _rows("folders.tsv"):
        rows.append((os.path.realpath(os.path.expanduser(folder)), allowed.split(","), default))
    return sorted(rows, key=lambda r: len(r[0]), reverse=True)


def rule_for(path):
    """(folder, allowed, default) for the longest folder containing path, or None if unrestricted."""
    p = os.path.realpath(os.path.expanduser(path))
    for folder, allowed, default in folders():
        if p == folder or p.startswith(folder + os.sep):
            return folder, allowed, default
    return None


def profile_of_email(email):
    email = (email or "").lower()
    for name, prof in profiles().items():
        if email and any(email.endswith(m.lower()) for m in prof["match"]):
            return name
    return None


def claude_email(config_dir=None):
    """Login email for a config dir; None = this process's CLAUDE_CONFIG_DIR, "default" = unset."""
    if config_dir is None:
        config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or "default"
    if config_dir == "default":
        path = os.path.join(HOME, ".claude.json")
    else:
        path = os.path.join(config_dir, ".claude.json")
    try:
        with open(path) as f:
            return (json.load(f).get("oauthAccount") or {}).get("emailAddress")
    except (OSError, ValueError):
        return None


def codex_email(home):
    try:
        with open(os.path.join(home, "auth.json")) as f:
            tok = (json.load(f).get("tokens") or {}).get("id_token", "")
        part = tok.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part)).get("email")
    except (OSError, ValueError, IndexError):
        return None


def gemini_email():
    try:
        with open(os.path.join(HOME, ".gemini", "google_accounts.json")) as f:
            return json.load(f).get("active")
    except (OSError, ValueError):
        return None


def short(path):
    return path.replace(HOME, "~", 1) if path.startswith(HOME) else path


# ---------------------------------------------------------------- resolve (shell wrappers)

def env_profile(tool, profs):
    """Profile already chosen by the environment (CLAUDE_CONFIG_DIR / CODEX_HOME), if it names one.

    Lets a pane started with an explicit login dir (crew-up, project-up) keep it in a folder
    whose default is another allowed account; the allowed-list check below still applies."""
    val = os.environ.get("CLAUDE_CONFIG_DIR" if tool == "claude" else "CODEX_HOME", "")
    if not val:
        return ""
    real = os.path.realpath(os.path.expanduser(val))
    for name, p in profs.items():
        t = p[tool]
        if t != "default" and os.path.realpath(os.path.expanduser(t)) == real:
            return name
    return ""


def cmd_resolve(tool, directory, explicit=""):
    profs = profiles()
    if explicit and explicit not in profs:
        return fail("unknown profile '%s' (known: %s)" % (explicit, ", ".join(profs)))
    rule = rule_for(directory)
    if rule is None:
        if explicit:
            print(profs[explicit][tool])
        return 0  # unrestricted folder, no profile asked for: empty output = leave the tool alone
    folder, allowed, default = rule
    chosen = explicit or env_profile(tool, profs) or default
    if chosen not in allowed:
        return fail("%s is a %s folder; the %s login is not allowed here (allowed: %s)"
                    % (short(folder), "/".join(allowed), chosen, ", ".join(allowed)))
    target = profs[chosen][tool]
    email = claude_email(target) if tool == "claude" else codex_email(target)
    if email and profile_of_email(email) != chosen:
        return fail("%s profile at %s is signed in as %s, not a %s login"
                    % (tool, "default location" if target == "default" else short(target), email, chosen))
    print(target)
    return 0


def cmd_check_gemini(directory):
    rule = rule_for(directory)
    if rule is None:
        return 0
    folder, allowed, _ = rule
    email = gemini_email()
    prof = profile_of_email(email)
    if prof not in allowed:
        return fail("Gemini is signed in as %s (%s); %s allows only %s. Switch accounts in agy yourself first."
                    % (email or "unknown", prof or "unknown profile", short(folder), ", ".join(allowed)))
    return 0


def cmd_check(directory):
    rule = rule_for(directory)
    if rule is None:
        print("folder  : %s is unrestricted" % short(os.path.realpath(directory)))
        return 0
    folder, allowed, default = rule
    print("folder  : %s allows %s (default %s)" % (short(folder), ", ".join(allowed), default))
    bad = 0
    lead = claude_email()
    for label, email in (("claude", lead), ("gemini", gemini_email())):
        prof = profile_of_email(email)
        ok = prof in allowed
        bad += not ok
        print("%-8s: %s -> %s %s" % (label, email or "unknown", prof or "?", "OK" if ok else "NOT ALLOWED HERE"))
    return 3 if bad else 0


def crews():
    return {p: {"workers": w.split(","), "ledger": l} for p, w, l in _rows("crews.tsv")}


def cmd_crew_env(directory):
    """Shell assignments for this folder's crew. The crew always runs under the coordinator's own
    account: inside Claude Code (CLAUDECODE=1) that is the lead's login; from a plain shell it is
    CREW_PROFILE or the folder default. Refuses accounts the folder does not allow."""
    rule = rule_for(directory)
    if rule is None:
        return fail("%s is not in an account folder (%s); no crew here"
                    % (short(os.path.realpath(directory)), ", ".join(short(f) for f, _, _ in folders())))
    folder, allowed, default = rule
    if os.environ.get("CLAUDECODE") == "1":
        email = claude_email()
        prof = profile_of_email(email)
        if not prof:
            return fail("cannot tell which account this Claude session uses (%s)" % (email or "unknown"))
        asked = os.environ.get("CREW_PROFILE")
        if asked and asked != prof:
            return fail("CREW_PROFILE=%s but this coordinator is logged in as %s; a crew runs under its "
                        "coordinator's account" % (asked, prof))
    else:
        prof = os.environ.get("CREW_PROFILE") or default
    if prof not in allowed:
        return fail("%s allows %s; a %s crew may not work here" % (short(folder), ", ".join(allowed), prof))
    crew = crews().get(prof)
    if not crew:
        return fail("no crew defined for %s in crews.tsv" % prof)
    workers = crew["workers"]
    if "gemini" in workers and profile_of_email(gemini_email()) != prof:
        workers = [w for w in workers if w != "gemini"]
        print("llm-profile: gemini skipped: agy is signed in as %s" % (gemini_email() or "unknown"), file=sys.stderr)
    q = lambda s: "'" + s.replace("'", "'\\''") + "'"
    print("CREW_ACCOUNT=%s" % q(prof))
    print("CREW_WORKERS=%s" % q(" ".join(workers)))
    print("CREW_LEDGER=%s" % q(crew["ledger"]))
    print("CREW_CODEX_HOME=%s" % q(profiles()[prof]["codex"]))
    return 0


def fail(msg):
    print("llm-profile: " + msg, file=sys.stderr)
    return 3


# ---------------------------------------------------------------- Claude Code hook

PATH_KEYS = ("file_path", "notebook_path", "path")
ABS_RE = re.compile(r"(?:~|\$HOME|\$\{HOME\}|" + re.escape(HOME) + r")(/[^\s'\";|&<>()`]*)")
TOKEN_RE = re.compile(r"[^\s'\";|&<>()`=]+")


def bash_paths(command, cwd):
    """Paths a Bash command visibly names: ~/... forms, plus relative ones resolved from cwd
    (any token with a slash, "..", or the bare name of a rule folder)."""
    found = [HOME + m.group(1) for m in ABS_RE.finditer(command)]
    bare = {".."} | {os.path.basename(f) for f, _, _ in folders()}
    for tok in TOKEN_RE.findall(command):
        if "://" in tok or tok.startswith(("/", "~", "$", "-")):
            continue
        if "/" in tok or tok in bare:
            found.append(os.path.normpath(os.path.join(cwd, tok)))
    return found


def violations(email, paths):
    prof = profile_of_email(email)
    out = []
    for p in paths:
        rule = rule_for(p)
        if rule and prof not in rule[1]:
            out.append((short(rule[0]), rule[1]))
    return prof, sorted(set((f, tuple(a)) for f, a in out))


def cmd_hook():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    cwd = event.get("cwd") or os.getcwd()
    email = claude_email()
    name = event.get("hook_event_name")
    if name == "SessionStart":
        prof, bad = violations(email, [cwd])
        if bad:
            folder, allowed = bad[0]
            msg = ("LLM PROFILE GUARD: this session's Claude login is %s (%s), but %s allows only %s. "
                   "Every tool call in that folder will be denied. Tell the user to restart with the "
                   "right login (cd there and run `claude`; the shell wrapper picks it)."
                   % (email or "unknown", prof or "unrecognised", folder, ", ".join(allowed)))
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg},
                              "systemMessage": msg}))
        return 0
    if name != "PreToolUse":
        return 0
    tool_input = event.get("tool_input") or {}
    paths = [cwd]
    for key in PATH_KEYS:
        v = tool_input.get(key)
        if isinstance(v, str) and v:
            paths.append(v if os.path.isabs(os.path.expanduser(v)) else os.path.join(cwd, v))
    if event.get("tool_name") == "Bash":
        paths += bash_paths(tool_input.get("command") or "", cwd)
    prof, bad = violations(email, paths)
    if not bad:
        return 0
    reason = "; ".join("%s allows only %s" % (f, ", ".join(a)) for f, a in bad)
    reason = ("LLM profile guard: this Claude login is %s (%s). %s. Do not work around this; "
              "tell the user which folder needs which login."
              % (email or "unknown", prof or "unrecognised", reason))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    return 0


def main(argv):
    if len(argv) >= 3 and argv[0] == "resolve" and argv[1] in ("claude", "codex"):
        return cmd_resolve(argv[1], argv[2], argv[3] if len(argv) > 3 else "")
    if argv == ["names"]:
        return cmd_names()
    if argv == ["claude-dirs"]:
        return cmd_claude_dirs()
    if len(argv) == 2 and argv[0] == "check-gemini":
        return cmd_check_gemini(argv[1])
    if len(argv) == 2 and argv[0] == "crew-env":
        return cmd_crew_env(argv[1])
    if len(argv) == 2 and argv[0] == "check":
        return cmd_check(argv[1])
    if argv == ["hook"]:
        return cmd_hook()
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
