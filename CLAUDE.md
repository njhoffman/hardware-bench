# CLAUDE.md

Guidance for Claude Code in this repository.

## Commands

- `just test [bats options]` — the suite: `tests/hardware-bench.bats` runs
  `tests/hardware_bench_cases.py` (unittest, stub suite and pt) and the CLI.
  One case class: `python3 tests/hardware_bench_cases.py Run`.
- `just lint` — pyflakes. `just install` — link `bin/hardware-bench` into `~/.local/bin`.

## Layout

- `bin/hardware-bench` — CLI (run, show, report, list); puts `lib/` on `sys.path`.
- `lib/sets.py` — the quick and full test sets (suite test, presets, unit, component).
- `lib/pts.py` — the suite under its own home (`HB_PTS_HOME`): writes
  `user-config.xml` before each call (uploads off, every directory inside the
  home), installs `hb_percentiles.php` as a module, runs batch-benchmark.
- `lib/hb_percentiles.php` — suite module: percentile cut points per test by
  comparison hash, live or from the bundled `generated.json`.
- `lib/percentile.py` — scores to percentiles, component and overall scores.
- `lib/pt.py` — PassMark pt autorun in a temp dir with its network blocked, `results_all.yml` parsing.
- `lib/conditions.py` — load, battery, power profile, display (`HB_SYS`, `HB_LOAD` for tests).
- `lib/store.py` — run records (`HB_RESULTS`) and the notes file (`HB_NOTES`); `lib/render.py` — terminal bars, the markdown block.

## Invariants

- Nothing is ever uploaded, and nothing is written to `~/.phoronix-test-suite`
  (a test checks a stray write is reported).
- Standard library only (Python 3); the suite version is pinned (README: Requirements).
- Tests never touch the real results, notes or suite home: they set
  `HB_RESULTS`, `HB_NOTES`, `HB_PTS_HOME`, `HB_PTS`, `HB_HOST`.
- The notes file is only rewritten between its begin and end markers.

## Versioning

Semantic versioning in `VERSION`, an annotated tag `vX.Y.Z` per release,
Keep a Changelog entries in `CHANGELOG.md`, open work in `TODO.md`.
