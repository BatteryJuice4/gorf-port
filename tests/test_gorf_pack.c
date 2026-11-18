// Checks that gamepacks/gorf/game.toml parses with the pinned launcher and still
// says what was verified against the real cartridge.
#include "gamepack/gamepack.h"
#include "input/keynames.h"

#include <stdio.h>
#include <string.h>

#ifndef GORF_PINNED_LAUNCHER
#error "CMake passes the submodule's launcher version"
#endif

static int failures;
#define CHECK(cond, ...) do { if (!(cond)) { fprintf(stderr, "FAIL %s:%d: ", __FILE__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); fputc('\n', stderr); failures++; } } while (0)

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: test_gorf_pack path/to/game.toml\n");
        return 2;
    }
    static char text[256 * 1024];
    FILE* f = fopen(argv[1], "rb");
    if (!f) {
        fprintf(stderr, "can't open %s\n", argv[1]);
        return 1;
    }
    size_t n = fread(text, 1, sizeof(text) - 1, f);
    fclose(f);
    text[n] = 0;

    gamepack_t p;
    settings_t d;
    settings_default(&d);
    char err[256], warns[4096];
    CHECK(gamepack_parse(text, n, &p, &d, err, sizeof(err), warns, sizeof(warns)), "parse failed: %s", err);

    CHECK(warns[0] == 0, "unexpected warnings:\n%s", warns);

    CHECK(!strcmp(p.id, "gorf") && !strcmp(p.title, "Gorf"), "id/title");
    CHECK(p.media == GAMEPACK_MEDIA_CARTRIDGE && p.cart_type == GAMEPACK_CART_16K, "16K cartridge");
    CHECK(gamepack_knows_sha1(&p, "4d24d5ed3d8b38235d9ae5965b675ffece0981cc"), "verified dump hash missing");
    CHECK(d.input.joystick_port == 1, "Gorf reads joystick port 1");
    CHECK(d.input.keys[INPUT_FIRE][0] == input_key_from_name("Space"), "fire on Space");
    CHECK(d.input.keys[INPUT_FIRE][2] == input_key_from_name("Gamepad_A"), "fire on gamepad A");
    CHECK(d.input.keys[INPUT_UP][1] == input_key_from_name("Gamepad_Up"), "d-pad up (launcher default)");
    CHECK(p.ntsc, "Gorf runs on an NTSC machine (owner's choice)");
    CHECK(!strcmp(d.video.palette, "colodore"), "palette \"%s\", want colodore", d.video.palette);
    CHECK(gamepack_launcher_ok(&p, GORF_PINNED_LAUNCHER), "pinned launcher %s too old for the pack", GORF_PINNED_LAUNCHER);
    CHECK(!gamepack_launcher_ok(&p, "0.3.0"), "0.3.0 has no gamepad names; the pack must require 0.4.0");
    if (failures == 0) printf("test_gorf_pack: all passed\n");
    return failures ? 1 : 0;
}
