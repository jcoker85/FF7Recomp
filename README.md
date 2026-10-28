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
own Disc 1 image.

```bash
git submodule update --init --recursive
tools/setup_framework.sh
tools/generate.sh "/path/to/Final Fantasy VII - Disc 1.chd"
cmake -S . -B build -G Ninja -DCMAKE_C_COMPILER=clang
cmake --build build
```

The game is built to `build/ff7/FinalFantasyVII_Recompiled.exe`.
`tools/package_release.sh` stages a release zip from that build into `dist/`.

Run from the source tree, the game looks for its discs in `discs/` at the
repository root (gitignored) rather than next to the executable: psxrecomp
anchors relative paths in `game.toml` on the project root, and only a packaged
release is its own root.

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

## License

PolyForm Noncommercial 1.0.0; see `LICENSE`. psxrecomp is under the same
license and recomp-ui is MIT.

Final Fantasy VII is a trademark of Square Enix, and the game is copyright its
owners. This repository contains none of its code, data or artwork.
