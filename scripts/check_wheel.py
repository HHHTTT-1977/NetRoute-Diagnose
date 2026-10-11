"""Install the final wheel in a clean venv and exercise the README from an empty cwd."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

if len(sys.argv) > 1:
    wheel = Path(sys.argv[1]).resolve()
else:
    wheels = list(Path("dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected exactly one final wheel in dist/")
    wheel = wheels[0].resolve()
repo = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    venv.EnvBuilder(with_pip=True).create(root / 'venv')
    bindir = root / 'venv' / ('Scripts' if os.name == 'nt' else 'bin')
    python = bindir / ('python.exe' if os.name == 'nt' else 'python')
    cli = bindir / ('netroute-diagnose.exe' if os.name == 'nt' else 'netroute-diagnose')
    cwd = root / 'empty'
    cwd.mkdir()
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    def run(*args):
        subprocess.run([str(x) for x in args], cwd=cwd, env=env, check=True, timeout=180)
    run(python, '-m', 'pip', 'install', '--disable-pip-version-check', wheel)
    run(python, '-m', 'pip', 'check')
    run(python, '-c', 'import netroute_diagnose,sys; from pathlib import Path; '
        'assert Path(netroute_diagnose.__file__).is_relative_to(Path(sys.prefix))')
    # This exact single-line command appears in all three READMEs.
    command = 'netroute-diagnose --demo --output demo.html'
    for name in ('README.md', 'README.zh-CN.md', 'README.en.md'):
        assert command in (repo / name).read_text(encoding='utf-8'), name
    run(cli, '--demo', '--output', 'demo.html')
    assert '<!doctype html>' in (cwd / 'demo.html').read_text(encoding='utf-8')
    run(cli, '--demo', '--output', 'json-demo.html', '--json-output', 'demo.json')
    data = json.loads((cwd / 'demo.json').read_text(encoding='utf-8'))
    assert data['offline'] and len(data['domain_checks']) == 10
    assert not data['dns_results'] and not data['egress_results']
    assert {x['status'] for x in data['domain_checks']} == {'PASS', 'UNCERTAIN'}
    # Test discovery stays outside the checkout cwd; imports come from this wheel.
    run(python, '-m', 'unittest', 'discover', '-s', repo / 'tests', '-v')
    print('Final-wheel empty-directory README smoke: PASS')
