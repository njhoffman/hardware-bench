"""The Phoronix Test Suite, run in its own state directory with uploads off.

Everything the suite keeps lives under one directory (HB_PTS_HOME, default
~/.local/share/hardware-bench/pts). Its user-config.xml is written before
every call: the suite creates ~/.phoronix-test-suite/ from its defaults
unless the install, cache and results directories are set as well as
PTS_USER_PATH_OVERRIDE, and uploads are made impossible, not just unasked.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
MODULE = HERE / 'hb_percentiles.php'


def default_home():
    base = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return Path(os.environ.get('HB_PTS_HOME') or Path(base) / 'hardware-bench' / 'pts')


def find_binary():
    b = os.environ.get('HB_PTS') or shutil.which('phoronix-test-suite')
    return b if b and os.access(b, os.X_OK) else None


class Suite:
    def __init__(self, home=None, binary=None):
        self.home = Path(home or default_home())
        self.binary = binary or find_binary()

    # --- configuration -------------------------------------------------
    def settings(self):
        h = str(self.home)
        return {
            ('OpenBenchmarking', 'AnonymousUsageReporting'): 'FALSE',
            ('OpenBenchmarking', 'AlwaysUploadSystemLogs'): 'FALSE',
            ('OpenBenchmarking', 'AllowResultUploadsToOpenBenchmarking'): 'FALSE',
            ('Installation', 'EnvironmentDirectory'): h + '/installed-tests/',
            ('Installation', 'CacheDirectory'): h + '/download-cache/',
            ('Testing', 'ResultsDirectory'): h + '/test-results/',
            ('Testing', 'AlwaysUploadResultsToOpenBenchmarking'): 'FALSE',
            ('BatchMode', 'SaveResults'): 'TRUE',
            ('BatchMode', 'OpenBrowser'): 'FALSE',
            ('BatchMode', 'UploadResults'): 'FALSE',
            ('BatchMode', 'PromptForTestIdentifier'): 'FALSE',
            ('BatchMode', 'PromptForTestDescription'): 'FALSE',
            ('BatchMode', 'PromptSaveName'): 'FALSE',
            ('BatchMode', 'RunAllTestCombinations'): 'FALSE',
            ('BatchMode', 'Configured'): 'TRUE',
        }

    def configure(self):
        """Write the settings into user-config.xml, keeping any others; install the module."""
        self.home.mkdir(parents=True, exist_ok=True)
        path = self.home / 'user-config.xml'
        root = ET.parse(path).getroot() if path.exists() else ET.Element('PhoronixTestSuite')
        options = root.find('Options')
        if options is None:
            options = ET.SubElement(root, 'Options')
        for (section, key), value in self.settings().items():
            sec = options.find(section)
            if sec is None:
                sec = ET.SubElement(options, section)
            el = sec.find(key)
            if el is None:
                el = ET.SubElement(sec, key)
            el.text = value
        ET.ElementTree(root).write(path, encoding='unicode', xml_declaration=True)
        (self.home / 'modules').mkdir(exist_ok=True)
        shutil.copyfile(MODULE, self.home / 'modules' / MODULE.name)

    # --- running ---------------------------------------------------------
    def call(self, args, **kw):
        """Run the suite; remember if it created ~/.phoronix-test-suite despite the config."""
        stray = Path(os.path.expanduser('~/.phoronix-test-suite'))
        existed = stray.exists()
        try:
            return subprocess.run([self.binary, *args], check=False, **kw)
        finally:
            if not existed and stray.exists():
                self.stray = stray

    stray = None

    def env(self, **extra):
        env = dict(os.environ, PTS_USER_PATH_OVERRIDE=str(self.home) + '/')
        env.update({k: str(v) for k, v in extra.items() if v is not None})
        return env

    def results_dir(self, name):
        return self.home / 'test-results' / name

    def benchmark(self, tests, times, name, identifier):
        """Install (when missing) and run tests into result file name; True when it was saved.

        The suite's exit status is not used: it exits 2 after a successful run
        when a background helper it tries to kill has already finished.
        """
        presets = ';'.join(p for p in (t.preset() for t in tests) if p)
        env = self.env(PRESET_OPTIONS=presets or None, FORCE_TIMES_TO_RUN=times,
                       TEST_RESULTS_NAME=name, TEST_RESULTS_IDENTIFIER=identifier)
        self.call(['batch-benchmark', *[t.test for t in tests]], env=env)
        return (self.results_dir(name) / 'composite.xml').exists()

    def percentiles(self, name, offline=False):
        """The module's JSON for result file name."""
        env = self.env(HB_OFFLINE='1' if offline else '0')
        out = self.call(['hb_percentiles.json', name], env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout
        for line in out.splitlines():
            if line.startswith('{'):
                return json.loads(line)
        raise RuntimeError(f'no percentile data for {name}')

    def system(self, name):
        """Hardware and software lines the suite recorded with the result."""
        info = {}
        try:
            root = ET.parse(self.results_dir(name) / 'composite.xml').getroot()
        except (OSError, ET.ParseError):
            return info
        for tag in ('Hardware', 'Software'):
            text = root.findtext(f'System/{tag}') or ''
            for part in text.split(', '):
                key, sep, value = part.partition(': ')
                if sep and key in ('Processor', 'Motherboard', 'Memory', 'Disk', 'Graphics', 'OS', 'Kernel'):
                    info[key] = value.strip()
        return info

    def version(self):
        out = self.call(['version'], env=self.env(),
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout
        for word in out.split():
            if word[:1] == 'v' and word[1:2].isdigit():
                return word[1:]
        return None
