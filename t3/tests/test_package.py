"""Portable negative-path tests. No provider calls or paid model work."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'skills/paddock-crew/scripts/paddock.py'
INSTALL = ROOT / 'install.py'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) if not isinstance(value, str) else value, encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crew():
    return {'schema': 1, 'providers': {'codex': {'approved': True, 'instance_id': None, 'model': None}},
            'roles': {r: 'codex' for r in ('coordinator', 'builder', 'reviewer', 'adversary')},
            'local_models': False, 'max_builders': 1, 'max_review_rounds': 2}


class Package(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='paddock test ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.project = self.base / 'new project'
        self.config = self.base / 'crew.json'
        write(self.config, crew())
        self.catalog = self.base / 'catalog.json'
        write(self.catalog, {'providers': [{'providerInstanceId': 'company', 'driverKind': 'codex',
              'canRunChildTask': True, 'models': [{'id': 'test-model'}]}]})

    def call(self, *args, script=CLI, **kw):
        return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True,
                              text=True, timeout=30, **kw)

    def init(self):
        r = self.call('project', self.project, '--crew', self.config, '--new', '--apply')
        self.assertEqual(r.returncode, 0, r.stderr)
        write(self.base / 'request.md', 'Add the requested feature; no deployment.')
        write(self.base / 'contract.md', 'Acceptance: real tests pass; independent reviews.')
        r = self.call('task', '--project', self.project, '--task', 'one',
                      '--request', self.base / 'request.md', '--contract', self.base / 'contract.md')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.rd = self.project / '.paddock/runs/one'
        self.contract_digest = json.loads(r.stdout)['contract_digest']

    def checks(self, checks, mode='tests'):
        write(self.project / '.paddock/project.json', {'schema': 1, 'verification_mode': mode, 'checks': checks})

    def verify(self):
        return self.call('verify', '--project', self.project, '--task', 'one')

    def unittest_check(self, code):
        write(self.project / 'tests/test_example.py', code)
        self.checks([{'id': 'unit', 'kind': 'test', 'argv': ['{python}', '.paddock/unittest_receipt.py', '-s', 'tests'], 'timeout': 5}])

    def test_interview_records_unbound_roles(self):
        r = self.call('interview', '--output', self.base / 'interview.json', '--apply', input='codex,claude\n\nclaude\n\nclaude\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        c = load(self.base / 'interview.json')
        self.assertEqual(c['roles']['adversary'], 'claude')
        self.assertIsNone(c['providers']['claude']['instance_id'])
        self.assertFalse(c['local_models'])

    def test_route_requires_explicit_binding_and_live_provider(self):
        args = ('route', '--crew', self.config, '--catalog', self.catalog, '--role', 'builder')
        self.assertNotEqual(self.call(*args).returncode, 0)
        binding = ('bind', '--crew', self.config, '--provider', 'codex', '--instance', 'company',
                   '--model', 'test-model', '--catalog', self.catalog, '--apply')
        self.assertNotEqual(self.call(*binding).returncode, 0)
        self.assertEqual(self.call(*binding, '--confirm-approved-instance').returncode, 0)
        self.assertEqual(self.call(*args).returncode, 0)
        data = load(self.catalog); data['providers'][0]['canRunChildTask'] = False; write(self.catalog, data)
        self.assertNotEqual(self.call(*args).returncode, 0)

    def test_preview_does_not_create_repo(self):
        self.assertEqual(self.call('project', self.project, '--crew', self.config, '--new').returncode, 0)
        self.assertFalse(self.project.exists())

    def test_adoption_preserves_existing_instructions_and_refuses_overwrite(self):
        self.project.mkdir()
        subprocess.run(['git', 'init', str(self.project)], check=True, capture_output=True)
        write(self.project / 'AGENTS.md', 'Existing project rules.\n')
        write(self.project / '.gitignore', 'existing-build/\n')
        r = self.call('project', self.project, '--crew', self.config, '--apply')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.project / 'AGENTS.md').read_text().startswith('Existing project rules.\n'))
        before = (self.project / 'AGENTS.md').read_bytes()
        self.assertNotEqual(self.call('project', self.project, '--crew', self.config, '--apply').returncode, 0)
        self.assertEqual((self.project / 'AGENTS.md').read_bytes(), before)
        self.assertNotEqual(self.call('doctor', '--project', self.project).returncode, 0)

    def test_install_preview_upgrade_and_uninstall(self):
        dest = self.base / 'skills with spaces'
        r = self.call('--skills-dir', dest, script=INSTALL)
        self.assertEqual(r.returncode, 0, r.stderr); self.assertFalse(dest.exists())
        r = self.call('--skills-dir', dest, '--apply', script=INSTALL)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.call('--skills-dir', dest, '--upgrade', '--apply', script=INSTALL).returncode, 0)
        self.assertEqual(self.call('--skills-dir', dest, '--uninstall', '--apply', script=INSTALL).returncode, 0)
        self.assertFalse((dest / 'paddock-crew').exists())

    def test_installer_refuses_local_changes(self):
        dest = self.base / 'skills'
        self.assertEqual(self.call('--skills-dir', dest, '--apply', script=INSTALL).returncode, 0)
        f = dest / 'paddock-crew/SKILL.md'; f.write_text('Local change')
        for mode in ('--upgrade', '--uninstall'):
            self.assertNotEqual(self.call('--skills-dir', dest, mode, '--apply', script=INSTALL).returncode, 0)
            self.assertEqual(f.read_text(), 'Local change')

    def test_symlink_adoption_refuses_without_writing(self):
        self.project.mkdir()
        subprocess.run(['git', 'init', str(self.project)], check=True, capture_output=True)
        outside = self.base / 'outside'; outside.mkdir()
        try:
            (self.project / '.paddock').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        r = self.call('project', self.project, '--crew', self.config, '--apply')
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_no_checks_is_not_success(self):
        self.init()
        r = self.verify()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('unconfigured', r.stderr)

    def test_actual_unittest_execution(self):
        self.init()
        self.unittest_check('import unittest\nclass Example(unittest.TestCase):\n def test_real(self): self.assertEqual(2+2,4)\n')
        r = self.verify(); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)['checks'][0]['counts']['passed'], 1)

    def test_zero_skipped_failure_and_early_exit_never_succeed(self):
        self.init()
        samples = ('# No tests\n',
            'import unittest\nclass E(unittest.TestCase):\n @unittest.skip("not run")\n def test_a(self): pass\n',
            'import unittest\nclass E(unittest.TestCase):\n def test_a(self): self.fail("real failure")\n',
            'import os\nos._exit(0)\n')
        for code in samples:
            with self.subTest(code=code):
                self.unittest_check(code)
                self.assertNotEqual(self.verify().returncode, 0)

    def test_generic_exit_zero_is_not_test_evidence(self):
        self.init()
        self.checks([{'id': 'fake', 'kind': 'test', 'argv': ['{python}', '-c', 'print("all tests passed")']}])
        r = self.verify(); self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)['checks'][0]['status'], 'incomplete')

    def test_command_only_requires_explicit_mode(self):
        self.init()
        check = [{'id': 'check', 'kind': 'command', 'argv': ['{python}', '-c', 'print("checked")']}]
        self.checks(check); self.assertNotEqual(self.verify().returncode, 0)
        self.checks(check, 'commands')
        r = self.verify(); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)['checks'][0]['status'], 'command_passed')

    def test_source_mutation_invalidates_success(self):
        self.init()
        self.checks([{'id': 'mutates', 'kind': 'command', 'argv': ['{python}', '-c', 'open("source.py","w").write("changed")']}], 'commands')
        r = self.verify(); self.assertNotEqual(r.returncode, 0)
        self.assertFalse(json.loads(r.stdout)['source_unchanged'])

    def test_timeout_stops_descendant_and_does_not_claim_success(self):
        self.init()
        marker = self.rd / 'escaped-marker'
        child = 'import time; from pathlib import Path; time.sleep(3); Path(' + repr(str(marker)) + ').write_text("escaped")'
        code = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); time.sleep(60)'
        self.checks([{'id': 'timeout', 'kind': 'command', 'argv': ['{python}', '-c', code], 'timeout': 0.3}], 'commands')
        r = self.verify(); self.assertNotEqual(r.returncode, 0)
        self.assertEqual(json.loads(r.stdout)['checks'][0]['status'], 'timeout')
        time.sleep(3.2)
        self.assertFalse(marker.exists(), 'Descendant survived timeout cleanup')

    def prepare_packet(self):
        self.init()
        self.unittest_check('import unittest\nclass E(unittest.TestCase):\n def test_a(self): self.assertTrue(True)\n')
        self.assertEqual(self.verify().returncode, 0)
        write(self.rd / 'claims.md', 'One test executed; host enforcement unknown.')
        write(self.rd / 'evidence/builder.json', {'fixture': True, 'session': 'builder'})
        write(self.rd / 'host.json', {'builder_session_ids': ['builder'], 'controls_state': 'unknown',
                                    'receipts': ['evidence/builder.json']})
        r = self.call('packet', '--project', self.project, '--task', 'one')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.packet_info = json.loads(r.stdout)

    def reviews(self):
        for kind in ('instruction', 'code', 'adversary'):
            write(self.rd / ('evidence/' + kind + '.json'), {'fixture': True, 'session': kind})
            write(self.rd / (kind + '-review.json'), {'status': 'pass',
                'input_digest': self.packet_info['contract_digest' if kind == 'instruction' else 'packet_digest'],
                'reviewer_session_id': kind, 'builder_session_ids': ['builder'],
                'receipt': 'evidence/' + kind + '.json', 'coverage': ['fixture coverage'], 'findings': [],
                'limitations': ['Test fixtures are not authentic host receipts']})

    def audit(self):
        return self.call('audit', '--project', self.project, '--task', 'one')

    def test_missing_reviews_fail_and_unknown_controls_remain_unknown(self):
        self.prepare_packet(); self.assertNotEqual(self.audit().returncode, 0)
        self.reviews()
        r = self.audit(); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout)['host_controls'], 'unknown')

    def test_stale_claims_logs_source_and_missing_receipts_fail(self):
        self.prepare_packet(); self.reviews()
        paths = [self.rd / 'claims.md', self.project / 'tests/test_example.py',
                 self.project / load(self.rd / 'verification.json')['checks'][0]['log'], self.rd / 'evidence/adversary.json']
        for path in paths:
            with self.subTest(path=path):
                before = path.read_bytes()
                if path.name == 'adversary.json': path.unlink()
                else: path.write_bytes(before + b' changed')
                self.assertNotEqual(self.audit().returncode, 0)
                path.write_bytes(before)

    def test_builder_or_same_session_cannot_fill_final_review_roles(self):
        self.prepare_packet(); self.reviews()
        path = self.rd / 'adversary-review.json'
        for session in ('builder', 'code'):
            r = load(path); r['reviewer_session_id'] = session; write(path, r)
            self.assertNotEqual(self.audit().returncode, 0)

    def test_changed_contract_invalidates_instruction_review(self):
        self.prepare_packet(); self.reviews()
        write(self.rd / 'contract.md', 'Different requirements')
        self.call('packet', '--project', self.project, '--task', 'one')
        self.assertNotEqual(self.audit().returncode, 0)

    def test_failed_new_attempt_invalidates_old_green_verification(self):
        self.init()
        code = ('import os,json; from pathlib import Path; '
                'Path(os.environ["PADDOCK_CHECK_RECEIPT"]).write_text('
                '\'[]\' if os.environ.get("PADDOCK_BAD_FIXTURE") else '
                'json.dumps({"completed":True,"passed":1,"failed":0,"skipped":0}))')
        self.checks([{'id': 'adapter', 'kind': 'test', 'argv': ['{python}', '-c', code]}])
        self.assertEqual(self.verify().returncode, 0)
        r = self.call('verify', '--project', self.project, '--task', 'one',
                      env=dict(os.environ, PADDOCK_BAD_FIXTURE='1'))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotEqual(load(self.rd / 'verification.json')['status'], 'verified')

    def test_interrupted_attempt_invalidates_old_success_before_waiting(self):
        self.init()
        code = ('import os,json,time; from pathlib import Path; '
                'time.sleep(60 if os.environ.get("PADDOCK_SLEEP_FIXTURE") else 0); '
                'Path(os.environ["PADDOCK_CHECK_RECEIPT"]).write_text('
                'json.dumps({"completed":True,"passed":1,"failed":0,"skipped":0}))')
        self.checks([{'id': 'adapter', 'kind': 'test', 'argv': ['{python}', '-c', code], 'timeout': 0.3}])
        self.assertEqual(self.verify().returncode, 0)
        proc = subprocess.Popen([sys.executable, str(CLI), 'verify', '--project', str(self.project), '--task', 'one'],
            env=dict(os.environ, PADDOCK_SLEEP_FIXTURE='1'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    if load(self.rd / 'verification.json')['status'] == 'running': break
                except (OSError, ValueError): pass
                time.sleep(0.01)
            self.assertEqual(load(self.rd / 'verification.json')['status'], 'running')
            # Let the bounded child timeout cleanly; the running marker was observed.
            proc.wait(timeout=15)
            self.assertNotEqual(load(self.rd / 'verification.json')['status'], 'verified')
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()

    def test_empty_host_receipt_or_claims_are_incomplete(self):
        self.prepare_packet()
        for p in (self.rd / 'claims.md', self.rd / 'evidence/builder.json'):
            old = p.read_bytes(); p.write_bytes(b'')
            self.assertNotEqual(self.call('packet', '--project', self.project, '--task', 'one').returncode, 0)
            p.write_bytes(old)

    def test_windows_anchored_receipt_paths_rejected_on_every_platform(self):
        self.prepare_packet()
        for name in ('\\outside\\receipt.json', 'D:receipt.json', 'C:/outside/receipt.json', 'file:stream'):
            h = load(self.rd / 'host.json'); h['receipts'] = [name]; write(self.rd / 'host.json', h)
            r = self.call('packet', '--project', self.project, '--task', 'one')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('relative in-project path', r.stderr)

    @unittest.skipIf(os.name == 'nt', 'Unix executable mode')
    def test_executable_mode_change_invalidates_source(self):
        self.prepare_packet(); self.reviews()
        self.assertEqual(self.audit().returncode, 0)
        p = self.project / 'tests/test_example.py'
        p.chmod(p.stat().st_mode | 0o111)
        self.assertNotEqual(self.audit().returncode, 0)

    def test_unittest_adapter_imports_real_project_module(self):
        self.init()
        write(self.project / 'report.py', 'def add(a, b): return a + b\n')
        self.unittest_check('import unittest\nfrom report import add\nclass E(unittest.TestCase):\n def test_a(self): self.assertEqual(add(2, 3), 5)\n')
        r = self.verify()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipIf(os.name == 'nt', 'Unix permission bits')
    def test_owner_execute_change_not_hidden_by_other_execute_bit(self):
        self.prepare_packet()
        p = self.project / 'tests/test_example.py'
        p.chmod(0o744)
        self.assertEqual(self.verify().returncode, 0)
        r = self.call('packet', '--project', self.project, '--task', 'one')
        self.packet_info = json.loads(r.stdout)
        self.reviews()
        self.assertEqual(self.audit().returncode, 0)
        p.chmod(0o654)
        self.assertNotEqual(self.audit().returncode, 0)

    @unittest.skipIf(os.name == 'nt', 'Native POSIX SIGINT; Windows timeout tree test is separate')
    def test_interrupt_cleans_up_child_and_never_keeps_green_status(self):
        self.init()
        ready = self.rd / 'ready'
        escaped = self.rd / 'escaped'
        code = ('from pathlib import Path; import time; Path(' + repr(str(ready)) + ').touch(); '
                'time.sleep(1.5); Path(' + repr(str(escaped)) + ').touch()')
        self.checks([{'id': 'interrupt', 'kind': 'command', 'argv': ['{python}', '-c', code]}], 'commands')
        proc = subprocess.Popen([sys.executable, str(CLI), 'verify', '--project', str(self.project), '--task', 'one'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline: time.sleep(0.01)
            self.assertTrue(ready.exists())
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=5)
            time.sleep(1.7)
            self.assertFalse(escaped.exists())
            self.assertNotEqual(load(self.rd / 'verification.json')['status'], 'verified')
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()

    # ---- The CLI proves its own claims: every write is re-read and reported by hash.

    def test_writes_report_hashes_of_what_is_on_disk(self):
        r = self.call('interview', '--output', self.base / 'interview.json', '--apply', input='codex\n\n\n\n\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['written'], {str(self.base / 'interview.json'): sha(self.base / 'interview.json')})
        r = self.call('project', self.project, '--crew', self.config, '--new', '--apply')
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(sorted(out['written']), out['files'])
        for name, digest in out['written'].items():
            self.assertEqual(sha(self.project / name), digest, name)
        write(self.base / 'request.md', 'Request.'); write(self.base / 'contract.md', 'Contract.')
        r = self.call('task', '--project', self.project, '--task', 'one',
                      '--request', self.base / 'request.md', '--contract', self.base / 'contract.md')
        self.assertEqual(r.returncode, 0, r.stderr)
        rd = self.project / '.paddock/runs/one'
        self.assertEqual(json.loads(r.stdout)['written'], {n: sha(rd / n) for n in ('request.md', 'contract.md')})
        self.assertEqual([p.name for p in rd.parent.iterdir()], ['one'])  # no staging leftovers

    def test_preview_reports_nothing_written(self):
        r = self.call('project', self.project, '--crew', self.config, '--new')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)['written'], {})

    @unittest.skipIf(os.name == 'nt' or (hasattr(os, 'geteuid') and os.geteuid() == 0), 'POSIX permissions')
    def test_failed_adoption_restores_every_file(self):
        self.project.mkdir()
        subprocess.run(['git', 'init', str(self.project)], check=True, capture_output=True)
        write(self.project / 'AGENTS.md', 'Existing project rules.\n')
        write(self.project / '.gitignore', 'existing-build/\n')
        before = {n: (self.project / n).read_bytes() for n in ('AGENTS.md', '.gitignore')}
        locked = self.project / '.paddock'; locked.mkdir(); locked.chmod(0o555)
        self.addCleanup(locked.chmod, 0o755)
        r = self.call('project', self.project, '--crew', self.config, '--apply')
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual({n: (self.project / n).read_bytes() for n in before}, before)
        self.assertFalse((self.project / 'CLAUDE.md').exists())
        self.assertEqual(sorted(p.name for p in self.project.iterdir()), ['.git', '.gitignore', '.paddock', 'AGENTS.md'])

    def test_audit_reports_missing_or_corrupt_records_instead_of_crashing(self):
        self.prepare_packet(); self.reviews()
        for name, damage in (('host.json', None), ('packet.json', 'not json'), ('verification.json', '[]'),
                             ('code-review.json', '{"findings": "x", "receipt": "../../escape"}')):
            with self.subTest(name=name):
                path = self.rd / name
                before = path.read_bytes()
                path.unlink() if damage is None else path.write_text(damage)
                r = self.audit()
                self.assertEqual(r.returncode, 1, r.stderr)
                report = json.loads(r.stdout)
                self.assertFalse(report['evidence_complete'])
                self.assertTrue(report['errors'])
                path.write_bytes(before)
        self.assertEqual(self.audit().returncode, 0)

    def test_audit_names_the_digests_it_compared(self):
        self.prepare_packet(); self.reviews()
        r = self.audit()
        self.assertEqual(r.returncode, 0, r.stdout)
        compared = json.loads(r.stdout)['compared']
        self.assertEqual(compared['packet_digest'], sha(self.rd / 'packet.json'))
        self.assertEqual(compared['contract_digest'], self.packet_info['contract_digest'])
        self.assertEqual(compared['source_digest'], load(self.rd / 'packet.json')['source_digest'])

    def test_validation_claims_name_real_tests(self):
        # Each claim in VALIDATION.md names the test that proves it; a renamed or deleted
        # test makes the claim unproven, and this test fails.
        text = (ROOT / 'VALIDATION.md').read_text(encoding='utf-8')
        section = text.split('## Claims and the tests that prove them', 1)[1].split('\n## ', 1)[0]
        named = [n for line in section.splitlines() if line.startswith('|') for n in
                 __import__('re').findall(r'`(test_\w+)`', line)]
        self.assertGreaterEqual(len(named), 10)
        tests = {name for cls in (Package,) for name in dir(cls) if name.startswith('test_')}
        self.assertEqual([n for n in named if n not in tests], [])

    @unittest.skipUnless(os.name == 'nt', 'Native PowerShell entry point')
    def test_powershell_installer(self):
        shell = shutil.which('pwsh') or shutil.which('powershell')
        self.assertIsNotNone(shell)
        r = subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'install.ps1'),
            '--skills-dir', str(self.base / 'powershell skills'), '--apply'], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.base / 'powershell skills/paddock-crew/SKILL.md').exists())


if __name__ == '__main__':
    unittest.main()
