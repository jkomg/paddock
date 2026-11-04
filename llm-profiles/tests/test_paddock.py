"""Tests for llm_profile.py, codex_guard.py and install.sh, in a throwaway HOME.

    python3 -m unittest discover -s llm-profiles/tests -v

Uses the sample accounts acme / globex / personal. The integration test runs the installed
`codex app-server` (skipped when codex is not on PATH); it needs no login.
"""
import base64
import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SANDBOX = tempfile.mkdtemp(prefix="paddock-test-")
HOME = os.path.join(SANDBOX, "home")
CFG = os.path.join(SANDBOX, "cfg")
P = lambda *a: os.path.join(HOME, *a)


def jwt(email):
    body = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).decode().rstrip("=")
    return "x.%s.y" % body


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def setup_sandbox():
    os.makedirs(HOME, exist_ok=True)
    os.makedirs(CFG, exist_ok=True)
    write(os.path.join(CFG, "profiles.tsv"),
          "# profile\tmatch\tclaude\tcodex\taliases\n"
          "acme\t@acme.example\tdefault\t~/.codex\n"
          "globex\t@globex.example\t~/.claude-globex,~/.t3claude-globex\t~/.codex-globex\tgx\n"
          "personal\tyou@example.com\t~/.claude-personal\t~/.codex-personal\n")
    write(os.path.join(CFG, "folders.tsv"),
          "~/Projects/acme\tacme\tacme\n"
          "~/Projects/globex\tglobex\tglobex\n"
          "~/Projects/personal\tpersonal\tpersonal\n"
          "~/Projects/joint\tacme,globex\tacme\n")
    for d in ("acme", "globex", "personal", "joint"):
        os.makedirs(P("Projects", d), exist_ok=True)
    write(P(".claude.json"), json.dumps({"oauthAccount": {"emailAddress": "me@acme.example"}}))
    write(P(".claude-globex", ".claude.json"), json.dumps({"oauthAccount": {"emailAddress": "me@globex.example"}}))
    write(P(".codex", "auth.json"), json.dumps({"tokens": {"id_token": jwt("me@acme.example")}}))
    write(P(".codex-globex", "auth.json"), json.dumps({"tokens": {"id_token": jwt("me@globex.example")}}))


def env(**extra):
    e = dict(os.environ, HOME=HOME, LLM_PROFILES_DIR=CFG)
    for k in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "CLAUDECODE", "PADDOCK_CODEX_BIN", "LLM_PROFILES_T3_DIR"):
        e.pop(k, None)
    e.update(extra)
    return e


def read(path, mode="r"):
    with open(path, mode) as f:
        return f.read()


def load_json(path):
    return json.loads(read(path))


def run(args, **kw):
    return subprocess.run(args, env=kw.pop("env", None) or env(), capture_output=True, text=True, **kw)


def load():
    os.environ.update(HOME=HOME, LLM_PROFILES_DIR=CFG)
    sys.path.insert(0, SRC)
    import llm_profile
    import codex_guard
    importlib.reload(llm_profile)
    importlib.reload(codex_guard)
    return llm_profile, codex_guard


def setUpModule():
    global lp, cg, OLD_ENV
    OLD_ENV = dict(os.environ)
    setup_sandbox()
    lp, cg = load()


def tearDownModule():
    os.environ.clear()
    os.environ.update(OLD_ENV)
    shutil.rmtree(SANDBOX, ignore_errors=True)


def make_worktree(main, wt, relative=False, commondir=True, name="wt"):
    """A linked worktree at wt of the repo at main, laid out the way `git worktree add` does."""
    gitdir = os.path.join(main, ".git", "worktrees", name)
    os.makedirs(gitdir, exist_ok=True)
    if commondir:
        write(os.path.join(gitdir, "commondir"), "../..\n")
    os.makedirs(wt, exist_ok=True)
    target = os.path.relpath(gitdir, wt) if relative else gitdir
    write(os.path.join(wt, ".git"), "gitdir: %s\n" % target)


# ------------------------------------------------------------------ worktrees

