"""Test sets: which Phoronix Test Suite tests run, with which options.

Options are preset for every multi-option test (PRESET_OPTIONS); in batch mode
the suite would otherwise run every combination. The choices follow the
variants with the most OpenBenchmarking.org samples, so the percentiles rest
on as many results as possible (GPU tests at 1920 x 1080 fullscreen, fio on
4KB direct IO_uring reads).
"""
from dataclasses import dataclass, field

COMPONENTS = ('cpu', 'memory', 'gpu', 'disk')
COMPONENT_LABELS = {'cpu': 'CPU', 'memory': 'Memory', 'gpu': 'GPU', 'disk': 'Disk'}


@dataclass(frozen=True)
class Test:
    key: str            # stable name in results and reports
    test: str           # suite identifier, e.g. pts/stream
    component: str
    label: str
    options: tuple = field(default=())  # (option identifier, menu entry name) pairs
    full_only: bool = False
    unit: str = ''     # which result to keep when the test reports several (fio, openssl)

    @property
    def needs_display(self):
        return self.component == 'gpu'

    def preset(self):
        base = self.test.split('/', 1)[1]
        return ';'.join(f'{base}.{opt}={val}' for opt, val in self.options)


GPU_1080 = (('auto-resolution', '1920 x 1080'), ('mode', 'Fullscreen'))

TESTS = (
    Test('coremark', 'pts/coremark', 'cpu', 'CoreMark, all cores'),
    Test('pybench', 'pts/pybench', 'cpu', 'PyBench, one core'),
    Test('stream-copy', 'pts/stream', 'memory', 'Stream Copy', (('run-type', 'Copy'),)),
    Test('gputest-plot3d', 'pts/gputest', 'gpu', 'GpuTest Plot3D, 1080p', (('test', 'Plot3D'),) + GPU_1080),
    Test('fio-randread', 'pts/fio', 'disk', 'fio random read 4KB',
         (('type', 'Random Read'), ('engine', 'IO_uring'), ('direct', 'Yes'), ('size', '4KB'),
          ('cpu-threads', '1'), ('auto-disk-mount-points', 'Default Test Directory')), unit='IOPS'),
    Test('c-ray', 'pts/c-ray', 'cpu', 'C-Ray 1080p', (('resolution', '1080p'), ('rays', '16')), True),
    Test('openssl-rsa4096', 'pts/openssl', 'cpu', 'OpenSSL RSA4096', (('algo', 'RSA4096'),), True, 'sign/s'),
    Test('sysbench-cpu', 'pts/sysbench', 'cpu', 'Sysbench CPU', (('run-test', 'CPU'),), True),
    Test('kernel-build', 'pts/build-linux-kernel', 'cpu', 'Linux kernel build, defconfig', (('build', 'defconfig'),), True),
    Test('stream-triad', 'pts/stream', 'memory', 'Stream Triad', (('run-type', 'Triad'),), True),
    Test('ramspeed', 'pts/ramspeed', 'memory', 'RAMspeed average, integer',
         (('run-type', 'Average'), ('benchmark', 'Integer')), True),
    Test('cachebench-read', 'pts/cachebench', 'memory', 'CacheBench read', (('test', 'Read'),), True),
    Test('unigine-heaven', 'pts/unigine-heaven', 'gpu', 'Unigine Heaven, 1080p OpenGL',
         GPU_1080 + (('renderer', 'OpenGL'),), True),
    Test('fio-seqread', 'pts/fio', 'disk', 'fio sequential read 4KB',
         (('type', 'Sequential Read'), ('engine', 'IO_uring'), ('direct', 'Yes'), ('size', '4KB'),
          ('cpu-threads', '1'), ('auto-disk-mount-points', 'Default Test Directory')), True, 'MB/s'),
)


def select(full=False, gpu=True, only=None):
    """Tests for one run: the quick set, or every test with full."""
    out = [t for t in TESTS if (full or not t.full_only) and (gpu or not t.needs_display)]
    if only:
        unknown = set(only) - {t.key for t in TESTS}
        if unknown:
            raise ValueError('unknown test: ' + ', '.join(sorted(unknown)))
        out = [t for t in TESTS if t.key in only and (gpu or not t.needs_display)]
    return out


def passes(tests):
    """Split tests into suite runs with at most one entry per suite test.

    PRESET_OPTIONS applies per suite test, so two variants of one test (stream
    Copy and Triad) in one run would be crossed with each other's options.
    """
    out = []
    for t in tests:
        for p in out:
            if all(o.test != t.test for o in p):
                p.append(t)
                break
        else:
            out.append([t])
    return out
