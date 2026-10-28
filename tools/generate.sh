#!/usr/bin/env bash
# Regenerate the recompiled C from your own disc image.
#
# Usage (from the repository root, after tools/setup_framework.sh):
#   tools/generate.sh <path to Disc 1 .cue or .chd>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DISC="${1:?disc image}"
G="$ROOT/games/ff7"
PY="$(command -v python3 || command -v python)"
cd "$G"
# The CLI regenerates OpenBIOS in its work area (games/ff7/psxrecomp) when that
# has no BIOS C, and at this framework pin the regenerate step fails there (the
# work area has no tools/bios_emitter_fingerprint.cmake). The build links the
# framework's own committed OpenBIOS C, so seed the work area with that copy.
mkdir -p psxrecomp/generated
cp -n "$ROOT"/psxrecomp/generated/OpenBIOS* psxrecomp/generated/
"$PY" "$ROOT/psxrecomp/psxrecomp_cli.py" generate --config game.toml --project-root . --disc "$DISC"
