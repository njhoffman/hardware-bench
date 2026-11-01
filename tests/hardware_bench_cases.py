"""hardware-bench: percentiles, test sets, suite config, conditions, pt parsing, rendering, and a run against a stub suite."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
import conditions  # noqa: E402
import percentile as pc  # noqa: E402
import pt  # noqa: E402
import pts  # noqa: E402
import render  # noqa: E402
import sets  # noqa: E402
import store  # noqa: E402

CUTS = [float(i * 10) for i in range(100)]  # cut i = 10 * i

# Stub suite: batch-benchmark writes a result file and logs its env;
# hb_percentiles.json prints module JSON for the tests of that run.
STUB = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    home = os.environ['PTS_USER_PATH_OVERRIDE']
    log = os.path.join(home, 'calls.log')
    cmd = sys.argv[1]
    with open(log, 'a') as f:
        f.write(json.dumps({'argv': sys.argv[1:], 'preset': os.environ.get('PRESET_OPTIONS'),
                            'times': os.environ.get('FORCE_TIMES_TO_RUN'), 'name': os.environ.get('TEST_RESULTS_NAME'),
                            'offline': os.environ.get('HB_OFFLINE')}) + '\\n')
    if cmd == 'version':
        print('Phoronix Test Suite v10.8.4')
    elif cmd == 'batch-benchmark':
        if os.environ.get('STUB_STRAY'):
            os.makedirs(os.path.expanduser('~/.phoronix-test-suite'), exist_ok=True)
        d = os.path.join(home, 'test-results', os.environ['TEST_RESULTS_NAME'])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'tests'), 'w').write(' '.join(sys.argv[2:]))
        open(os.path.join(d, 'composite.xml'), 'w').write(
            '<PhoronixTestSuite><System><Hardware>Processor: Test CPU (4 Cores), Memory: 16GB, Graphics: Test GPU'
            '</Hardware><Software>OS: Ubuntu 25.10, Kernel: 6.17</Software></System></PhoronixTestSuite>')
        sys.exit(2)  # the real suite exits 2 after a good run
    elif cmd == 'hb_percentiles.json':
        tests = open(os.path.join(home, 'test-results', sys.argv[2], 'tests')).read().split()
        cuts = [i * 10 for i in range(100)]
        res = []
        for t in tests:
            if t == 'pts/fio':
                res.append({'test': t, 'version': '2.2.0', 'unit': 'MB/s', 'hib': True, 'value': 900.0,
                            'source': 'openbenchmarking.org', 'ae': {'percentiles': cuts, 'samples': 40}})
                res.append({'test': t, 'version': '2.2.0', 'unit': 'IOPS', 'hib': True, 'value': 505.0,
                            'source': 'openbenchmarking.org', 'ae': {'percentiles': cuts, 'samples': 40}})
            elif t == 'pts/pybench':
                res.append({'test': t, 'version': '1.1.3', 'unit': 'Milliseconds', 'hib': False, 'value': 250.0,
                            'source': 'bundled', 'ae': {'percentiles': cuts, 'samples': 6362, 'last_appeared': 1644624000}})
            else:
                res.append({'test': t, 'version': '1.0', 'unit': 'Points', 'hib': True, 'value': 755.0,
                            'source': 'openbenchmarking.org', 'ae': {'percentiles': cuts, 'samples': 7108}})
        print('PHP noise')
        print(json.dumps({'system_type': 'D', 'retrieved': 1793000000, 'results': res}))
    ''')


class Percentiles(unittest.TestCase):
    def test_higher_is_better_follows_the_suite(self):
        self.assertEqual(pc.rank(505, CUTS, True), 50)    # first cut above is 51 -> 50
        self.assertEqual(pc.rank(5, CUTS, True), 0)
        self.assertEqual(pc.rank(10_000, CUTS, True), 99)

    def test_lower_is_better(self):
        self.assertEqual(pc.rank(250, CUTS, False), 74)   # first cut above is 26 -> 100 - 26
        self.assertEqual(pc.rank(-1, CUTS, False), 100)
        self.assertEqual(pc.rank(10_000, CUTS, False), 0)

    def test_missing_data(self):
        self.assertIsNone(pc.rank(5, [], True))
        self.assertIsNone(pc.rank(None, CUTS, True))

    def test_cut_points_from_dict_keyed_by_index(self):
        self.assertEqual(pc.cut_points({'1': 2, '0': 1, '10': 3}), [1.0, 2.0, 3.0])

    def test_ordinal_and_summary(self):
        self.assertEqual([pc.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 99, None)],
                         ['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '99th', '-'])
        s = pc.summarize([{'component': 'cpu', 'percentile': 20}, {'component': 'cpu', 'percentile': 40},
                          {'component': 'disk', 'percentile': 90}, {'component': 'gpu', 'percentile': None}])
        self.assertEqual(s, {'cpu': 30, 'disk': 90, 'overall': 60})


class Sets(unittest.TestCase):
    def test_quick_full_and_gpu(self):
        quick = {t.key for t in sets.select()}
        self.assertEqual(quick, {'coremark', 'pybench', 'stream-copy', 'gputest-plot3d', 'fio-randread'})
        self.assertEqual(len(sets.select(full=True)), len(sets.TESTS))
        self.assertFalse(any(t.needs_display for t in sets.select(full=True, gpu=False)))
        self.assertEqual([t.key for t in sets.select(only=['c-ray', 'gputest-plot3d'], gpu=False)], ['c-ray'])
        with self.assertRaises(ValueError):
            sets.select(only=['nope'])

    def test_variants_of_one_test_run_apart(self):
        groups = sets.passes(sets.select(full=True))
        for g in groups:
            names = [t.test for t in g]
            self.assertEqual(len(names), len(set(names)))
        self.assertEqual(sum(len(g) for g in groups), len(sets.TESTS))

    def test_preset_string(self):
        t = next(t for t in sets.TESTS if t.key == 'gputest-plot3d')
        self.assertEqual(t.preset(), 'gputest.test=Plot3D;gputest.auto-resolution=1920 x 1080;gputest.mode=Fullscreen')
        self.assertEqual(next(t for t in sets.TESTS if t.key == 'coremark').preset(), '')

    def test_every_multi_option_test_is_preset(self):
        # In batch mode an unset option runs every combination.
        for t in sets.TESTS:
            if t.test in ('pts/coremark', 'pts/pybench'):
                continue
            self.assertTrue(t.options, t.key)


class SuiteConfig(unittest.TestCase):
    def test_configure_sets_paths_and_uploads_and_keeps_other_keys(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / 'pts'
            home.mkdir()
            (home / 'user-config.xml').write_text(
                '<?xml version="1.0"?><PhoronixTestSuite><Options><OpenBenchmarking>'
                '<AllowResultUploadsToOpenBenchmarking>TRUE</AllowResultUploadsToOpenBenchmarking>'
                '<IndexCacheTTL>3</IndexCacheTTL></OpenBenchmarking></Options></PhoronixTestSuite>')
            s = pts.Suite(home, '/bin/false')
            s.configure()
            s.configure()
            root = ET.parse(home / 'user-config.xml').getroot()
            opt = root.find('Options')
            self.assertEqual(opt.findtext('OpenBenchmarking/AllowResultUploadsToOpenBenchmarking'), 'FALSE')
            self.assertEqual(opt.findtext('OpenBenchmarking/IndexCacheTTL'), '3')
            self.assertEqual(opt.findtext('BatchMode/UploadResults'), 'FALSE')
            for key in ('Installation/EnvironmentDirectory', 'Installation/CacheDirectory', 'Testing/ResultsDirectory'):
                self.assertTrue(opt.findtext(key).startswith(str(home) + '/'), key)
            self.assertEqual(len(opt.findall('BatchMode')), 1)
            self.assertTrue((home / 'modules' / 'hb_percentiles.php').exists())


class Conditions(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.sys = Path(self.d.name)
        os.environ['HB_SYS'] = str(self.sys)

    def tearDown(self):
        os.environ.pop('HB_SYS', None)
        os.environ.pop('HB_LOAD', None)
        self.d.cleanup()

    def supply(self, name, kind, online):
        p = self.sys / 'class/power_supply' / name
        p.mkdir(parents=True)
        (p / 'type').write_text(kind + '\n')
        (p / 'online').write_text(online + '\n')

    def test_power_and_load(self):
        self.assertIsNone(conditions.on_ac())
        self.supply('BAT0', 'Battery', '1')
        self.supply('AC', 'Mains', '0')
        self.assertIs(conditions.on_ac(), False)
        (self.sys / 'firmware/acpi').mkdir(parents=True)
        (self.sys / 'firmware/acpi/platform_profile').write_text('balanced\n')
        os.environ['HB_LOAD'] = '99'
        c = conditions.snapshot()
        self.assertTrue(c['busy'])
        w = conditions.warnings(c)
        self.assertEqual(len(w), 3)
        self.assertIn('on battery', w)
        os.environ['HB_LOAD'] = '0.1'
        (self.sys / 'class/power_supply/AC/online').write_text('1\n')
        (self.sys / 'firmware/acpi/platform_profile').write_text('performance\n')
        self.assertEqual(conditions.warnings(conditions.snapshot()), [])


class PassMark(unittest.TestCase):
    def test_parse_finds_marks_anywhere(self):
        text = 'Version:\n  Major: 11\nResults:\n  Results Complete: true\n  SUMM_CPU: 9391.2\n  SUMM_ME: 1918\n' \
               '  CPU_SINGLETHREAD: 2020\n  Other: [ {ME_LATENCY: 67} ]\nSystemInformation:\n  Processor: x\n'
        self.assertEqual(pt.parse(text), {'cpu_mark': 9391.2, 'memory_mark': 1918.0, 'single_thread': 2020.0,
                                          'memory_latency': 67.0})

    def test_network_is_blocked(self):
        env = pt.offline_env()
        for k in ('http_proxy', 'https_proxy', 'HTTPS_PROXY', 'ALL_PROXY'):
            self.assertEqual(env[k], pt.NO_NETWORK)
        self.assertNotIn('no_proxy', env)


def record(host='host-a', **kw):
    tests = [{'key': 'coremark', 'label': 'CoreMark, all cores', 'component': 'cpu', 'unit': 'Iterations/Sec',
              'value': 54092.7, 'percentile': 14, 'samples': 7108, 'data_source': 'openbenchmarking.org'},
             {'key': 'fio-randread', 'label': 'fio random read 4KB', 'component': 'disk', 'unit': 'IOPS',
              'value': 505.0, 'percentile': 50, 'samples': 40, 'data_source': 'openbenchmarking.org'}]
    rec = {'host': host, 'started': '2026-10-31T14:02:00-05:00', 'set': 'quick', 'runs_per_test': 1,
           'tests': tests, 'skipped': [{'key': 'gputest-plot3d', 'reason': 'no display'}],
           'summary': pc.summarize(tests), 'system': {'Processor': 'Test CPU'}, 'data_retrieved': '2026-10-31T14:30:00'}
    rec.update(kw)
    return rec


class Render(unittest.TestCase):
    def test_terminal_plain(self):
        out = render.terminal(record(), color=False, warnings=['on battery'])
        self.assertNotIn('\x1b', out)
        self.assertIn('CoreMark, all cores', out)
        self.assertIn('14th', out)
        self.assertIn('only 40 samples', out)
        self.assertIn('! on battery', out)
        self.assertIn('skipped gputest-plot3d: no display', out)
        self.assertIn('OpenBenchmarking.org uploads', out)

    def test_terminal_colors_follow_percentile(self):
        out = render.terminal(record(), color=True)
        self.assertIn('\x1b[38;2;190;112;112m' + render.bar(14), out)   # red: 14th
        self.assertIn('\x1b[38;2;196;178;118m' + render.bar(50), out)   # yellow: 50th

    def test_notes_append_then_replace(self):
        text = '# Hardware\n\n## PassMark PerformanceTest\n\nold tables\n'
        one = render.update_notes(text, render.md_block([record()]))
        self.assertIn('## Benchmarks (hardware-bench)', one)
        self.assertIn('| **CPU** (14th) | CoreMark, all cores | 54,093 Iterations/Sec |', one)
        self.assertIn('old tables', one)
        two = render.update_notes(one, render.md_block([record(), record('host-b', passmark={'cpu_mark': 11306})]))
        self.assertEqual(two.count(render.END), 1)
        self.assertEqual(two.count('## Benchmarks (hardware-bench)'), 1)
        self.assertIn('### Hosts compared', two)
        self.assertIn('| PassMark CPU Mark | - | 11,306 |', two)


class Store(unittest.TestCase):
    def test_save_latest_hosts(self):
        with tempfile.TemporaryDirectory() as d:
            store.save(record(), d)
            p = store.save(record(started='2026-11-01T09:05:00-05:00'), d)
            self.assertEqual(p.name, '2026-11-01-0905.json')
            self.assertEqual(store.latest('host-a', d)['started'][:10], '2026-11-01')
            self.assertEqual(store.hosts(d), ['host-a'])
            self.assertIsNone(store.latest('nope', d))
            store.save(record(started='2026-11-02T09:05:00-05:00', set='only'), d)
            self.assertEqual(store.latest('host-a', d)['set'], 'only')
            self.assertEqual(store.latest('host-a', d, complete=True)['started'][:10], '2026-11-01')


class Run(unittest.TestCase):
    """The CLI end to end against the stub suite, with HOME in a temp dir."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        t = Path(self.d.name)
        self.t = t
        stub = t / 'pts-stub'
        stub.write_text(STUB)
        stub.chmod(0o755)
        (t / 'notes.md').write_text('# Hardware\n')
        self.env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY')}
        self.env.update(HOME=str(t / 'home'), HB_PTS=str(stub), HB_PTS_HOME=str(t / 'pts'), HB_RESULTS=str(t / 'results'),
                        HB_NOTES=str(t / 'notes.md'), HB_HOST='testhost', HB_LOAD='0', HB_PT=str(t / 'missing-pt'),
                        NO_COLOR='1')

    def tearDown(self):
        self.d.cleanup()

    def cli(self, *args):
        return subprocess.run([str(ROOT / 'bin' / 'hardware-bench'), *args], env=self.env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def calls(self):
        return [json.loads(line) for line in (self.t / 'pts' / 'calls.log').read_text().splitlines()]

    def test_quick_run_without_display(self):
        r = self.cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        runs = list((self.t / 'results' / 'testhost').glob('*.json'))
        self.assertEqual(len(runs), 1)
        rec = json.loads(runs[0].read_text())
        self.assertEqual([t['key'] for t in rec['tests']], ['coremark', 'pybench', 'stream-copy', 'fio-randread'])
        fio = rec['tests'][-1]
        self.assertEqual((fio['unit'], fio['value'], fio['percentile']), ('IOPS', 505.0, 50))
        py = rec['tests'][1]
        self.assertEqual((py['percentile'], py['data_source'], py['data_last']), (74, 'bundled', '2022-02-12'))
        self.assertEqual(rec['skipped'], [{'key': 'gputest-plot3d', 'reason': 'no display'}])
        self.assertEqual(rec['system']['Processor'], 'Test CPU (4 Cores)')
        self.assertEqual(rec['suite'], {'version': '10.8.4', 'system_type': 'D'})
        bench = [c for c in self.calls() if c['argv'][0] == 'batch-benchmark']
        self.assertEqual(len(bench), 1)
        self.assertEqual(bench[0]['times'], '1')
        self.assertNotIn('gputest', bench[0]['preset'])
        self.assertIn('fio.type=Random Read', bench[0]['preset'])
        self.assertIn('## Benchmarks (hardware-bench)', (self.t / 'notes.md').read_text())
        self.assertIn('fio random read 4KB', r.stdout)
        self.assertFalse((self.t / 'home' / '.phoronix-test-suite').exists())
        self.assertEqual(ET.parse(self.t / 'pts' / 'user-config.xml').getroot()
                         .findtext('Options/BatchMode/UploadResults'), 'FALSE')

    def test_full_run_splits_variants_and_skips_pt(self):
        r = self.cli('--full', '--offline')
        self.assertEqual(r.returncode, 0, r.stderr)
        bench = [c for c in self.calls() if c['argv'][0] == 'batch-benchmark']
        self.assertEqual(len(bench), 2)
        self.assertEqual({c['times'] for c in bench}, {'3'})
        self.assertIn('stream.run-type=Triad', bench[1]['preset'])
        self.assertTrue(all(c['offline'] == '1' for c in self.calls() if c['argv'][0] == 'hb_percentiles.json'))
        rec = store.latest('testhost', self.t / 'results')
        self.assertIn({'key': 'passmark', 'reason': 'pt not installed (README: Requirements)'}, rec['skipped'])
        self.assertEqual(len(rec['tests']), 12)
        self.assertIn('unigine-heaven', {s['key'] for s in rec['skipped']})

    def test_missing_suite_and_dry_run_and_show(self):
        r = self.cli('-n')
        self.assertEqual(r.returncode, 0)
        self.assertIn('PRESET_OPTIONS=stream.run-type=Copy', r.stdout)
        self.assertFalse((self.t / 'pts').exists())
        r = self.cli('show')
        self.assertNotEqual(r.returncode, 0)
        self.env['HB_PTS'] = ''
        self.env['PATH'] = '/usr/bin:/bin'
        r = self.cli()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('phoronix-test-suite not found', r.stderr)

    def test_a_suite_writing_to_home_is_reported(self):
        self.env['STUB_STRAY'] = '1'
        r = self.cli('--only', 'coremark')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('.phoronix-test-suite despite its config', r.stderr)
        rec = store.latest('testhost', self.t / 'results')
        self.assertTrue(any('.phoronix-test-suite' in w for w in rec['warnings']))

    def test_busy_machine_without_terminal_still_runs_and_records_it(self):
        self.env['HB_LOAD'] = '999'
        r = self.cli('--only', 'coremark')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('busy', r.stderr)
        rec = store.latest('testhost', self.t / 'results')
        self.assertTrue(rec['conditions']['busy'])
        self.assertEqual(rec['set'], 'only')
        self.assertTrue(any('busy' in w for w in rec['warnings']))
        r = self.cli('show', 'testhost')
        self.assertEqual(r.returncode, 0)
        self.assertIn('! busy', r.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=1)
