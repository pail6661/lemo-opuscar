"""Fetch verified upstream asset packs without a POSIX shell.

python tools/fetch_assets.py voice | hdri | instruments <library|all>
The same release manifest and hashes as tools/fetch.sh are used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def digest(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(name, manifest):
    pack = manifest['packs'][name]
    cache = ROOT / '.release'
    cache.mkdir(exist_ok=True)
    marker = cache / (name + '.installed.json')
    if marker.exists():
        saved = json.loads(marker.read_text(encoding='utf-8'))
        if saved.get('sha256') == pack['sha256'] and all((ROOT / p).is_file() for p in saved.get('files', [])) and saved.get('files'):
            print(f'{name}: already installed')
            return
    filename = pack['file']
    if Path(filename).name != filename:
        raise ValueError('The manifest contains an invalid archive name')
    archive = cache / (filename + '.download')
    size = pack['size']
    have = archive.stat().st_size if archive.exists() else 0
    if have > size:
        archive.unlink()
        have = 0
    need = int(size * 2.2) - have
    if shutil.disk_usage(ROOT).free < need:
        raise OSError(f'{name} needs approximately {need / 1e9:.1f} GB free')
    if have < size:
        url = f'https://github.com/{manifest["repo"]}/releases/download/{manifest["tag"]}/{filename}'
        print(f'{name}: downloading {size / 1e6:.0f} MB', flush=True)
        curl = shutil.which('curl.exe') or shutil.which('curl')
        if curl:
            subprocess.run([curl, '-sS', '-L', '--fail', '--retry', '3', '--connect-timeout', '20',
                            '-C', '-', '-o', str(archive), url], check=True)
        else:
            request = urllib.request.Request(url, headers={'Range': f'bytes={have}-'} if have else {})
            with urllib.request.urlopen(request, timeout=60) as response:
                append = have and response.status == 206
                with archive.open('ab' if append else 'wb') as output:
                    shutil.copyfileobj(response, output)
    if archive.stat().st_size != size or digest(archive) != pack['sha256']:
        archive.unlink()
        raise ValueError(f'{name}: size or SHA-256 mismatch; refresh the manifest before retrying')
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        # Validate every entry before extraction (Python 3.11+). No links or devices.
        for member in members:
            target = (ROOT / member.name).resolve()
            if not target.is_relative_to(ROOT) or member.issym() or member.islnk() or member.isdev():
                raise ValueError(f'Unsafe archive entry: {member.name}')
        if hasattr(tarfile, 'data_filter'):
            bundle.extractall(ROOT, filter='data')
        else:
            bundle.extractall(ROOT)
        files = [member.name for member in members if member.isfile()]
    marker.write_text(json.dumps({'sha256': pack['sha256'], 'files': files}, indent=2), encoding='utf-8')
    archive.unlink()
    print(f'{name}: SHA-256 verified; {len(files)} files installed')


def main():
    manifest = json.loads((ROOT / 'tools/assets.json').read_text(encoding='utf-8'))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pack', choices=['voice', 'hdri', 'instruments'] + list(manifest['packs']))
    parser.add_argument('library', nargs='?')
    args = parser.parse_args()
    names = [args.pack]
    if args.pack == 'instruments':
        if args.library == 'all':
            names = [name for name in manifest['packs'] if name.startswith('instruments-')]
        else:
            names = ['instruments-' + (args.library or '')]
    if any(name not in manifest['packs'] for name in names):
        parser.error('Unknown instrument library; see tools/assets.json')
    for name in names:
        fetch(name, manifest)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError, tarfile.TarError) as error:
        sys.exit(f'fetch_assets.py: {error}')