class Worktrees(unittest.TestCase):
    def allowed(self, path):
        r = lp.rule_for(path)
        return None if r is None else sorted(r[1])

    def test_normal_repo(self):
        repo = P("Projects", "globex", "app")
        os.makedirs(os.path.join(repo, ".git"), exist_ok=True)
        self.assertEqual(self.allowed(os.path.join(repo, "src", "x.py")), ["globex"])
        self.assertIsNone(lp.worktree_main(repo))

    def test_worktree_outside_rule_folders_follows_main(self):
        main = P("Projects", "globex", "svc")
        wt = P(".t3", "worktrees", "svc", "feature")
        make_worktree(main, wt)
        self.assertEqual(lp.worktree_main(os.path.join(wt, "deep", "file")), os.path.realpath(main))
        self.assertEqual(self.allowed(os.path.join(wt, "deep", "file")), ["globex"])
        self.assertEqual(lp.rule_for(wt)[0], os.path.realpath(P("Projects", "globex")))

    def test_worktree_inside_rule_folder_needs_both(self):
        main = P("Projects", "globex", "svc2")
        wt = P("Projects", "joint", "svc2-wt")
        make_worktree(main, wt, name="j")
        self.assertEqual(self.allowed(wt), ["globex"])            # joint allows acme,globex
        wt2 = P("Projects", "acme", "svc2-wt")
        make_worktree(main, wt2, name="a")
        self.assertEqual(self.allowed(wt2), [])                   # acme-only and globex-only

    def test_worktree_of_unrestricted_repo_inside_rule_folder(self):
        main = P("scratch", "free")
        wt = P("Projects", "acme", "free-wt")
        make_worktree(main, wt)
        self.assertEqual(self.allowed(wt), ["acme"])

    def test_relative_gitdir(self):
        main = P("Projects", "personal", "rel")
        wt = P("wts", "rel")
        make_worktree(main, wt, relative=True)
        self.assertEqual(self.allowed(wt), ["personal"])

    def test_no_commondir_and_bare_repo(self):
        main = P("Projects", "globex", "plain")
        wt = P("wts", "nocommon")
        make_worktree(main, wt, commondir=False)
        self.assertEqual(self.allowed(wt), ["globex"])
        bare = P("Projects", "globex", "bare.git")
        os.makedirs(os.path.join(bare, "worktrees", "b"), exist_ok=True)
        wt2 = P("wts", "bare")
        write(os.path.join(wt2, ".git"), "gitdir: %s\n" % os.path.join(bare, "worktrees", "b"))
        self.assertEqual(lp.worktree_main(wt2), os.path.realpath(bare))
        self.assertEqual(self.allowed(wt2), ["globex"])

    def test_odd_gitdir_is_not_a_worktree(self):
        wt = P("wts", "odd")
        write(os.path.join(wt, ".git"), "gitdir: %s\n" % P("Projects", "globex", "elsewhere"))
        self.assertIsNone(lp.worktree_main(wt))
        self.assertIsNone(self.allowed(wt))
        sub = P("Projects", "acme", "super", "sub")
        write(os.path.join(sub, ".git"), "gitdir: ../.git/modules/sub\n")   # submodule
        self.assertEqual(self.allowed(sub), ["acme"])
        junk = P("wts", "junk")
        write(os.path.join(junk, ".git"), "not a git file\n")
        self.assertIsNone(self.allowed(junk))

    def test_missing_main_repo_still_follows_named_folder(self):
        wt = P("wts", "orphan")
        write(os.path.join(wt, ".git"), "gitdir: %s\n" % P("Projects", "globex", "gone", ".git", "worktrees", "o"))
        self.assertFalse(os.path.exists(P("Projects", "globex", "gone")))
        self.assertEqual(self.allowed(wt), ["globex"])

    def test_hook_denies_wrong_login_in_worktree(self):
        main = P("Projects", "globex", "hooked")
        wt = P(".t3", "worktrees", "hooked", "w")
        make_worktree(main, wt)
        ev = {"hook_event_name": "PreToolUse", "cwd": wt, "tool_name": "Read",
              "tool_input": {"file_path": os.path.join(wt, "a.txt")}}
        r = run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "hook"], input=json.dumps(ev))
        self.assertIn('"deny"', r.stdout)                         # default login = acme
        r = run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "hook"], input=json.dumps(ev),
                env=env(CLAUDE_CONFIG_DIR=P(".claude-globex")))
        self.assertEqual(r.stdout.strip(), "")


