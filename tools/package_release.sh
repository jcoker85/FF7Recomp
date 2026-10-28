#!/usr/bin/env bash
# Stage a ready-to-run release from a finished build and zip it.
#
# The result is what a player downloads: the game program and the files it
# reads beside itself. It holds no disc images, BIOS dumps, saves, settings
# from this machine, sources or generated C. The first launch opens the
# launcher so the player can choose their own disc image.
#
# Usage (from the repository root, after `cmake --build build`):
#   tools/package_release.sh [--build-dir build] [--version 1.0.0]
# Output: dist/FF7Recomp-<version>/ and the same name + .zip
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BUILD=build
VERSION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-dir) BUILD="${2:?}"; shift 2 ;;
    --version) VERSION="${2:?}"; shift 2 ;;
    *) echo "error: unknown argument $1" >&2; exit 1 ;;
  esac
done
[[ -n "$VERSION" ]] || VERSION="$(git describe --tags --always 2>/dev/null || echo dev)"
NAME="FF7Recomp-$VERSION"
STAGE="dist/$NAME"
EXE="FinalFantasyVII_Recompiled.exe"
src="$BUILD/ff7"
[[ -f "$src/$EXE" ]] || { echo "error: $src/$EXE is missing; run cmake --build $BUILD first" >&2; exit 1; }
for need in assets/fonts assets/img bios/openbios.bin bios/OpenBIOS.LICENSE game.toml mods/bundled; do
  [[ -e "$src/$need" ]] || { echo "error: $src/$need is missing; rebuild" >&2; exit 1; }
done

rm -rf "$STAGE" "dist/$NAME.zip"
mkdir -p "$STAGE/licenses" "$STAGE/bios" "$STAGE/mods"
cp "$src/$EXE" "$src/game.toml" "$STAGE/"
for opt in game_options.toml psx_game_version.txt; do
  [[ -f "$src/$opt" ]] && cp "$src/$opt" "$STAGE/"
done
for dll in "$src"/*.dll; do [[ -e "$dll" ]] && cp "$dll" "$STAGE/"; done
cp -r "$src/assets" "$STAGE/assets"
cp "$src/bios/openbios.bin" "$src/bios/OpenBIOS.LICENSE" "$STAGE/bios/"
cp -r "$src/mods/bundled" "$STAGE/mods/bundled"

cp LICENSE "$STAGE/licenses/FF7Recomp-LICENSE"
cp psxrecomp/LICENSE "$STAGE/licenses/psxrecomp-LICENSE"
cp recomp-ui/LICENSE "$STAGE/licenses/recomp-ui-LICENSE"
[[ -d psxrecomp/runtime/licenses ]] && cp -r psxrecomp/runtime/licenses/. "$STAGE/licenses/"
[[ -f psxrecomp/THIRD_PARTY_ATTRIBUTION.md ]] && cp psxrecomp/THIRD_PARTY_ATTRIBUTION.md "$STAGE/licenses/"

cat > "$STAGE/START_HERE.txt" <<EOF
FF7Recomp $VERSION

Final Fantasy VII as a native Windows program. Unofficial fan project;
non-commercial use only.

You need your own disc images of the game (.chd, or .cue with its .bin).
Nothing from the game is included here.

Supported discs (USA): Final Fantasy VII SCUS-94163, SCUS-94164 and
SCUS-94165. Other versions are accepted by the launcher but are not expected
to run correctly.

1. Run $EXE. The first time, its launcher opens: choose your Disc 1 image
   there, then start the game.
2. The launcher opens again at any time for display, audio, controls and
   memory cards.

The game runs on the bundled open-source OpenBIOS (bios/OpenBIOS.LICENSE).
The game program contains a machine-translated build of the game's own code.
Licenses are in the licenses folder.
EOF

# Nothing personal or copyrighted may ride along.
bad="$(find "$STAGE" -type f \( -iname '*.chd' -o -iname '*.cue' -o -iname '*.iso' -o -iname '*.mcd' -o -iname '*.mcr' \
      -o -iname 'settings.toml' -o -iname 'state.toml' -o -iname 'keybinds.ini' -o -iname 'input.ini' \
      -o -iname 'SCPH*' -o -iname '*.c' \) 2>/dev/null || true)"
[[ -z "$bad" ]] || { echo "error: the package would include files it must not:" >&2; echo "$bad" >&2; exit 1; }
bins="$(find "$STAGE" -type f -iname '*.bin' ! -path '*/bios/openbios.bin' 2>/dev/null || true)"
[[ -z "$bins" ]] || { echo "error: unexpected .bin files in the package:" >&2; echo "$bins" >&2; exit 1; }

PY="$(command -v python3 || command -v python)"
"$PY" - "$STAGE" "dist/$NAME.zip" <<'PY'
import os, sys, zipfile
stage, out = sys.argv[1], sys.argv[2]
base = os.path.dirname(stage)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for d, _, files in os.walk(stage):
        for f in sorted(files):
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, base))
print(f"{out}: {os.path.getsize(out) / 1048576:.1f} MB")
PY
echo "staged $STAGE"
