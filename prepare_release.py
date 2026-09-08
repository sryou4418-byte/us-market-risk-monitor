"""Build a reproducible source-file manifest and a ZIP without runtime caches."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
EXCLUDED = {'.git', '.venv', '__pycache__', '.pytest_cache', 'node_modules'}


def release_files():
    return sorted(p for p in ROOT.rglob('*') if p.is_file()
                  and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
                  and p.suffix not in ('.pyc', '.pyo', '.zip')
                  and p.name not in ('SHA256SUMS.json', '.env', 'secrets.toml'))


def main():
    files = release_files()
    checksums = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest = ROOT / 'SHA256SUMS.json'
    manifest.write_text(json.dumps(checksums, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    target = ROOT.parent / '미국_증시_종합위험지수_v3.50.0.zip'
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files + [manifest]:
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name, sha in checksums.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == sha, name
    print(json.dumps({'zip': str(target), 'files': len(files) + 1,
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
