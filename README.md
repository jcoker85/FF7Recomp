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

You need your own disc images of the game (`.chd`, or `.cue` with its `.bin`),
in the version listed in the table above.

1. Download the latest release zip and unzip it anywhere.
2. Run `FinalFantasyVII_Recompiled.exe`. The first time, its launcher opens:
   choose your Disc 1 image, then click Play.
3. The launcher is where display, audio, controls and memory cards are set.

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

## What is and is not in this repository

The repository holds configuration and build files. It does **not** contain
disc images, a PlayStation BIOS, game assets, or recompiled game code. The
recompiled C is generated on your machine from your own disc
(`tools/generate.sh`), and game data is read from your disc images when the
game runs. The game runs on the open-source OpenBIOS bundled with psxrecomp.

Release zips contain the built program, which includes a machine-translated
build of the game's own code, plus OpenBIOS. They contain no disc data, game
assets or retail BIOS.

Both submodules are pinned to upstream commits and used unpatched.

## License

PolyForm Noncommercial 1.0.0; see `LICENSE`. psxrecomp is under the same
license and recomp-ui is MIT.

Final Fantasy VII is a trademark of Square Enix, and the game is copyright its
owners. This repository contains none of its code, data or artwork.
