# Changelog

All notable changes to hardware-bench. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-11-02

### Added

- MIT license (`LICENSE`).

## [0.1.0] - 2026-11-01

First release on its own, extracted from njhoffman/.shell (`scripts/tools/hardware-bench/`), where it shipped
in 0.24.0 through 0.39.0.

### Added

- `hardware-bench` benchmarks the machine through the Phoronix Test Suite and ranks every score among
  OpenBenchmarking.org results, with bars per test, per component (CPU, memory, GPU, disk) and overall. The
  quick set takes about 10 minutes (one run per test); `--full` runs every test three times and adds PassMark
  pt's CPU Mark and Memory Mark. `show`, `report` and `list` read the saved runs; `-n` prints the plan.
- Nothing is uploaded: the suite runs from its own state directory with uploads turned off, and pt runs with
  its network blocked. Percentile lookups send only a test's identifier and the system type. Each percentile is
  shown with its sample count, a note under 100 results, and the date of the data.
- The busy-machine check warns about load, battery and power profile and stores them with the run.
- `just test`, `just lint`, `just install`.

### Changed

- Runs and the notes file default to `$XDG_DATA_HOME/hardware-bench/` (`results/`, `hardware.md`) instead of
  `deploy/notes/` in the dotfiles repo; `HB_RESULTS` and `HB_NOTES` still override them.
- Messages about a missing suite or pt point at the README's Requirements instead of a dotfiles recipe.
