#!/usr/bin/env python3
"""Folder guard for Codex run by an app such as T3 Code (binaryPath = the t3-codex wrapper).

T3 runs one long-lived `codex app-server` per provider instance and sends each thread's folder
over its stdio JSON-RPC, so a launch wrapper never sees the folder. This proxy sits on that
stdio: it reads every request, learns each thread's cwd from the server's replies, and answers
with an error (without forwarding) when the instance's login may not work in a folder.

  t3-codex app-server [args]   guarded stdio proxy around the real `codex app-server`
  t3-codex exec ... (and other session commands)   refused if the current folder is not allowed
  t3-codex --version | login | mcp ...   passed straight through

Fail closed: a request on a thread whose cwd it has not seen (except pure reads, whose replies
teach it the cwd), a thread/start|resume|fork reply without a usable cwd, a JSON-RPC batch, or
an app-server mode it cannot watch (--listen on a socket, daemon) is refused. All other bytes
pass through unchanged, in order. The account is the CODEX_HOME login (T3 sets CODEX_HOME from
the instance's homePath), judged like the Claude hook: by the signed-in email.

This guards the folders a thread is opened in and paths named in requests. It is not a
sandbox: a full-access Codex turn can still run commands that touch other folders.
"""
import json
import os
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm_profile as lp  # noqa: E402

# Param keys (any depth) whose string or list-of-string values are filesystem paths.
PATH_KEYS = {
    "cwd", "cwds", "path", "paths", "sourcePath", "destinationPath", "roots", "savePath",
    "filePath", "extraRoots", "marketplacePath", "pluginPath", "writableRoots", "readableRoots",
    "runtimeWorkspaceRoots", "writable_roots", "readable_roots",
}
# Thread requests allowed before the thread's cwd is known: they only read, and their replies
# carry the cwd.
READ_OK = {"thread/read", "thread/turns/list", "thread/items/list", "thread/unsubscribe",
           "thread/loaded/list"}
OPENS_THREAD = {"thread/start", "thread/resume", "thread/fork"}
ERR_CODE = -32001
PASS_SUBCOMMANDS = {"--version", "-V", "--help", "-h", "help", "login", "logout", "mcp",
                    "completion", "features"}
APP_SERVER_PASS = {"generate-ts", "generate-json-schema", "help", "--help", "-h"}


def account():
    """(profile or None, label) for this process's CODEX_HOME."""
    home = os.environ.get("CODEX_HOME") or os.path.join(lp.HOME, ".codex")
    email = lp.codex_email(home)
    prof = lp.profile_of_email(email) if email else lp.profile_of_dir("codex", home, lp.profiles())
    return prof, "%s (%s)" % (email or "signed out", prof or "unrecognised")


def path_problem(prof, path):
    rule = lp.rule_for(path)
    if rule and prof not in rule[1]:
        return "%s allows only %s" % (lp.short(rule[0]), ", ".join(rule[1]) or "no login")
    return None


def named_paths(obj, key=None):
    """Every string under a PATH_KEYS key, at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from named_paths(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from named_paths(v, key)
    elif isinstance(obj, str) and key in PATH_KEYS and obj:
        yield obj


def thread_paths(result):
    """Folders a thread/start|resume|fork|read reply says the thread works in."""
    out = []
    if isinstance(result, dict):
        if isinstance(result.get("cwd"), str):
            out.append(result["cwd"])
        t = result.get("thread")
        if isinstance(t, dict):
            if isinstance(t.get("cwd"), str):
                out.append(t["cwd"])
            for env in t.get("environments") or []:
                if isinstance(env, dict):
                    out += [p for p in [env.get("cwd")] + list(env.get("runtimeWorkspaceRoots") or [])
                            if isinstance(p, str)]
    return [p for p in out if p]


class Guard:
    def __init__(self, prof, label, out):
        self.prof, self.label, self.out = prof, label, out
        self.lock = threading.Lock()       # guards threads, pending and writes to out
        self.threads = {}                  # threadId -> None (allowed) or reason (denied)
        self.pending = {}                  # request id (json) -> method

    def deny_msg(self, why):
        return "paddock: this Codex login is %s; %s. Use that account's Codex instance." % (self.label, why)

    def learn(self, thread, extra=()):
        """Record a Thread object's verdict. Returns the denial reason or None."""
        if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
            return None
        paths = list(extra) + thread_paths({"thread": thread})
        if not paths:
            why = "the folder of thread %s is unknown" % thread["id"]
        else:
            why = next((w for w in (path_problem(self.prof, p) for p in paths) if w), None)
        self.threads[thread["id"]] = why
        return why

    # -------------------------------------------------- client -> server
    def check_request(self, method, params):
        """None to forward, or a reason to refuse."""
        if not isinstance(params, dict):
            params = {}
        tid = params.get("threadId")
        for p in named_paths(params):
            if not os.path.isabs(os.path.expanduser(p)):
                return "relative path %r: the guard cannot tell which folder it means" % p
            why = path_problem(self.prof, p)
            if why:
                return why
        if isinstance(tid, str):
            if tid in self.threads:
                return self.threads[tid]
            if method in OPENS_THREAD or method in READ_OK:
                return None  # the reply tells us the folder
            return "thread %s has not been opened through this guard, so its folder is unknown" % tid
        return None

    def from_client(self, line):
        try:
            msg = json.loads(line)
        except ValueError:
            return line, None  # not JSON: the server rejects it
        if isinstance(msg, list):
            errs = [self.error(m.get("id"), "JSON-RPC batches are not supported by the paddock guard")
                    for m in msg if isinstance(m, dict) and "id" in m]
            return None, b"".join(errs) or None
        if not isinstance(msg, dict) or not isinstance(msg.get("method"), str):
            return line, None  # a response to a server request, or something the server rejects
        with self.lock:
            why = self.check_request(msg["method"], msg.get("params"))
            if why is None:
                if "id" in msg:
                    self.pending[json.dumps(msg["id"])] = msg["method"]
                return line, None
        if "id" not in msg:
            return None, None  # refused notification: drop it
        return None, self.error(msg["id"], self.deny_msg(why))

    # -------------------------------------------------- server -> client
    def from_server(self, line):
        try:
            msg = json.loads(line)
        except ValueError:
            return line
        if not isinstance(msg, dict):
            return line
        with self.lock:
            if "method" in msg:
                params = msg.get("params")
                if isinstance(params, dict) and isinstance(params.get("thread"), dict):
                    self.learn(params["thread"])
                return line
            if "id" not in msg:
                return line
            method = self.pending.pop(json.dumps(msg["id"]), None)
            result = msg.get("result")
            if method is None or not isinstance(result, dict):
                return line
            if method == "thread/list":
                for t in result.get("data") or []:
                    self.learn(t)
                return line
            if isinstance(result.get("thread"), dict) or method in OPENS_THREAD:
                top = [result["cwd"]] if isinstance(result.get("cwd"), str) else []
                why = self.learn(result.get("thread"), top)
                if method in OPENS_THREAD and (why or not isinstance(result.get("thread"), dict)):
                    return self.error(msg["id"], self.deny_msg(why or "the reply named no thread folder"))
            return line

    def error(self, mid, message):
        return (json.dumps({"id": mid, "error": {"code": ERR_CODE, "message": message}}) + "\n").encode()

    def write(self, data):
        with self.lock:
            self.out.write(data)
            self.out.flush()