# ------------------------------------------------------------------ profiles

class Profiles(unittest.TestCase):
    def test_multi_dir_claude_column(self):
        g = lp.profiles()["globex"]
        self.assertEqual(g["claude"], P(".claude-globex"))
        self.assertEqual(g["claude_dirs"], [P(".claude-globex"), P(".t3claude-globex")])
        r = run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "claude-dirs"])
        self.assertEqual(r.stdout.split(), [P(".claude"), P(".claude-globex"), P(".t3claude-globex"),
                                            P(".claude-personal")])

    def test_second_dir_counts_as_the_profile(self):
        os.makedirs(P(".t3claude-globex"), exist_ok=True)
        r = run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "resolve", "claude",
                 P("Projects", "joint")], env=env(CLAUDE_CONFIG_DIR=P(".t3claude-globex")))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, P(".claude-globex")))

    def test_old_single_dir_rows_still_work(self):
        self.assertEqual(lp.profiles()["personal"]["claude_dirs"], [P(".claude-personal")])
        self.assertEqual(lp.profiles()["acme"]["claude"], "default")


# ------------------------------------------------------------------ T3 check

def make_t3(root, instances, projects):
    write(os.path.join(root, "userdata", "settings.json"), json.dumps({"providerInstances": instances}))
    db = os.path.join(root, "userdata", "statev2.sqlite")
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE projection_projects (project_id TEXT, title TEXT, workspace_root TEXT, deleted_at TEXT)")
    con.execute("CREATE TABLE projection_threads (thread_id TEXT, title TEXT, worktree_path TEXT, deleted_at TEXT)")
    for n, p in enumerate(projects):
        con.execute("INSERT INTO projection_projects VALUES (?,?,?,NULL)", (str(n), os.path.basename(p), p))
    con.execute("INSERT INTO projection_projects VALUES ('gone','gone',?, '2026-01-01')", (P("Projects", "personal", "gone"),))
    con.commit()
    con.close()


