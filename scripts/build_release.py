"""Create a code-only installation ZIP with the usual custom_components layout."""
from pathlib import Path
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED
from check_repository import check, ROOT, PACKAGE

check()
version = json.loads((PACKAGE / 'manifest.json').read_text())['version']
output = ROOT / 'dist'
output.mkdir(exist_ok=True)
archive = output / f'lightshow-studio-{version}.zip'
with ZipFile(archive, 'w', ZIP_DEFLATED) as target:
    for path in sorted(PACKAGE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in {'.py', '.json', '.yaml', '.js', '.png'}:
            target.write(path, path.relative_to(ROOT).as_posix())
    for name in ['README.md', 'LICENSE', 'CHANGELOG.md', 'hacs.json', 'DASHBOARD-KARTE.yaml']:
        target.write(ROOT / name, name)
    for folder in ['docs', 'show_packs']:
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and path.suffix in {'.md', '.png', '.json'}:
                target.write(path, path.relative_to(ROOT).as_posix())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / 'SHA256SUMS').write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
print(archive)
