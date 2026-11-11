#!/usr/bin/env bash
# Regenerate the recompiled C from your own disc image.
#
# Usage (from the repository root, after tools/setup_framework.sh):
#   tools/generate.sh <Disc 1 .cue or .chd> [<Disc 3 .cue or .chd>]
#
# Disc 3 is optional. It adds native code for the one module only Disc 3
# carries (the final boss's effect, SNOVA/LASBOSS3.BIN); without it that module
# runs on the interpreter.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
abspath() { [[ -z "$1" ]] && return; (cd "$(dirname "$1")" && printf '%s/%s' "$(pwd)" "$(basename "$1")"); }
DISC="$(abspath "${1:?disc image}")"
DISC3="$(abspath "${2:-}")"
G="$ROOT/games/ff7"
PY="$(command -v python3 || command -v python)"
cd "$G"
# The CLI regenerates OpenBIOS in its work area (games/ff7/psxrecomp) when that
# has no BIOS C, and at this framework pin the regenerate step fails there (the
# work area has no tools/bios_emitter_fingerprint.cmake). The build links the
# framework's own committed OpenBIOS C, so seed the work area with that copy.
mkdir -p psxrecomp/generated
cp -n "$ROOT"/psxrecomp/generated/OpenBIOS* psxrecomp/generated/
# --no-aot-static: the CLI looks for the AOT pipeline in that same work area,
# which has no tools/, so the static overlay step runs below instead.
"$PY" "$ROOT/psxrecomp/psxrecomp_cli.py" generate --config game.toml --project-root . --disc "$DISC" --no-aot-static

# Native overlays (aot/overlays.json): field, world map, minigames and menus,
# rebuilt from the disc's own bytes. The pipeline reads raw sectors from the
# cue/bin that generate prepared in disc/ from your image, checks every loader
# fact the profile pins, and writes generated/overlays_static*.c.
CUE="$G/disc/Final Fantasy VII - Disc 1.cue"
CPS=()
grep -q psx_cps_mark_game generated/SCUS_941.63_dispatch.c && CPS=(--cps)
WORK="$G/.cache/aot-static"
rm -rf "$WORK"
mkdir -p "$WORK"
"$PY" "$ROOT/psxrecomp/tools/aot_overlay_pipeline.py" static   --profile aot/overlays.json --game-toml game.toml --disc "$CUE"   --recompiler "$ROOT/psxrecomp/recompiler/build/psxrecomp-game$( [[ -e "$ROOT/psxrecomp/recompiler/build/psxrecomp-game.exe" ]] && echo .exe)"   --work-dir "$WORK/run" --gcc "${OVERLAY_CC:-$(command -v gcc || command -v clang)}"   --cmake "$(command -v cmake)" "${CPS[@]}"

# Disc 3's LASBOSS3.BIN (aot/disc3.json) becomes an audited DLL cache the runtime
# loads beside the static shard. CMake copies generated/disc3/cache next to the
# executable and tools/package_release.sh ships it.
if [[ -n "$DISC3" ]]; then
  CUE3="$G/disc/Final Fantasy VII - Disc 3.cue"
  case "${DISC3,,}" in
    *.chd) "$PY" "$ROOT/psxrecomp/tools/psx_chd.py" "$DISC3" --no-hash --layout single              --extract "$G/disc" --cue-name "Final Fantasy VII - Disc 3.cue" ;;
    *.cue) CUE3="$DISC3" ;;
    *) echo "error: Disc 3 must be a .chd or .cue" >&2; exit 1 ;;
  esac
  rm -rf "$WORK-disc3" generated/disc3
  mkdir -p "$WORK-disc3"
  "$PY" "$ROOT/psxrecomp/tools/aot_overlay_pipeline.py" release     --profile aot/disc3.json --game-toml game.toml --disc "$CUE3"     --recompiler "$ROOT/psxrecomp/recompiler/build/psxrecomp-game$( [[ -e "$ROOT/psxrecomp/recompiler/build/psxrecomp-game.exe" ]] && echo .exe)"     --work-dir "$WORK-disc3/run" --stage generated/disc3     --gcc "${OVERLAY_CC:-$(command -v gcc || command -v clang)}"
fi
