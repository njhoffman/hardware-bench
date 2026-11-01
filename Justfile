default:
    @just --list

# run the test suite (bats; the Python cases run inside it)
test *ARGS:
    bats {{ ARGS }} tests

# lint the Python
lint:
    pyflakes bin/hardware-bench lib/*.py tests/*.py

# symlink bin/hardware-bench into ~/.local/bin (or $XDG_BIN_HOME); refuses to replace anything that is not a symlink
install:
    #!/usr/bin/env bash
    set -euo pipefail
    src="$(pwd -P)/bin/hardware-bench"
    dest="${XDG_BIN_HOME:-$HOME/.local/bin}/hardware-bench"
    mkdir -p "${dest%/*}"
    if [[ -e "$dest" && ! -L "$dest" ]]; then
      echo "install: $dest exists and is not a symlink; remove it first" >&2
      exit 1
    fi
    ln -sfn "$src" "$dest"
    echo "$dest -> $src"
