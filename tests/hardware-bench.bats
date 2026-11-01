#!/usr/bin/env bats
# hardware-bench: the Python cases (percentiles, sets, suite config,
# conditions, pt parsing, rendering, runs against a stub suite) and the CLI.

ROOT="$BATS_TEST_DIRNAME/.."

@test "hardware-bench: python cases" {
  run python3 "$BATS_TEST_DIRNAME/hardware_bench_cases.py"
  [ "$status" -eq 0 ] || { printf '%s\n' "$output"; false; }
}

@test "hardware-bench: help and list" {
  run "$ROOT/bin/hardware-bench" --help
  [ "$status" -eq 0 ]
  [[ $output == *"--full"* && $output == *"report"* ]]
  run "$ROOT/bin/hardware-bench" list
  [ "$status" -eq 0 ]
  [[ $output == *"quick  cpu     coremark"* && $output == *"PassMark pt"* ]]
}

@test "hardware-bench: results and notes default under XDG_DATA_HOME" {
  run env -u HB_RESULTS -u HB_NOTES XDG_DATA_HOME=/x python3 -c "
import sys; sys.path.insert(0, '$ROOT/lib'); import store
print(store.results_root()); print(store.notes_file())"
  [ "$status" -eq 0 ]
  [ "$output" = $'/x/hardware-bench/results\n/x/hardware-bench/hardware.md' ]
}
