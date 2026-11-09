#!/usr/bin/env python3
"""Validate archive inventories/checksums, optionally test the extracted installer."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
import tempfile
import zipfile


def check(path, test=False):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(set(names)) != len(names):
            raise ValueError('Duplicate ZIP paths')
        for name in names:
            p = PurePosixPath(name)
            if p.is_absolute() or PureWindowsPath(name).anchor or '..' in p.parts or ':' in name or '\\' in name:
                raise ValueError('Unsafe ZIP path: ' + name)
            if (z.getinfo(name).external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP must not contain symlinks')
        manifests = [n for n in names if PurePosixPath(n).name == 'MANIFEST.json']
        if len(manifests) != 1:
            raise ValueError('Expected one manifest')
        manifest_path = manifests[0]
        prefix = manifest_path.removesuffix('MANIFEST.json')
        m = json.loads(z.read(manifest_path))
        expected = {prefix + n for n in m['files']} | {manifest_path}
        if set(names) != expected:
            raise ValueError('Archive inventory differs from manifest')
        for name, expected_hash in m['files'].items():
            raw = z.read(prefix + name)
            if hashlib.sha256(raw).hexdigest() != expected_hash:
                raise ValueError('Checksum mismatch: ' + name)
            if name.endswith(('.py', '.md', '.json', '.yaml', '.txt')) and b'/Users/jkennedy' in raw:
                raise ValueError('Machine-specific path leaked: ' + name)
        print(f'{path.name}: {len(m["files"])} payload files verified', flush=True)
        if test and prefix + 'install.py' in names:
            with tempfile.TemporaryDirectory(prefix='paddock extracted ') as temp:
                dest = Path(temp).resolve()
                z.extractall(dest)
                bundle = dest / prefix
                subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(bundle / 'tests'), '-v'], check=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('archives', nargs='+', type=Path)
    p.add_argument('--test', action='store_true')
    a = p.parse_args()
    for archive in a.archives:
        check(archive, a.test)
