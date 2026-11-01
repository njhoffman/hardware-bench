"""PassMark PerformanceTest (pt; README: Requirements): CPU Mark and Memory Mark.

pt runs `sudo dmidecode -t 17` itself, so it needs a terminal for the sudo
prompt; without one it is skipped. It can submit results to PassMark over
libcurl, so it runs with every proxy variable pointed at a closed local port:
nothing it sends can leave the machine. Results come from the results_all.yml
it writes into its working directory.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import yaml

NO_NETWORK = 'http://127.0.0.1:9'
KEYS = {
    'SUMM_CPU': 'cpu_mark', 'SUMM_ME': 'memory_mark', 'CPU_SINGLETHREAD': 'single_thread',
    'CPU_INTEGER_MATH': 'integer_math', 'CPU_FLOATINGPOINT_MATH': 'floating_point',
    'CPU_COMPRESSION': 'compression', 'CPU_ENCRYPTION': 'encryption',
    'ME_READ_S': 'memory_read_cached', 'ME_LATENCY': 'memory_latency', 'ME_THREADED': 'memory_threaded',
}


def find_binary():
    b = os.environ.get('HB_PT') or shutil.which('pt')
    return b if b and os.access(b, os.X_OK) else None


def offline_env():
    env = dict(os.environ)
    for k in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy'):
        env[k] = NO_NETWORK
    env.pop('no_proxy', None)
    env.pop('NO_PROXY', None)
    return env


def parse(text):
    """The KEYS values found anywhere in a results YAML document."""
    out = {}

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in KEYS and isinstance(v, (int, float)):
                    out[KEYS[k]] = float(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(yaml.safe_load(text))
    return out


def run(binary):
    """Run CPU + memory suites (autorun 3); the parsed marks, or None."""
    with tempfile.TemporaryDirectory(prefix='hardware-bench-pt.') as d:
        subprocess.run([binary, '-r', '3'], cwd=d, env=offline_env(), check=False)
        f = Path(d) / 'results_all.yml'
        if not f.exists():
            return None
        marks = parse(f.read_text(errors='replace'))
        return marks or None