CODEX_DIRS = ("~/.local/bin", "/opt/homebrew/bin", "/usr/local/bin")


def real_codex():
    """The real codex binary: $PADDOCK_CODEX_BIN, else the first `codex` on PATH, then in the
    usual install dirs (GUI apps such as T3 often lack ~/.local/bin on PATH). Never t3-codex
    itself or a launcher for it, which would loop."""
    explicit = os.environ.get("PADDOCK_CODEX_BIN")
    if explicit:
        return os.path.expanduser(explicit)
    dirs = os.environ.get("PATH", "").split(os.pathsep) + [os.path.expanduser(d) for d in CODEX_DIRS]
    for d in dirs:
        c = os.path.join(d, "codex")
        if d and os.path.isfile(c) and os.access(c, os.X_OK) and not lp.is_codex_guard(c):
            return c
    return None


def refuse(msg):
    print("t3-codex: " + msg, file=sys.stderr)
    return 3


def run_proxy(cmd, prof, label):
    child = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out = sys.stdout.buffer
    guard = Guard(prof, label, out)

    def pump_server():
        for line in iter(child.stdout.readline, b""):
            guard.write(guard.from_server(line))

    t = threading.Thread(target=pump_server, daemon=True)
    t.start()
    try:
        for line in iter(sys.stdin.buffer.readline, b""):
            fwd, reply = guard.from_client(line)
            if reply:
                guard.write(reply)
            if fwd:
                child.stdin.write(fwd)
                child.stdin.flush()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        try:
            child.stdin.close()
        except OSError:
            pass
    code = child.wait()
    t.join(timeout=5)
    return code


def main(argv):
    codex = real_codex()
    if not codex:
        return refuse("cannot find the real codex binary on PATH or in %s; set PADDOCK_CODEX_BIN "
                      "to its full path" % ", ".join(CODEX_DIRS))
    first = argv[0] if argv else ""
    if first in PASS_SUBCOMMANDS:
        os.execv(codex, [codex] + argv)
    prof, label = account()
    if first == "app-server":
        rest = argv[1:]
        if any(a in APP_SERVER_PASS for a in rest):
            os.execv(codex, [codex] + argv)
        if "daemon" in rest:
            return refuse("`app-server daemon` serves a socket the guard cannot watch; refused")
        for i, a in enumerate(rest):
            v = a.split("=", 1)[1] if a.startswith("--listen=") else (
                rest[i + 1] if a == "--listen" and i + 1 < len(rest) else None)
            if v is not None and v != "stdio://":
                return refuse("`--listen %s` serves a socket the guard cannot watch; refused" % v)
        return run_proxy([codex] + argv, prof, label)
    # Any other command runs a session in a folder: the current one, or -C/--cd DIR.
    folders = [os.getcwd()]
    for i, a in enumerate(argv):
        if a in ("-C", "--cd") and i + 1 < len(argv):
            folders.append(os.path.join(os.getcwd(), os.path.expanduser(argv[i + 1])))
        elif a.startswith("--cd="):
            folders.append(os.path.join(os.getcwd(), os.path.expanduser(a[5:])))
    for f in folders:
        why = path_problem(prof, f)
        if why:
            return refuse("this Codex login is %s; %s" % (label, why))
    os.execv(codex, [codex] + argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
