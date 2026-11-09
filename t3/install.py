#!/usr/bin/env python3
"""Install/update/remove the Paddock skill in an explicitly selected skills directory."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parent
NAME = 'paddock-crew'
FILES = (
    'SKILL.md', 'agents/openai.yaml',
    'references/onboarding.md', 'references/orchestration.md',
    'references/reviews.md', 'references/evidence.md',
    'scripts/paddock.py', 'assets/project/RULES.md',
    'assets/project/project.json', 'assets/project/unittest_receipt.py',
)
MANIFEST = '.paddock-install.json'


def no_links(path):
    p = Path(path).absolute()
    for a in (p, *p.parents):
        if a.is_symlink() or (hasattr(a, 'is_junction') and a.is_junction()):
            raise ValueError('Refusing symlink/junction: ' + str(a))
    return p


def hashes(folder):
    out = {}
    for p in sorted(folder.rglob('*')):
        no_links(p)
        if p.is_file() and p.name != MANIFEST:
            out[p.relative_to(folder).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--skills-dir', required=True, help='Explicit provider skill directory; no auto-discovery')
    parser.add_argument('--apply', action='store_true', help='Write changes; default is preview')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--upgrade', action='store_true')
    mode.add_argument('--uninstall', action='store_true')
    a = parser.parse_args()
    parent = no_links(a.skills_dir)
    target = no_links(parent / NAME)
    action = 'uninstall' if a.uninstall else 'upgrade' if a.upgrade else 'install'
    if target.exists():
        m = target / MANIFEST
        if not m.is_file():
            raise ValueError('Existing unmanaged skill; choose a different directory or reconcile it manually')
        previous = json.loads(m.read_text(encoding='utf-8'))
        if previous.get('files') != hashes(target):
            raise ValueError('Installed skill contains local changes; preserve/reconcile them before upgrade or uninstall')
        if not (a.upgrade or a.uninstall):
            raise ValueError('Already installed; use --upgrade explicitly')
    elif a.uninstall:
        print(json.dumps({'action': action, 'state': 'already_absent', 'path': str(target)}))
        return 0
    source = ROOT / 'skills' / NAME
    payload = {}
    if not a.uninstall:
        for name in FILES:
            p = no_links(source / name)
            payload[name] = p.read_bytes()
    if a.apply:
        parent.mkdir(parents=True, exist_ok=True)
        old = parent / ('.paddock-backup-' + uuid.uuid4().hex)
        stage = parent / ('.paddock-stage-' + uuid.uuid4().hex)
        try:
            if not a.uninstall:
                stage.mkdir()
                for name, content in payload.items():
                    p = stage / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(content)
                (stage / MANIFEST).write_text(json.dumps({'version': (ROOT / 'VERSION').read_text().strip(),
                    'files': hashes(stage)}, indent=2) + '\n', encoding='utf-8')
            if target.exists():
                target.rename(old)
            try:
                if not a.uninstall:
                    stage.rename(target)
            except OSError:
                if old.exists():
                    old.rename(target)
                raise
            if old.exists():
                shutil.rmtree(old)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    print(json.dumps({'action': action, 'applied': a.apply, 'path': str(target),
        'host_registration': 'not_changed', 'credentials': 'not_changed'}, indent=2))
    return 0


if __name__ == '__main__':
    try:
        if sys.version_info < (3, 11):
            raise ValueError('Python 3.11 or newer is required')
        sys.exit(main())
    except (OSError, ValueError, KeyError, TypeError) as e:
        print('paddock install: ' + str(e), file=sys.stderr)
        sys.exit(2)
