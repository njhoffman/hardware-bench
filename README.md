# hardware-bench

Benchmarks this machine through the [Phoronix Test Suite](https://github.com/phoronix-test-suite/phoronix-test-suite)
and ranks every score among OpenBenchmarking.org results, with bars per test,
per component (CPU, memory, GPU, disk) and overall.

```sh
hardware-bench -n               # the plan, nothing run
hardware-bench                  # quick set: one run per test, about 10 minutes
hardware-bench --full           # every test three times, plus PassMark pt (about an hour)
hardware-bench --only coremark,stream-copy
hardware-bench show [HOST]      # a host's latest run
hardware-bench report           # rewrite the notes file from the saved runs
hardware-bench list             # the tests in each set
```

- **Nothing is uploaded.** The suite runs from its own state directory
  (`~/.local/share/hardware-bench/pts`, `HB_PTS_HOME`) with uploads turned off;
  its `user-config.xml` is rewritten before every call, so nothing lands in
  `~/.phoronix-test-suite`. Percentile lookups send only a test's comparison
  hash and the system type. pt runs with its network blocked.
- **Percentiles** come from the `hb_percentiles` suite module
  (`lib/hb_percentiles.php`), live from OpenBenchmarking.org, falling back to
  the cut points bundled with each test profile (early 2022, labelled as
  such; `--offline` uses only those). Each is shown with its sample count, a
  note under 100 results, and the date of the data. OpenBenchmarking.org
  uploads lean to servers and workstations: read them as "among
  OpenBenchmarking.org results", not "among PCs".
- **Conditions**: load, battery and power profile are checked before a run
  (a busy machine asks first; `-y` skips the question) and stored with it.
  GPU tests are skipped without a display.

## Results

Each run is saved as `<results>/<host>/<YYYY-MM-DD-HHMM>.json`, and a
generated block per host plus a comparison of your machines is rewritten in
the notes file, between `<!-- hardware-bench:begin ... -->` and
`<!-- hardware-bench:end -->` (the rest of the file is left alone):

| | Default | Override |
|---|---|---|
| Results | `$XDG_DATA_HOME/hardware-bench/results` | `HB_RESULTS` |
| Notes | `$XDG_DATA_HOME/hardware-bench/hardware.md` | `HB_NOTES` |

Point both into a repository to keep the runs under version control.

## Requirements

- Python 3 (standard library only; developed on 3.13).
- **Phoronix Test Suite 10.8.4**, pinned: `lib/hb_percentiles.php` uses the
  suite's internal classes, so check the module still works before moving to a
  newer release. Install the GitHub release tarball
  (`phoronix-test-suite-10.8.4.tar.gz`, sha256
  `1f2092d536c0a3193efc53e4a50f3cee65c0ef1a78d31e5404f1c663fff7b7f4`) and the
  PHP packages `php-cli php-xml php-zip php-gd php-sqlite3`. The launcher
  finds its files from `dirname $0`: put a wrapper script on PATH, not a
  symlink. `HB_PTS` names the launcher when it is not on PATH.
- **PassMark pt** for `--full` (optional; skipped when missing):
  <https://www.passmark.com/products/pt_linux/>. The binary links
  `libncurses.so.5`, which current Ubuntu and Debian no longer ship; Debian
  bookworm's `libncurses5` / `libtinfo5` next to it with `LD_LIBRARY_PATH`
  work. pt runs `sudo dmidecode` itself, so it needs a terminal.

## Install

```sh
just install           # links bin/hardware-bench into ~/.local/bin (or $XDG_BIN_HOME)
```

## Tests

`just test`: `tests/hardware_bench_cases.py` (unittest) against a stub suite
and stub pt, plus the CLI (`tests/hardware-bench.bats`). `just lint` runs
pyflakes.

## License

MIT, see [LICENSE](LICENSE).
