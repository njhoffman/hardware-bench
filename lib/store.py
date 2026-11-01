"""Run records: one JSON file per host and run, and the notes file their summary goes into.

Results: HB_RESULTS, default $XDG_DATA_HOME/hardware-bench/results, laid out
as <host>/<YYYY-MM-DD-HHMM>.json. Notes: HB_NOTES, default
$XDG_DATA_HOME/hardware-bench/hardware.md. Point both into a repo to keep the
runs under version control.
"""
import json
import os
from pathlib import Path
import socket



def _data():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return Path(base) / 'hardware-bench'


def results_root():
    return Path(os.environ.get('HB_RESULTS') or _data() / 'results')


def notes_file():
    return Path(os.environ.get('HB_NOTES') or _data() / 'hardware.md')


def hostname():
    return os.environ.get('HB_HOST') or socket.gethostname().split('.')[0]


def save(record, root=None):
    root = Path(root or results_root())
    d = root / record['host']
    d.mkdir(parents=True, exist_ok=True)
    path = d / (record['started'][:16].replace('T', '-').replace(':', '') + '.json')
    path.write_text(json.dumps(record, indent=1) + '\n')
    return path


def runs(host, root=None):
    d = Path(root or results_root()) / host
    return sorted(d.glob('*.json')) if d.is_dir() else []


def load(path):
    return json.loads(Path(path).read_text())


def latest(host, root=None, complete=False):
    """The newest run; with complete, the newest quick or full run (else the newest)."""
    recs = [load(p) for p in reversed(runs(host, root))]
    if complete:
        recs = [r for r in recs if r.get('set') != 'only'] or recs
    return recs[0] if recs else None


def hosts(root=None):
    root = Path(root or results_root())
    return sorted(p.name for p in root.iterdir() if p.is_dir() and any(p.glob('*.json'))) if root.is_dir() else []
