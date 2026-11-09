#!/usr/bin/env python3
"""Build deterministic distribution ZIPs from an explicit file allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 't3'
SKILL_FILES = runpy.run_path(str(SOURCE / 'install.py'))['FILES']
BASE_FILES = ('VERSION', 'NOTICE.txt', 'QUICKSTART.md', 'VALIDATION.md', 'install.py', 'install.ps1', 'install.sh',
              'tests/test_package.py', 'workflow.png', 'workflow.svg')


def build(output):
    version = (SOURCE / 'VERSION').read_text().strip()
    output.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for kind in ('installer', 'skill'):
        names = list(BASE_FILES) if kind == 'installer' else ['NOTICE.txt', 'VERSION']
        names += ['skills/paddock-crew/' + f for f in SKILL_FILES]
        entries = {}
        for name in names:
            p = SOURCE / name
            if p.is_symlink() or any(x.is_symlink() for x in p.parents if x != ROOT.parent):
                raise ValueError('Symlink in release allowlist: ' + name)
            content = p.read_bytes()
            dest = name if kind == 'installer' else name.removeprefix('skills/')
            entries[dest] = content
        manifest = {'version': version, 'distribution': 'public-preview',
                    'files': {p: hashlib.sha256(b).hexdigest() for p, b in sorted(entries.items())}}
        entries['MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
        path = output / f'paddock-t3-{kind}-{version}.zip'
        prefix = f'paddock-t3-{version}/' if kind == 'installer' else ''
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, content in sorted(entries.items()):
                info = zipfile.ZipInfo(prefix + name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100755 if name.endswith('.sh') else 0o100644) << 16
                z.writestr(info, content)
        artifacts.append(path)
    checksums = '\n'.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name for p in artifacts) + '\n'
    (output / 'SHA256SUMS').write_text(checksums)
    return artifacts


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=ROOT / 'dist')
    for path in build(p.parse_args().output):
        print(path)