class T3Check(unittest.TestCase):
    def setUp(self):
        self.t3 = os.path.join(SANDBOX, "t3-%s" % self._testMethodName)
        guard = os.path.join(SRC, "t3-codex")
        make_t3(self.t3, {
            "claudeAgent": {"driver": "claudeAgent", "displayName": "Claude Acme", "enabled": True},
            "claude_gx": {"driver": "claudeAgent", "displayName": "Claude Globex", "enabled": True,
                          "config": {"homePath": "~/.t3claude-globex"}},
            "codex": {"driver": "codex", "displayName": "Codex Acme", "enabled": True},
            "codex_gx": {"driver": "codex", "displayName": "Codex Globex", "enabled": True,
                         "config": {"homePath": P(".codex-globex"), "binaryPath": guard}},
            "codex_odd": {"driver": "codex", "displayName": "Codex Odd", "enabled": False,
                          "config": {"homePath": P(".codex-odd")}},
            "oc": {"driver": "opencode", "displayName": "OpenCode", "enabled": True},
            "oc_gx": {"driver": "opencode", "displayName": "OpenCode Globex", "enabled": True,
                      "config": {"binaryPath": "~/bin/opencode-globex"}},
            "cur": {"driver": "cursor", "displayName": "Cursor", "enabled": True},
        }, [P("Projects", "acme", "a1"), P("Projects", "globex", "g1"), P("scratch")])
        write(os.path.join(CFG, "wrappers.tsv"), "~/bin/opencode-globex\tglobex\n")
        os.makedirs(P(".t3claude-globex"), exist_ok=True)
        write(P(".t3claude-globex", ".claude.json"), json.dumps({"oauthAccount": {"emailAddress": "me@globex.example"}}))
        write(P(".claude", "settings.json"), json.dumps({"hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": lp.HOOK_CMD}]}],
            "PreToolUse": [{"hooks": [{"type": "command", "command": lp.HOOK_CMD}]}]}}))

    def check(self, *args):
        return run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "t3-check"] + list(args),
                   env=env(LLM_PROFILES_T3_DIR=self.t3))

    def test_report(self):
        before = {f: read(os.path.join(self.t3, "userdata", f), "rb") for f in ("settings.json", "statev2.sqlite")}
        r = self.check()
        out = r.stdout
        self.assertEqual(r.returncode, 1, out + r.stderr)
        self.assertIn("Claude Acme (claude, enabled)\n  dir    : default (~/.claude) -> acme", out)
        self.assertIn("Claude Globex (claude, enabled)\n  dir    : ~/.t3claude-globex -> globex", out)
        self.assertIn("NO HOOK", out.split("Claude Globex")[1].split("Codex")[0])
        self.assertIn("Codex Acme (codex, enabled)", out)
        acme = out.split("Codex Acme")[1].split("Codex Globex")[0]
        self.assertIn("UNGUARDED", acme)
        self.assertIn("~/Projects/globex/g1", acme)
        self.assertIn("NOT blocked", acme)
        gx = out.split("Codex Globex")[1].split("\nCursor")[0]
        self.assertIn("t3-codex guard", gx)
        self.assertIn("~/Projects/acme/a1", gx)
        self.assertNotIn("WARN", gx)
        self.assertIn("-> UNKNOWN", out.split("Codex Odd")[1])
        oc = out.split("OpenCode (opencode, enabled)")[1].split("OpenCode Globex")[0]
        self.assertIn("unmapped, unmetered", oc)
        self.assertIn("UNGUARDED", oc)
        ocg = out.split("OpenCode Globex (opencode, enabled)")[1].split("\nC")[0]
        self.assertIn("account: globex", ocg)
        self.assertIn("~/Projects/acme/a1", ocg)
        cur = out.split("Cursor (cursor, enabled)")[1].split("\nOpenCode")[0]
        self.assertIn("unmapped (in-process Cursor SDK", cur)
        self.assertIn("can open all 2 T3 project folder(s)", cur)
        self.assertNotIn("gone", out)                              # deleted project
        self.assertIn("5 warning(s)", out)   # hook missing, unguarded codex, 2 OpenCode, Cursor
        after = {f: read(os.path.join(self.t3, "userdata", f), "rb") for f in before}
        self.assertEqual(before, after)
        self.assertFalse(os.path.exists(os.path.join(self.t3, "userdata", "statev2.sqlite-wal")))

    def test_summary_and_dirs(self):
        r = self.check("--summary")
        self.assertIn("7 enabled provider instance(s), 5 warning(s)", r.stdout)
        r = run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "t3-claude-dirs"],
                env=env(LLM_PROFILES_T3_DIR=self.t3))
        self.assertEqual(r.stdout.split(), [P(".claude"), P(".t3claude-globex")])

    def test_no_t3(self):
        r = run([sys.executable, "-I", os.path.join(SRC, "llm_profile.py"), "t3-check"],
                env=env(LLM_PROFILES_T3_DIR=os.path.join(SANDBOX, "nothing")))
        self.assertEqual(r.returncode, 0)
        self.assertIn("no T3 settings", r.stdout)


# ------------------------------------------------------------------ install.sh

