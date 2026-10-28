#!/usr/bin/env bash
# Prepare the framework checkout: build the recompiler emitters (plus the CHD
# reader the tools use). Both submodules are used as pinned, unpatched.
#
# Usage (from the repository root):
#   tools/setup_framework.sh [--toolchain-dir DIR]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

for sub in psxrecomp recomp-ui; do
  [[ -e "$sub/.git" ]] || { echo "error: $sub is missing; run: git submodule update --init --recursive" >&2; exit 1; }
done

bash psxrecomp/tools/ci/build_emitters.sh --framework psxrecomp --build-dir psxrecomp/recompiler/build "$@"
cmake --build psxrecomp/recompiler/build --target chdr
