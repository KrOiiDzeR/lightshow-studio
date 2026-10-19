"""Offline release checks; no Home Assistant installation is needed."""
from pathlib import Path
import ast
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'custom_components/lightshow_studio'


def check():
    manifest = json.loads((PACKAGE / 'manifest.json').read_text())
    assert manifest['domain'] == 'lightshow_studio'
    assert manifest['codeowners'] == ['@KrOiiDzeR']
    assert re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:beta|rc)\.[1-9]\d*)?', manifest['version'])
    assert manifest['documentation'] == 'https://github.com/KrOiiDzeR/lightshow-studio'
    assert manifest['issue_tracker'] == manifest['documentation'] + '/issues'
    assert manifest['config_flow'] is True
    assert (PACKAGE / 'config_flow.py').is_file()
    assert f'VERSION = "{manifest["version"]}"' in (PACKAGE / 'const.py').read_text(encoding='utf-8')
    assert f"const LS_BUILD = '{manifest['version']}';" in (PACKAGE / 'static/lightshow-studio.js').read_text(encoding='utf-8')
    for language in ('de', 'en'):
        assert (PACKAGE / 'translations' / f'{language}.json').is_file()
    assert [p.name for p in (ROOT / 'custom_components').iterdir() if p.is_dir()] == ['lightshow_studio']
    assert json.loads((ROOT / 'hacs.json').read_text())['name'] == 'Lightshow Studio'
    assert (PACKAGE / 'brand/icon.png').is_file()
    assert (ROOT / 'LICENSE').is_file()
    for path in ROOT.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for path in ROOT.rglob('*.json'):
        json.loads(path.read_text(encoding='utf-8'))
    # Guard against accidentally packaging local HA data or common credentials.
    denied = {'secrets.yaml', 'configuration.yaml', 'customize.yaml', '.env'}
    patterns = [r'gh[pousr]_[A-Za-z0-9]{20,}', r'github_pat_[A-Za-z0-9_]{20,}',
                r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                r'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',
                r'0x[0-9a-fA-F]{16}(?![0-9a-fA-F])']
    for path in ROOT.rglob('*'):
        if not path.is_file() or any(p in {'.git', '__pycache__', 'dist', 'node_modules'} for p in path.relative_to(ROOT).parts):
            continue
        assert path.name not in denied and '.storage' not in path.parts, f'Private file: {path}'
        if path.suffix in {'.png', '.zip'}:
            continue
        text = path.read_text(encoding='utf-8')
        for pattern in patterns:
            assert not re.search(pattern, text), f'Potential private data: {path.name}'
    print('PASS: structure, metadata, syntax, JSON and private-data guards')


if __name__ == '__main__':
    check()
