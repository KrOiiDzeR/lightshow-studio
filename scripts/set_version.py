"""Set a release version; never changes persisted Home Assistant settings."""
from pathlib import Path
import argparse
import json
import re

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('version')
args = parser.parse_args()
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-(?:beta|rc)\.[1-9]\d*)?', args.version):
    parser.error('Use e.g. 2.0.0-beta.3 or 2.0.0 (without v)')
path = root / 'custom_components/lightshow_studio/manifest.json'
manifest = json.loads(path.read_text())
manifest['version'] = args.version
path.write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
constants = root / 'custom_components/lightshow_studio/const.py'
constants.write_text(re.sub(r'VERSION = "[^"]+"', 'VERSION = "'+args.version+'"', constants.read_text(encoding='utf-8')), encoding='utf-8')
path = root / 'README.md'
path.write_text(re.sub(r'lightshow-studio\.js\?v=[0-9A-Za-z.-]+', 'lightshow-studio.js?v='+args.version, path.read_text(encoding='utf-8')), encoding='utf-8')
changelog = (root / 'CHANGELOG.md').read_text(encoding='utf-8')
if f'## {args.version}' not in changelog:
    raise SystemExit('Add release notes for this version to CHANGELOG.md first')
print(args.version)
