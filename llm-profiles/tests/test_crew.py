"""Crew script integration tests with fake herdr; never start a model or service."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.name != "nt", "crew uses Unix shells")
class Crew(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paddock-crew-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.project = self.home / "project"
        self.project.mkdir()
        self.worker = self.home / "worker"
        self.worker.mkdir()
        self.cfg = self.home / ".config" / "llm-profiles"
        self.cfg.mkdir(parents=True)
        shutil.copy2(ROOT / "llm-profiles" / "llm_profile.py", self.cfg)
        (self.cfg / "profiles.tsv").write_text("acme\t@acme.example\tdefault\t~/.codex\n")
        (self.cfg / "folders.tsv").write_text(str(self.home) + "\tacme\tacme\n")
        (self.cfg / "crews.tsv").write_text("acme\tcodex\tacme\n")
        self.crew = self.home / "crew"
        shutil.copytree(ROOT / "crew", self.crew, ignore=shutil.ignore_patterns("local.env", "local"))
        bindir = self.home / "bin"
        bindir.mkdir()
        herdr = bindir / "herdr"
        herdr.write_text('#!' + sys.executable + '\n' + '''import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_CALLS"], "a") as f: f.write(json.dumps(args) + "\\n")
a = {"name": "codex-acme", "pane_id": "ws:p", "agent": "codex", "agent_status": "idle", "cwd": os.environ["FAKE_CWD"]}
if args[:2] == ["workspace", "get"]: out = {"workspace": {"label": "Acme Coordinator"}}
elif args[:2] == ["agent", "list"]: out = {"agents": [a]}
elif args[:2] == ["agent", "get"]: out = {"agent": a}
elif args[:2] == ["tab", "list"]: out = {"tabs": []}
elif args[:2] == ["pane", "current"]: out = {"pane": {}}
else: raise SystemExit("Unexpected herdr operation: " + str(args))
print(json.dumps({"result": out}))
''')
        herdr.chmod(0o755)
        for name in ("curl", "lms", "opencode"):
            path = bindir / name
            path.write_text('#!/bin/sh\necho "unexpected local service" >&2\nexit 91\n')
            path.chmod(0o755)
        self.e = dict(os.environ, HOME=str(self.home), HERDR_ENV="1", HERDR_WORKSPACE_ID="ws",
                      FAKE_CALLS=str(self.home / "calls"), FAKE_CWD=str(self.worker),
                      LLM_PROFILES_DIR=str(self.cfg), PATH=str(bindir) + os.pathsep + os.environ["PATH"])
        for key in ("CREW_PROFILE", "CLAUDECODE", "CREW_QWEN_FORCE"):
            self.e.pop(key, None)

    def run_script(self, name, *args):
        return subprocess.run(["bash", str(self.crew / "scripts" / name), *map(str, args)],
                              env=self.e, cwd=self.project, capture_output=True, text=True, timeout=15)

    def test_codex_only_needs_no_local_model_or_gateway(self):
        self.e.update(CREW_QWEN_MODEL="invalid", CREW_QWEN_CTX="not-an-int")
        r = self.run_script("crew-up.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("already live", r.stdout)
        self.assertNotIn("unexpected local service", r.stderr)
        self.assertFalse((self.home / ".local/share/token-factory/opencode-crew").exists())

    def test_qwen_sizes_files_relative_to_worker(self):
        (self.cfg / "crews.tsv").write_text("acme\tqwen,codex\tacme\n")
        (self.worker / "large.txt").write_text("x" * 70000)
        brief = self.project / "brief.md"
        brief.write_text("Read large.txt and summarize it.\n")
        r = self.run_script("delegate.sh", "qwen", brief)
        self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn("1 files", r.stderr)
        self.assertNotIn('"prompt"', (self.home / "calls").read_text())
        self.assertTrue((self.home / ".local/share/token-factory/profiles/acme").is_dir())

    def lib(self, snippet):
        return subprocess.run(["bash", "-c", '. "$1"; ' + snippet, "-", str(self.crew / "scripts" / "crew-lib.sh")],
                              env=self.e, cwd=self.project, capture_output=True, text=True, timeout=15)

    def test_remote_backend_route_and_tunnel(self):
        bindir = self.home / "bin"
        # curl fails until fake ssh has "opened" the tunnel; ssh records its arguments.
        (bindir / "curl").write_text('#!/bin/sh\n[ -f "$HOME/tunnel" ] || exit 7\necho \'{"data":[]}\'\n')
        (bindir / "ssh").write_text('#!/bin/sh\necho "$@" >> "$HOME/ssh-calls"\n'
                                    'case " $* " in *" -fN "*) touch "$HOME/tunnel";; esac\n')
        for name in ("curl", "ssh"):
            (bindir / name).chmod(0o755)
        for backend, route in ((None, "lmstudio"), ("ollama", "ollama"), ("remote", "lmstudio-remote")):
            env = dict(self.e)
            if backend: env["CREW_QWEN_BACKEND"] = backend
            r = subprocess.run(["bash", "-c", '. "$1"; crew_qwen_route', "-", str(self.crew / "scripts" / "crew-lib.sh")],
                               env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(r.stdout.strip(), route)
        r = self.lib("crew_remote_tunnel")
        self.assertEqual(r.returncode, 1)
        self.assertIn("CREW_LMSTUDIO_SSH not set", r.stderr)
        self.e.update(CREW_LMSTUDIO_SSH="lab-mac", CREW_LMSTUDIO_TUNNEL_PORT="12999")
        r = self.lib("crew_remote_tunnel && crew_remote_tunnel")   # second call reuses the tunnel
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = (self.home / "ssh-calls").read_text().splitlines()
        self.assertEqual(len(calls), 1)
        self.assertIn("-L 127.0.0.1:12999:127.0.0.1:1234 lab-mac", calls[0])
        r = self.lib("crew_remote_lms ps")
        self.assertIn("lab-mac ~/.lmstudio/bin/lms ps", (self.home / "ssh-calls").read_text())

    def test_qwen_line_limit_and_worker_opt_in(self):
        brief = self.project / "brief.md"
        brief.write_text("task\n" * 46)
        r = self.run_script("delegate.sh", "qwen", brief)
        self.assertEqual(r.returncode, 2)
        (self.cfg / "crews.tsv").write_text("acme\tqwen,codex\tacme\n")
        r = self.run_script("delegate.sh", "qwen", brief)
        self.assertEqual(r.returncode, 6, r.stdout + r.stderr)
        self.assertIn("46 lines", r.stderr)
