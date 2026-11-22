# The vertical slice (throwaway)

A prototype lane, not the engine: `docs/plans/vertical_slice.md` says what it is for and what is relaxed. Nothing here
is the real step 5b, 7 or 8, and nothing under `src/` changes for it.

## Run it

From the worktree root, with the worktree's own `.venv` (`CLAUDE.md`, Commands):

1. **Once per checkout, import the Godot project.** Godot keeps its import cache (`godot/.godot/`) out of git, and
   without it the scripts' class names (`SliceNet`, `SliceVoxels`) don't resolve and the client won't load:
   `Godot --headless --path spikes/slice/godot --import`
2. **The model, for the vendor's voice:** Ollama serving `qwen2.5:3b` on 127.0.0.1:11434 (`ollama pull qwen2.5:3b`).
   Without it, or with `--no-llm`, the vendor speaks canned lines.
3. **The server:** `cd spikes/slice && ../../.venv/bin/python -m slice_server serve`. It writes this launch's port and
   token to `run/session.json` and its session log to `sessions/`. Ctrl-C stops it between ticks.
4. **The client:** `Godot --path spikes/slice/godot`. WASD to move (relative to the camera), Shift for Overdrive,
   F to kindle, Space to strike, Enter to talk to the vendor, Q/E to orbit, H for the heat view.

`-- --demo` walks to the crate and kindles it (counted in server ticks); `-- --capture=<png> --frames=<n>` saves a
frame and quits.

## Check a session

`../../.venv/bin/python -m slice_server replay sessions/<file>.jsonl` reruns its intents and compares the final digest.
`../../.venv/bin/python -m slice_server metrics sessions/<file>.jsonl` replays it and prints the playtest numbers
(Overdrive seconds per minute, trips, puddle time, fires, the vendor's states, voice and budget); `--json` for the raw
numbers. It exits non-zero, and says so, when the replay doesn't match the recorded end.
The tests: `../../.venv/bin/pytest tests` from `spikes/slice`.

## Playtests

On the Mac mini (owner, 2026-11-21), with the player at its own keyboard and screen: everything local there, the
server bound to 127.0.0.1. Not over Screen Sharing, whose input lag would change the feel being judged. Before each
session, restart the server so the world starts fresh, and keep the session log for the verdict note.