class Install(unittest.TestCase):
    def test_install_and_uninstall_cover_t3_dirs(self):
        home = os.path.join(SANDBOX, "ihome")
        cfg = os.path.join(home, ".config", "llm-profiles")
        os.makedirs(cfg, exist_ok=True)
        for f in ("llm_profile.py", "llm-profile.zsh", "install.sh"):
            shutil.copy(os.path.join(SRC, f), cfg)
        write(os.path.join(cfg, "profiles.tsv"), "acme\t@acme.example\t~/.claude-acme\t~/.codex\n")
        write(os.path.join(cfg, "folders.tsv"), "~/Projects/acme\tacme\tacme\n")
        write(os.path.join(home, ".zshrc"), "# rc\n")
        t3claude = os.path.join(home, "t3-claude")
        os.makedirs(os.path.join(home, ".claude-acme"))
        write(os.path.join(t3claude, "settings.json"), json.dumps({"theme": "dark"}))
        write(os.path.join(home, ".t3", "userdata", "settings.json"), json.dumps({"providerInstances": {
            "c": {"driver": "claudeAgent", "enabled": False, "config": {"homePath": "~/t3-claude"}},
            "x": {"driver": "codex", "enabled": True}}}))
        e = dict(os.environ, HOME=home)
        for k in ("LLM_PROFILES_DIR", "LLM_PROFILES_T3_DIR", "CLAUDE_CONFIG_DIR"):
            e.pop(k, None)
        r = subprocess.run(["bash", os.path.join(cfg, "install.sh")], env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("T3 Code", r.stdout)
        s = load_json(os.path.join(t3claude, "settings.json"))
        self.assertEqual(s["theme"], "dark")
        self.assertIn("PreToolUse", s["hooks"])
        self.assertTrue(os.path.exists(os.path.join(t3claude, "settings.json.llm-profiles-bak")))
        self.assertIn("PreToolUse", load_json(os.path.join(home, ".claude-acme", "settings.json"))["hooks"])
        r = subprocess.run(["bash", os.path.join(cfg, "install.sh"), "--uninstall"], env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(load_json(os.path.join(t3claude, "settings.json")), {"theme": "dark"})


# ------------------------------------------------------------------ Codex guard (unit)

def req(mid, method, **params):
    return (json.dumps({"id": mid, "method": method, "params": params}) + "\n").encode()


def reply(mid, result):
    return (json.dumps({"id": mid, "result": result}) + "\n").encode()


def thread(tid, cwd):
    return {"thread": {"id": tid, "cwd": cwd, "environments": [
        {"environmentId": "local", "cwd": cwd, "runtimeWorkspaceRoots": [cwd]}]}, "cwd": cwd}


class GuardUnit(unittest.TestCase):
    def setUp(self):
        self.g = cg.Guard("acme", "me@acme.example (acme)", None)
        self.ok = P("Projects", "acme", "proj")
        self.bad = P("Projects", "globex", "proj")

    def client(self, line):
        return self.g.from_client(line)

    def refused(self, line):
        fwd, rep = self.client(line)
        self.assertIsNone(fwd)
        self.assertIsNotNone(rep)
        msg = json.loads(rep)
        self.assertEqual(msg["error"]["code"], cg.ERR_CODE)
        return msg

    def test_allowed_thread_flow_passes_bytes_unchanged(self):
        line = req(1, "thread/start", cwd=self.ok)
        self.assertEqual(self.client(line), (line, None))
        r = reply(1, thread("t1", self.ok))
        self.assertEqual(self.g.from_server(r), r)
        line = req(2, "turn/start", threadId="t1", input=[])
        self.assertEqual(self.client(line), (line, None))
        note = b'{"method":"item/agentMessage/delta","params":{"threadId":"t1","delta":"hi"}}\n'
        self.assertEqual(self.g.from_server(note), note)

    def test_disallowed_cwd_refused_before_forwarding(self):
        msg = self.refused(req(1, "thread/start", cwd=self.bad))
        self.assertEqual(msg["id"], 1)
        self.assertIn("globex", msg["error"]["message"])

    def test_server_chosen_cwd_checked_in_reply(self):
        line = req(5, "thread/start")
        self.assertEqual(self.client(line), (line, None))
        out = json.loads(self.g.from_server(reply(5, thread("t5", self.bad))))
        self.assertIn("error", out)
        self.refused(req(6, "turn/start", threadId="t5", input=[]))

    def test_resume_reply_without_folder_fails_closed(self):
        self.client(req(7, "thread/resume", threadId="t7"))
        out = json.loads(self.g.from_server(reply(7, {"thread": {"id": "t7"}})))
        self.assertIn("unknown", out["error"]["message"])
        self.refused(req(8, "turn/start", threadId="t7", input=[]))
        self.client(req(9, "thread/resume", threadId="t9"))
        self.assertIn("error", json.loads(self.g.from_server(reply(9, {"cwd": self.ok}))))

    def test_unknown_thread_refused_but_reads_learn(self):
        self.refused(req(1, "turn/start", threadId="tx", input=[]))
        line = req(2, "thread/read", threadId="tx")
        self.assertEqual(self.client(line), (line, None))
        self.g.from_server(reply(2, thread("tx", self.ok)))
        line = req(3, "turn/start", threadId="tx", input=[])
        self.assertEqual(self.client(line), (line, None))

    def test_thread_list_and_started_notification_learn(self):
        self.client(req(1, "thread/list"))
        self.g.from_server(reply(1, {"data": [thread("a", self.ok)["thread"], thread("b", self.bad)["thread"]]}))
        self.assertEqual(self.client(req(2, "turn/start", threadId="a", input=[]))[1], None)
        self.refused(req(3, "turn/start", threadId="b", input=[]))
        self.g.from_server((json.dumps({"method": "thread/started", "params": thread("c", self.bad)}) + "\n").encode())
        self.refused(req(4, "turn/steer", threadId="c"))

    def test_paths_in_params(self):
        self.refused(req(1, "fs/readFile", path=os.path.join(self.bad, "x")))
        line = req(2, "fs/readFile", path=os.path.join(self.ok, "x"))
        self.assertEqual(self.client(line), (line, None))
        self.refused(req(3, "command/exec", command=["ls"], cwd=self.bad))
        self.refused(req(4, "skills/list", cwds=[self.ok, self.bad]))
        self.refused(req(5, "thread/start", cwd=self.ok, config={"sandbox_workspace_write": {"writable_roots": [self.bad]}}))
        self.refused(req(6, "fs/readFile", path="relative/x"))
        self.client(req(7, "thread/start", cwd=self.ok))
        self.g.from_server(reply(7, thread("t7", self.ok)))
        self.refused(req(8, "turn/start", threadId="t7", input=[], cwd=self.bad))
        line = req(9, "model/list")
        self.assertEqual(self.client(line), (line, None))

    def test_worktree_of_disallowed_repo(self):
        main = P("Projects", "globex", "wtrepo")
        wt = P(".t3", "worktrees", "wtrepo", "x")
        make_worktree(main, wt)
        self.refused(req(1, "thread/start", cwd=wt))

    def test_batches_notifications_and_junk(self):
        fwd, rep = self.client(b'[{"id":1,"method":"model/list"},{"method":"initialized"}]\n')
        self.assertIsNone(fwd)
        self.assertEqual(json.loads(rep)["id"], 1)
        self.assertEqual(self.client(b"not json\n"), (b"not json\n", None))
        n = b'{"method":"initialized"}\n'
        self.assertEqual(self.client(n), (n, None))
        self.assertEqual(self.client(b'{"method":"x","params":{"cwd":"%s"}}\n' % self.bad.encode()), (None, None))
        resp = b'{"id":"srv-1","result":{"decision":"accept"}}\n'
        self.assertEqual(self.client(resp), (resp, None))

    def test_unrecognised_account_denied_in_every_rule_folder(self):
        g = cg.Guard(None, "signed out (unrecognised)", None)
        fwd, rep = g.from_client(req(1, "thread/start", cwd=self.ok))
        self.assertIsNone(fwd)
        line = req(2, "thread/start", cwd=P("scratch"))
        self.assertEqual(g.from_client(line), (line, None))


# ------------------------------------------------------------------ t3-codex wrapper

class Wrapper(unittest.TestCase):
    def setUp(self):
        self.log = os.path.join(SANDBOX, "fake-%s.log" % self._testMethodName)
        self.fake = os.path.join(SANDBOX, "fakecodex")
        write(self.fake, "#!/bin/sh\necho \"$PWD|$*\" >> \"%s\"\necho codex-cli 9.9.9\n" % self.log)
        os.chmod(self.fake, 0o755)

    def wrap(self, args, cwd, **e):
        return run([os.path.join(SRC, "t3-codex")] + args, cwd=cwd,
                   env=env(PADDOCK_CODEX_BIN=self.fake, CODEX_HOME=P(".codex"), **e))

    def calls(self):
        return read(self.log).splitlines() if os.path.exists(self.log) else []

    def test_version_passes_anywhere(self):
        r = self.wrap(["--version"], P("Projects", "globex"))
        self.assertEqual(r.stdout.strip(), "codex-cli 9.9.9")

    def test_exec_checks_folder(self):
        r = self.wrap(["exec", "-s", "read-only", "-"], P("Projects", "globex"))
        self.assertEqual(r.returncode, 3)
        self.assertEqual(self.calls(), [])
        r = self.wrap(["exec", "-C", P("Projects", "globex"), "-"], P("Projects", "acme"))
        self.assertEqual(r.returncode, 3)
        r = self.wrap(["exec", "-"], P("Projects", "acme"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.calls()), 1)

    def test_socket_modes_refused(self):
        for args in (["app-server", "--listen", "unix://"], ["app-server", "daemon", "start"],
                     ["app-server", "--listen=ws://127.0.0.1:1"]):
            self.assertEqual(self.wrap(args, P("scratch") if os.path.isdir(P("scratch")) else HOME).returncode, 3, args)
        self.assertEqual(self.wrap(["app-server", "--help"], HOME).returncode, 0)


# ------------------------------------------------------------------ against the installed codex

def installed_codex():
    for d in os.environ.get("PATH", "").split(os.pathsep) + [os.path.expanduser("~/.local/bin")]:
        c = os.path.join(d, "codex")
        if os.path.isfile(c) and os.access(c, os.X_OK):
            try:
                out = subprocess.run([c, "--version"], capture_output=True, text=True, timeout=20).stdout
            except (OSError, subprocess.TimeoutExpired):
                continue
            if out.startswith("codex-cli"):
                return c
    return None


REAL_CODEX = installed_codex()


@unittest.skipUnless(REAL_CODEX, "codex not installed")
class GuardAgainstInstalledCodex(unittest.TestCase):
    def test_app_server_round_trip(self):
        chome = P(".codex-globex")                  # globex profile; signed in per auth.json
        start_dir = P("Projects", "acme")           # the server's own cwd: disallowed for globex
        p = subprocess.Popen([os.path.join(SRC, "t3-codex"), "app-server"], cwd=start_dir,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             env=env(PADDOCK_CODEX_BIN=REAL_CODEX, CODEX_HOME=chome))
        replies = {}

        def send(obj):
            p.stdin.write((json.dumps(obj) + "\n").encode())
            p.stdin.flush()

        def wait(mid, timeout=30):
            end = time.time() + timeout
            while time.time() < end and mid not in replies:
                line = p.stdout.readline()
                if not line:
                    break
                m = json.loads(line)
                if "id" in m and "method" not in m:
                    replies[m["id"]] = m
            return replies.get(mid)

        try:
            send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "paddock-test", "version": "0"}}})
            self.assertIn("result", wait(1))
            send({"method": "initialized"})
            ok_dir = P("Projects", "globex", "live")
            os.makedirs(ok_dir, exist_ok=True)
            send({"id": 2, "method": "thread/start", "params": {"cwd": ok_dir, "ephemeral": True}})
            r = wait(2)
            self.assertIn("result", r, r)
            tid = r["result"]["thread"]["id"]
            self.assertEqual(os.path.realpath(r["result"]["thread"]["cwd"]), os.path.realpath(ok_dir))
            send({"id": 3, "method": "thread/start", "params": {"cwd": P("Projects", "personal"), "ephemeral": True}})
            self.assertEqual(wait(3)["error"]["code"], cg.ERR_CODE)
            send({"id": 4, "method": "thread/start", "params": {"ephemeral": True}})   # server picks its cwd
            r = wait(4)
            self.assertEqual(r.get("error", {}).get("code"), cg.ERR_CODE, r)
            send({"id": 5, "method": "turn/start", "params": {"threadId": "00000000-0000-0000-0000-000000000000", "input": []}})
            self.assertEqual(wait(5)["error"]["code"], cg.ERR_CODE)
            send({"id": 6, "method": "thread/read", "params": {"threadId": tid}})
            self.assertIn("id", wait(6))
        finally:
            p.stdin.close()
            p.wait(timeout=30)
            p.stdout.close()


if __name__ == "__main__":
    unittest.main()
