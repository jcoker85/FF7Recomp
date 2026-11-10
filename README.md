# FF7Recomp

A static recompilation of the PlayStation Final Fantasy VII as a native
Windows program, built on [psxrecomp](https://github.com/mstan/psxrecomp) and
[recomp-ui](https://github.com/RetroPortingToolKit/recomp-ui).

| Id | Game | Serials | Supported discs (USA) |
|---|---|---|---|
| `ff7` | Final Fantasy VII | SCUS-94163 / SCUS-94164 / SCUS-94165 | retail release, 3 discs |

This is an unofficial fan project. It is not affiliated with or endorsed by
Square Enix or Sony Interactive Entertainment.

## Play

You need your own disc images of the game, in the version listed in the table
above. Each disc can be a `.chd`, an `.iso`, or a `.cue` with its `.bin`.

1. Download the latest release zip and unzip it anywhere.
2. Put your three discs in the `discs` folder next to the program, named
   `Disc 1`, `Disc 2` and `Disc 3` (for example `discs/Disc 1.chd`,
   `discs/Disc 2.iso`). The game changes discs from this folder when it asks
   for the next one.
3. Run `FinalFantasyVII_Recompiled.exe` and click Play.
4. The launcher is where display, audio, controls and memory cards are set.
   To change discs by hand during play, press **Ctrl+L** or **F10** (or hold
   **Select + L3**), choose **Disc**, pick the disc and **Insert disc and
   resume**.

## Build

You need CMake, Ninja, Python 3 and a clang toolchain (the psxrecomp
llvm-mingw toolchain pack works; pass `-DCMAKE_C_COMPILER=clang`), plus your
own Disc 1 image (and optionally Disc 3, see below).

```bash
git submodule update --init --recursive
tools/setup_framework.sh
tools/generate.sh "/path/to/Final Fantasy VII - Disc 1.chd" "/path/to/Final Fantasy VII - Disc 3.chd"
cmake -S . -B build -G Ninja -DCMAKE_C_COMPILER=clang
cmake --build build
```

The game is built to `build/ff7/FinalFantasyVII_Recompiled.exe`.
`tools/package_release.sh` stages a release zip from that build into `dist/`.

Run from the source tree, the game looks for its discs in `discs/` at the
repository root (gitignored) rather than next to the executable: psxrecomp
anchors relative paths in `game.toml` on the project root, and only a packaged
release is its own root.

## Native code coverage

FF7's boot program (`SCUS_941.63`) is only the engine core. The game itself
lives in modules it loads from disc while you play. psxrecomp recompiles the
boot program, and `tools/generate.sh` also compiles these modules ahead of time
from your disc, following `games/ff7/aot/overlays.json`:

| Compiled to native code | Load address |
|---|---|
| Field (`FIELD/FIELD.BIN`) and world map (`WORLD/WORLD.BIN`) | 0x800A0000 |
| Minigames: Chocobo racing, snowboarding (both), Fort Condor, submarine, highway chase, jet | 0x800A0000 |
| Disc change (`DSCHANGE.X`) and ending (`ENDING.X`) | 0x800A0000 |
| All 13 menu modules (`MENU/*.MNU`) | 0x801D0000 |
| Battle (`BATTLE/BATTLE.X`) and the battle-start screen (`BROM.X`) | 0x800A0000 |
| Battle setup and results (`BATINI.X`, `BATRES.X`) | 0x801B0000 |
| All 289 battle effect modules (`MAGIC/*.BIN`) | 0x801B0000 |

Each module's disc location, load address and entry points come from the
game's own loader code: the boot program's module and menu tables, the battle
file table it copies from `INIT/YAMADA.BIN`, and the effect table inside
`BATTLE.X`. The profile pins those instructions and every input's hash, so a
different disc revision builds nothing rather than something wrong.
`tools/make_aot_profile.py` rebuilds the profile from your disc. Anything the
profile does not cover still runs correctly on psxrecomp's interpreter; the
`MAGIC/*.LZS` files are packed effect data, not code.

Discs 2 and 3 carry byte-identical copies of all of these modules, so they run
natively there too. The one code module only Disc 3 has, the final boss's
effect `SNOVA/LASBOSS3.BIN`, is built from Disc 3 by `games/ff7/aot/disc3.json`
when you pass Disc 3 to `tools/generate.sh`: the AOT pipeline compiles it into
an audited DLL in `cache/`, which the runtime loads beside the built-in
overlays. Without Disc 3 that one module runs on the interpreter.

`tools/check_aot_coverage.py` checks this statically. `discs` scores every
file on the discs for MIPS code, including embedded gzip streams and unpacked
LZS files, and lists code the profile does not compile. `modules` lists
code-shaped bytes inside compiled modules that no compiled function covers.
Today the only result is `LASBOSS3.BIN`, which `aot/disc3.json` covers. Code reached only through jumps the
compiler cannot follow can still fall back to the interpreter; only running the
game shows that.

## What is and is not in this repository

The repository holds configuration and build files. It does **not** contain
disc images, a PlayStation BIOS, game assets, or recompiled game code. The
recompiled C is generated on your machine from your own disc
(`tools/generate.sh`), and game data is read from your disc images when the
game runs. The game runs on the open-source OpenBIOS bundled with psxrecomp.

Release zips contain the built program, which includes a machine-translated
build of the game's own code, plus OpenBIOS. They contain no disc data, game
assets or retail BIOS.

## Framework patches

Both submodules stay pinned to upstream commits; `tools/setup_framework.sh`
applies these to their working trees.

- `psxrecomp-disc-roster-any-format.patch` lets an entry in `game.toml`'s
  disc list name a disc rather than a file: when `discs/Disc 2.chd` is not
  there, the runtime uses `Disc 2` in whichever format is (`.chd`, `.cue`,
  `.iso`, `.bin` or `.img`). Stock psxrecomp mounts the listed file only.
- `psxrecomp-aot-gzip-member.patch` adds a `gzip_member` method to the AOT
  pipeline's prepared files, so overlays the game stores gzip-compressed can be
  decoded from the disc and compiled ahead of time. Its optional `zero_tail`
  covers memory the loader clears right after a decoded module.
- `psxrecomp-libcxx-missing-includes.patch` adds two includes that newer libc++
  (llvm-mingw 20261020) no longer pulls in for the framework's bundled
  libraries: `<exception>` for toml11's `std::terminate` and `<cstdlib>` for
  rabbitizer's `malloc`/`free`. Without them the recompiler and runtime do not
  compile with current clang.

## License

PolyForm Noncommercial 1.0.0; see `LICENSE`. psxrecomp is under the same
license and recomp-ui is MIT.

Final Fantasy VII is a trademark of Square Enix, and the game is copyright its
owners. This repository contains none of its code, data or artwork.
