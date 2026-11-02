# hardware-bench task list

Open work for hardware-bench. Every item carries a priority, `(p1)` high,
`(p2)` normal or `(p3)` low, and a category: `[bug]`, `[feature]`,
`[refactor]`, `[docs]`, `[test]`, `[chore]` or `[perf]`.

Reviewed: 2026-11-01

## 1. Real runs

- [ ] **First real quick and full runs.** (p2) [test] Run `hardware-bench`
  (quick) and `hardware-bench --full` on a real machine and keep the runs.
  Verified so far against the real suite: pybench, stream Copy and fio random
  read (presets applied, live percentiles, nothing in
  `~/.phoronix-test-suite`), plus coremark by hand. Not yet run for real: the
  GPU tests (gputest, unigine-heaven: fullscreen, and their `1920 x 1080`
  preset only matches when that mode is available; otherwise the suite falls
  back to its default and the recorded arguments show it) and the other
  `--full` tests.
- [ ] **pt autorun.** (p2) [test] `--full` runs `pt -r 3` in a temp dir with
  its proxies pointed at a closed port and reads `results_all.yml`.
  Unchecked: whether autorun exits by itself or waits for a key, whether the
  proxy block stops its upload (it might also show an error), and the YAML
  layout: `pt.parse` finds `SUMM_CPU`, `SUMM_ME` and the `CPU_*`/`ME_*` keys
  anywhere in the document, guessed from the binary's strings. Needs a
  terminal and the sudo password; fix `lib/pt.py` from a real
  `results_all.yml`.

## 2. Packaging and docs

- [x] **Add a LICENSE.** (p2) [chore] MIT, 2026-11-02.
- [ ] **Install the suite from the repo.** (p3) [feature] The pinned suite
  (version, checksum, PHP packages, wrapper) is documented in the README but
  installed by a dotfiles recipe; a `just deps` would make the repo
  self-contained.
- [ ] **CI.** (p3) [test] Run `just test` and `just lint` on push (GitHub
  Actions; the stub suite needs no PHP).
