/*
 * FF7 FPS Mode "Target 30" (ff7.enhancement.steady-30, feature fps_mode,
 * switched by the launcher's Settings -> Display -> FPS Mode).
 *
 * Field screens step their game logic once per frame and end each frame with
 * VSync(n) in FIELD.BIN (0x800A2A68), n = 2 in most scenes and 3 in a few. On
 * the PlayStation's CPU a field frame took about two vblanks either way (30
 * fps), and more whenever a scene cost more, when the game slowed down with it.
 * Measured: Cloud walks the same distance per frame at any frame rate, so a
 * faster CPU alone makes the field run fast (40-60 fps).
 *
 * This feature does both halves:
 *  - selects variant 1 of game.toml [mod_immediate] group 1, which turns both
 *    choices into VSync(4): with a 4x CPU that measures as exactly two vblanks
 *    per frame (VSync(2) gives 60 fps, VSync(3) 40);
 *  - opens the [timing] guest_cycle_scale gate, so the emulated CPU runs 4x
 *    while FIELD.BIN is resident (game.toml's RAM predicate), and a frame no
 *    longer misses its two vblanks.
 * Battle, the world map, minigames and boot keep the original CPU speed.
 */
#include "mod_plugins.h"

enum { FIELD_VSYNC_GROUP = 1, FIELD_VSYNC_4 = 1 };

static void steady30_activate(void) {
    (void)psx_mod_set_immediate_selector(FIELD_VSYNC_GROUP, FIELD_VSYNC_4);
    psx_mod_set_guest_cycle_scale_gate(1);
}

PSX_MOD_CONSTRUCTOR(ff7_register_steady30_plugin) {
    (void)psx_mod_register_activation_plugin("ff7.steady30", steady30_activate);
}
