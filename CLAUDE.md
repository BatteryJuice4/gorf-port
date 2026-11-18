# CLAUDE.md: gorf-port

Gorf game pack + branded build of Breadbin-6502. The full project guide lives in the
workspace `CLAUDE.md` one level up (`../CLAUDE.md`). Read it first, especially:
**Workspace layout**, **Game pack format**, **ROM handling**, **Mod system**,
**Testing** and **Working conventions**.

Repo-specific rules:

- **Only Gorf-specific things live here:** `gamepacks/gorf/` (game.toml, art, later
  mods), docs, and the branded build. Anything a game needs from the launcher is added
  to `breadbin-6502` as a generic, config-driven option, released, and then adopted here.
- **The launcher is a submodule pinned to a tag** (`external/breadbin-6502`, currently
  `v0.5.1`). Update deliberately: check out the new tag, rebuild, run the game with the
  owner's dump, then commit the submodule bump. Keep `min_launcher_version` in
  `game.toml` honest; CMake refuses older launchers.
- **Never commit the ROM** or any game media (`.gitignore` covers `*.crt *.bin *.prg
  *.d64 *.g64 *.tap *.t64 roms/`). Artwork must be original: regenerate it with
  `tools/make_art.py`, don't add the game's art or logo.
- Verified facts (owner's dump "Gorf (USA, Europe).crt"): standard 16K cartridge,
  chip-data SHA-1 `4d24d5ed3d8b38235d9ae5965b675ffece0981cc`, joystick port 1, boots
  on the bundled Open ROMs, **NTSC** (owner compared both with `--ntsc`, Nov 2026).
- License: AGPL-3.0, matching the launcher.

Build: `cmake -S . -B build && cmake --build build && ctest --test-dir build`.
The executable is `build/gorf`.
