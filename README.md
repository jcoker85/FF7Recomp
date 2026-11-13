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
3. Run `FF7Recomp.exe`. The cover art and the program's icon download in the
   background the first time. **Play** starts the game; **Settings** opens its launcher.
4. The launcher is where display, audio, controls, memory cards and the
   options below are set.
   To change discs by hand during play, press **Ctrl+L** or **F10** (or hold
   **Select + L3**), choose **Disc**, pick the disc and **Insert disc and
   resume**.

## Options

All of these start off, so a fresh install plays like the PlayStation game.

- **FPS Mode** (Settings -> Display): **Original** or **Target 30**.
  - **Original** plays at the PlayStation's frame rates. Field screens (towns,
    dungeons, anywhere you walk around) aim for 30 frames a second, but busy
    ones drop below that, and because the field runs its game logic once per
    frame, the game slows down with them.
  - **Target 30** holds field screens at a steady 30 without slowing down. It
    gives the emulated CPU 4x headroom while a field screen is loaded and caps
    each field frame at two vblanks, so frames neither drop nor run fast
    (`games/ff7/game.toml` `[mod_immediate]` and `[timing]`,
    `games/ff7/mods/src/ff7_steady30.c`).
  - The rest of the game is the same in both. The world map runs at 30.
    Battles draw their 3D at 15 frames a second; their menus and gauges
    redraw at 60, so a frame counter reads 60 there. Battle logic also runs
    once per frame, so 30 fps battles would play at double speed. Movies are
    15 frames a second, and so are scenes drawn over a movie background, such
    as the camera sweeps around the Mako reactors.
- **Faster disc loading** (Mods): emulates a 4x faster CD drive. On Disc 1 the
  first battle draws 2.9 s after the game asks for it instead of 4.4 s; the
  rest is the game's own transition. Movies, music and transitions keep their
  original speed.
- **Smooth Motion** (Settings -> Display) is listed because psxrecomp offers it
  to every game, but it does little in FF7: the in-between frames it builds
  need 3D it can follow from frame to frame, and it rejects nearly all of
  FF7's. FPS Mode above is the way to a steadier frame rate.
- **Dithering** (Settings -> Display): the PlayStation's dithering pattern on
  shaded polygons. **On** is the console's pattern on its own pixel grid, so at
  a high internal resolution it shows as a visible checkerboard; **Fine** draws
  it at full resolution, nearly invisible; **Off** gives smooth colour.
- **Texture filtering** (Settings -> Display) smooths textures on polygons
  only. Field backgrounds, sprites and text stay sharp: each field screen is
  built from layers of 16x16 tiles, and the bottom layer hides a pure green
  filler under the top one, which filtering would blend into green outlines
  (`games/ff7/game.toml` `filter_rectangles = false`).
- Graphics options from psxrecomp: internal resolution, anti-aliasing,
  PGXP precision (less wobbly polygons) and HD texture packs.
- No widescreen: field screens are pre-rendered 320-pixel backgrounds, and a
  wider view of battles shows the edges of their arena models, so FF7 stays
  4:3.

**HD texture packs.** psxrecomp's HD Texture Packs mod works for FF7 as it is:
enable it on the Mods page, turn on **Dump textures** to collect the game's
textures while playing, edit them, and put them back as replacements. The
replacements show with the OpenGL renderer (the default). No pack is included.

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

The game is built to `build/ff7/FinalFantasyVII_Recompiled.exe`, and the hub to
`build/FF7Recomp.exe`.
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

## Code in this repository

- `hub/`: the menu (`hub.c`, ported from TwistedMetal1234Recomp's), a
  cover-shaped window with **Play** and **Settings**. It lists the games in
  `games.txt` beside it (here one) and downloads the cover from
  [libretro-thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails),
  which is not redistributed here. It has no icon built in: on its first start
  it downloads its icon (credited below) into `covers/icon.png` and makes
  `covers/icon.ico`, and its window and the game window show it from there (a
  square PNG put at `covers/icon.png` is used instead). It also writes the icon
  into its own `FF7Recomp.exe` (it renames itself to `FF7Recomp.exe.old` and
  puts a copy with the icon in its place), so Explorer and shortcuts show it
  from the next start; the release zip's hub has none.
- The hub and game window icon: [Final Fantasy VII icon by Gundamguy2255](https://www.steamgriddb.com/icon/10591)
  on SteamGridDB, downloaded by the hub on its first start.
- `games/ff7/mods/preloaded/`: the **Faster disc loading** package, which turns
  on psxrecomp's CD Speed feature at 4x.
- `games/ff7/symbols.toml`: names for the functions this project has traced
  (main loop, module loaders, overlay entry points) and the tables they use;
  `tools/sync_symbols.py` writes `psx_symbols.h` from it.

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
applies these to their working trees (`psxrecomp-*` to psxrecomp, `recomp-ui-*`
to recomp-ui).

- `psxrecomp-disc-roster-any-format.patch` lets an entry in `game.toml`'s
  disc list name a disc rather than a file: when `discs/Disc 2.chd` is not
  there, the runtime uses `Disc 2` in whichever format is (`.chd`, `.cue`,
  `.iso`, `.bin` or `.img`). Stock psxrecomp mounts the listed file only.
- `psxrecomp-aot-gzip-member.patch` adds a `gzip_member` method to the AOT
  pipeline's prepared files, so overlays the game stores gzip-compressed can be
  decoded from the disc and compiled ahead of time. Its optional `zero_tail`
  covers memory the loader clears right after a decoded module.
- `recomp-ui-display-settings.patch` turns the launcher's window size control
  into a dropdown and adds the render thread, present
  thread and Smooth Motion checkboxes to the Display settings (from
  TwistedMetal1234Recomp).
- `psxrecomp-filter-rectangles.patch` adds `[video] filter_rectangles`: a
  title setting that keeps textured rectangles (2D tiles, sprites, text)
  point-sampled while texture filtering smooths polygons (OpenGL renderer).
- `psxrecomp-launcher-dithering.patch` and `recomp-ui-dithering-setting.patch`
  make `[video] dithering` a player setting: a Dithering row (On / Fine / Off)
  in the launcher's Display settings, saved in `settings.toml` and applied at
  launch and from the in-game menu. Stock psxrecomp reads it only from
  `game.toml`.
- `psxrecomp-window-icon-env.patch` lets whatever starts the game choose its
  window icon: `PSX_WINDOW_ICON` names a PNG used instead of
  `assets/psxrecomp.png`. The hub sets it to the icon it downloaded.
- `psxrecomp-launcher-fps-mode.patch` and `recomp-ui-fps-mode.patch` add the
  launcher's FPS Mode row (Settings -> Display) and `[video] fps_mode =
  "original" | "30"` in `settings.toml`. At launch the runtime switches every
  mod package's hidden `fps_mode` feature on for Target 30 and off for
  Original; here that is the Target 30 package. Adapted from
  TwistedMetal1234Recomp's FPS Mode.
- `psxrecomp-libcxx-missing-includes.patch` adds three includes that newer libc++
  (llvm-mingw 20261020) no longer pulls in for the framework's bundled
  libraries: `<exception>` for toml11's `std::terminate` and `<cstdlib>` for
  rabbitizer's `malloc`/`free` and the recompiler's `strtoul`. Without them the recompiler and runtime do not
  compile with current clang.

## License

PolyForm Noncommercial 1.0.0; see `LICENSE`. psxrecomp is under the same
license and recomp-ui is MIT.

Final Fantasy VII is a trademark of Square Enix, and the game is copyright its
owners. This repository contains none of its code, data or artwork, nor the
icon and box art the hub downloads.
