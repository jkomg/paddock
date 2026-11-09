"""Native-platform installer tests: run on Windows as well as macOS/Linux."""
import json
import os
import shlex
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1]


class PortableInstall(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paddock install ")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"
        self.home.mkdir()
        self.cfg = self.home / "paddock"
        self.cfg.mkdir()
        for name in ("llm_profile.py", "install.py", "llm-profile.zsh"):
            shutil.copy2(SRC / name, self.cfg / name)
        (self.cfg / "profiles.tsv").write_text(
            "acme\t@acme.example\t~/.claude-acme\t~/.codex\n", encoding="utf-8-sig")
        (self.cfg / "folders.tsv").write_text(
            "~/Projects/acme\tacme\tacme\n", encoding="utf-8")
        self.e = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home),
                      LLM_PROFILES_DIR=str(self.cfg), LLM_PROFILES_T3_DIR=str(self.home / ".t3"))
        for key in ("CLAUDE_CONFIG_DIR", "LLM_PROFILES_EXTRA_CLAUDE_DIRS"):
            self.e.pop(key, None)
        self.settings = self.home / ".claude-acme" / "settings.json"

    def install(self, *args):
        return subprocess.run([sys.executable, "-I", str(self.cfg / "install.py"), *args],
                              env=self.e, capture_output=True, text=True, timeout=15)

    def test_fresh_hooks_install_and_real_hook_invocation(self):
        r = self.install("--shell", "none")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.home / ".zshrc").exists())
        data = json.loads(self.settings.read_text())
        command = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        auth = self.settings.parent / ".claude.json"
        auth.write_text(json.dumps({"oauthAccount": {"emailAddress": "wrong@other.example"}}))
        # Execute exactly the installed command, including quoting and paths with spaces.
        r = subprocess.run(command, shell=True, env=dict(self.e, CLAUDE_CONFIG_DIR=str(auth.parent)),
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read",
                           "cwd": str(self.home / "Projects" / "acme"), "tool_input": {}}),
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(self.install("--shell", "none", "--uninstall").returncode, 0)
        self.assertEqual(json.loads(self.settings.read_text()), {})

    @unittest.skipUnless(os.name != "nt" and shutil.which("zsh"), "requires native zsh")
    def test_missing_zshrc_and_idempotence(self):
        self.assertEqual(self.install().returncode, 0)
        rc = self.home / ".zshrc"
        first = rc.read_text()
        self.assertIn("# llm-profiles", first)
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(rc.read_text(), first)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertNotIn("# llm-profiles", rc.read_text())

    def test_uninstall_preserves_other_hooks_and_backup(self):
        self.settings.parent.mkdir()
        original = {"theme": "dark", "hooks": {"PreToolUse": [{"matcher": "Read", "hooks": [
            {"type": "command", "command": "python3 -I $HOME/.config/llm-profiles/llm_profile.py hook"},
            {"type": "command", "command": "echo keep-me"}]}]}}
        self.settings.write_text(json.dumps(original))
        for _ in range(2):
            r = self.install("--shell", "none")
            self.assertEqual(r.returncode, 0, r.stderr)
        backup = Path(str(self.settings) + ".llm-profiles-bak")
        self.assertEqual(json.loads(backup.read_text()), original)
        self.assertEqual(self.install("--shell", "none", "--uninstall").returncode, 0)
        kept = json.loads(self.settings.read_text())
        self.assertEqual(kept["theme"], "dark")
        self.assertEqual(kept["hooks"]["PreToolUse"][0]["hooks"],
                         [{"type": "command", "command": "echo keep-me"}])

    @unittest.skipIf(os.name == "nt", "POSIX interpreter naming")
    def test_hook_survives_python_upgrades(self):
        # A versioned interpreter path vanishes on upgrade, and a hook that cannot start is a
        # non-blocking error in Claude Code: the guard would be silently off.
        self.assertEqual(self.install("--shell", "none").returncode, 0)
        command = json.loads(self.settings.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertTrue(command.startswith("python3 -I "), command)
        self.assertNotIn(sys.executable, command)

    def test_stale_interpreter_is_reported_and_replaced(self):
        self.settings.parent.mkdir()
        parts = ["/gone/python3.9", "-I", str(self.cfg / "llm_profile.py"), "hook"]
        stale = subprocess.list2cmdline(parts) if os.name == "nt" else shlex.join(parts)
        self.settings.write_text(json.dumps({"hooks": {ev: [{"hooks": [{"type": "command", "command": stale}]}]
                                                       for ev in ("SessionStart", "PreToolUse")}}))
        probe = ("import sys; sys.path.insert(0, sys.argv[1]); import llm_profile as lp; "
                 "print(lp.hook_installed(sys.argv[2]))")
        check = lambda: subprocess.run([sys.executable, "-I", "-c", probe, str(self.cfg), str(self.settings.parent)],
                                       env=self.e, capture_output=True, text=True, timeout=15).stdout.strip()
        self.assertEqual(check(), "False")
        self.assertEqual(self.install("--shell", "none").returncode, 0)
        hooks = json.loads(self.settings.read_text())["hooks"]
        commands = [h["command"] for ev in hooks.values() for e in ev for h in e["hooks"]]
        self.assertNotIn(stale, commands)
        self.assertEqual(len(commands), 2)
        self.assertEqual(check(), "True")

    def test_hook_recognised_with_either_quoting(self):
        probe = ("import sys; sys.path.insert(0, sys.argv[1]); import llm_profile as lp; "
                 "print(lp.hook_command_parts(sys.argv[2]) is not None)")
        for quote in ("'", '"'):
            with self.subTest(quote=quote):
                command = f"python3 -I {quote}{self.cfg / 'llm_profile.py'}{quote} hook"
                r = subprocess.run([sys.executable, "-I", "-c", probe, str(self.cfg), command],
                                   env=self.e, capture_output=True, text=True, timeout=15)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(r.stdout.strip(), "True", command)

    @unittest.skipUnless(os.name != "nt" and shutil.which("zsh"), "requires native zsh")
    def test_hook_and_shell_name_the_stable_link(self):
        # Through ~/.config/llm-profiles, moving the checkout needs only the link updated;
        # a checkout path baked into the hook would leave the guard silently off.
        link = self.home / ".config" / "llm-profiles"
        link.parent.mkdir()
        link.symlink_to(self.cfg, target_is_directory=True)
        r = subprocess.run([sys.executable, "-I", str(link / "install.py")], env=self.e,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        command = json.loads(self.settings.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertIn(str(link / "llm_profile.py"), command)
        self.assertIn(str(link / "llm-profile.zsh"), (self.home / ".zshrc").read_text())
        moved = self.home / "moved"
        self.cfg.rename(moved)
        link.unlink(); link.symlink_to(moved, target_is_directory=True)
        # A real setup does not set LLM_PROFILES_DIR: config is found beside the linked script.
        env = {k: v for k, v in self.e.items() if k != "LLM_PROFILES_DIR"}
        r = subprocess.run(command, shell=True, env=env, capture_output=True, text=True, timeout=15,
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read",
                                             "cwd": str(self.home / "Projects" / "acme"), "tool_input": {}}))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    @unittest.skipUnless(os.name != "nt" and shutil.which("zsh"), "requires native zsh")
    def test_moved_checkout_does_not_break_shells(self):
        self.assertEqual(self.install().returncode, 0)
        (self.cfg / "llm-profile.zsh").unlink()
        r = subprocess.run(["zsh", "-c", "source ~/.zshrc; echo alive"], env=self.e,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual((r.returncode, r.stdout.strip(), r.stderr), (0, "alive", ""))

    def test_invalid_settings_do_not_partially_install(self):
        self.settings.parent.mkdir()
        self.settings.write_text("invalid JSON")
        r = self.install("--shell", "none")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.settings.read_text(), "invalid JSON")
        self.assertFalse(Path(str(self.settings) + ".llm-profiles-bak").exists())

    def test_bad_arguments_do_not_uninstall(self):
        self.assertEqual(self.install("--shell", "none").returncode, 0)
        original = self.settings.read_bytes()
        self.assertNotEqual(self.install("--uninstal").returncode, 0)
        self.assertEqual(self.settings.read_bytes(), original)

    @unittest.skipUnless(os.name == "nt", "Windows path semantics")
    def test_windows_case_and_drive_root_rules(self):
        (self.cfg / "folders.tsv").write_text(
            str(self.home / "Projects" / "acme").upper() + "\tacme\tacme\n")
        r = subprocess.run([sys.executable, str(self.cfg / "llm_profile.py"), "resolve", "claude",
                            str(self.home / "Projects" / "acme")], env=self.e,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(".claude-acme", r.stdout)
