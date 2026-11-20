# Step 2 pre-push review: Wire integrity, Trust boundary, supply chain

**Branch:** `phase1/godot-skeleton` at `aa5fcfa`, diff `origin/main...HEAD`. **Lens:** Wire integrity, Trust
boundary, and supply chain (charter `docs/code_review.md`). **Counts:** 0 BLOCKER, 4 SHOULD-FIX, 6 NIT.

**What I ran:** `.venv/bin/pytest -q tests/test_isolation.py` (42 passed); `scripts/check_lock.py` (PASS, py3.14,
0 differences); `git check-ignore` on `build/` and `client/.godot/` (both ignored). I did not run Godot, Docker or the
installer, and I did not recompute the Godot SHA-256s against the release assets (that needs network access). The
digests in `ci/godot.env` are taken on the author's word.

**What holds:** `ci/install_godot.sh` verifies the SHA-256 before `unzip`, and unzipping comes before the first exec.
`set -euo pipefail` stops the script on a mismatch. The URL is pinned to the `4.7.2-stable` release over https. After
install, the script refuses a binary whose `--version` is not the pin. The base image is pinned by digest. apt reads
from an https snapshot whose date is pinned, and the archive key still signs every index, so turning off peer
verification for the one bootstrap `update` costs no integrity. There is no `curl | sh`. `.dockerignore` limits the
build context to three files, and the repository is mounted read-only. pillow 13.0.0 is in both lockfiles. Every
Godot call goes through `godot_check.run_godot`, which puts HOME and the XDG directories in the work directory. The
gate's scratch directory is a `TemporaryDirectory` under the ignored `build/`, and the clean-gate test asserts that it
is removed.

## SHOULD-FIX

### S2W-S1: The JSON-read caveat is recorded only where step 7 will not look
`docs/design/client_rendering.md::Errata` and `docs/plans/checklists.md::Step 7`. The probe found that
`JSON.parse_string` turns every number into a float, so values above 2^53 lose precision. That fact lives only in
`docs/design/research/godot_probes.md` ("Step 7's decoder tests should hold both"). The step-2 errata block lists six
corrections and leaves this one out. §3 line 95 still says the int cast is "*to verify*". §4.1 and §12 say nothing
about reading. The step 7 checklist does carry "the `Origin` capture test", but it has nothing on int-on-read. Step 7
works from the checklist and §12.

**Failure scenario:** step 7's `net_client.gd` reads `tick`, `regions_version` or the cell frame's JSON header (offset
and size per array) and uses the values straight away. A float offset passed to `PackedByteArray.slice` gets coerced,
or trips the `unsafe_*` / `narrowing_conversion` warnings that are set to Error. Worse, an id or version compared with
`==` against an int-typed field fails without any message. Nothing here makes the step-7 author write the decoder
tests.

**Fix:** add an errata bullet for §3 and §4: encoding is confirmed (`int()` before `stringify`). Reading returns
floats. Every integer read from `tick` or a frame header is cast back with `int()`. Nothing on the JSON path exceeds
2^53. Add two bullets to the step 7 checklist. (a) Decoder fixtures with integer fields at 2^53 and at 2^53 + 1. The
decoder must refuse the second, or the spec must exclude it. (b) Server-side stage 1 refuses `5500.0` and `true`
where an integer is expected, because Python's `json.loads` yields `float` for the first, and `bool` is a subclass of
`int`.

### S2W-S2: B14 and B3 still say "Phase 1 step 2", and step 2 is landing now
`docs/standards_backlog.md::B14` (and `::B3`, "steps 2 and 4"). This branch rewrote the B6 and B7 rows and left these
two pointing at the step it closes. `docs/plans/foundations_plan.md` puts the token, the refusal of a handshake that
carries `Origin`, wire fixtures and B3/B14 in step 7.

**Failure scenario:** after merge, the trust-boundary row (the server refusing `Origin`, a wrong token, an oversized
message, a loopback-only bind) names a step that is already merged. Anyone reading the backlog can conclude that step
2 delivered it, or that it slipped without anyone noticing. This is the "silent deferral" that CLAUDE.md's first
principle forbids, applied to the main guard of "the client is untrusted input".

**Fix:** retarget B14 to "Phase 1 step 7 (`phase1/protocol`)". Retarget B3 to "steps 7 and 9" (protocol, then save),
or to whatever the current plan says. Check every other row with an old step number while you are in the file.

### S2W-S3: No check stops the next Godot call from running with the real HOME
`tests/test_isolation.py` (the B20 guard). The scan finds fixed temp paths, reads of HOME/TMPDIR, fixed ports, and git
calls outside `_gitutil.py`. Godot is a new kind of process that writes to HOME on its own: editor settings, a shader
cache, `godot.log`. The scan can't see that. Today isolation rests on one convention, routing every call through
`godot_check.run_godot`. `test_godot_keeps_its_per_user_files_in_the_home_it_is_given` shows that the log lands in the
given home. It doesn't show that the real home is left alone, and it doesn't stop a new call site.

**Failure scenario:** a step-8 test adds `subprocess.run([godot, "--path", ...])` to render a tile golden. The scan
passes it. Two sessions' gates now share `~/Library/Application Support/Godot/` (editor settings, the shader cache,
the log rotation) and race on it.

**Fix:** add a rule to the isolation scan. Any `subprocess.*` call in `tests/` or `scripts/` outside
`scripts/godot_check.py` must either pass `env=` or not reach Godot. The simplest version is "no subprocess call
outside an allowlist of modules". Prove the rule by deletion with a seeded fixture string, as the scan's other rules
are proved.

### S2W-S4: Player builds will ship `res://tests/` unless something says otherwise, and nothing records that
`client/tests/**` (probes, `run.gd`, `golden.tscn`/`golden.gd`, `test_context.gd`'s global `class_name`). There is no
`export_presets.cfg` yet, so no player build exists today. Godot's default export mode, "Export all resources",
includes every file under `res://`. That covers the WebSocket probe, which connects to a port taken from argv, and
`golden.gd`, which writes a PNG to a path taken from argv. A player who starts the binary with `--script` or a scene
path can reach them. I have not verified whether 4.7.2 release templates honour `-s`. Today this is hygiene and
attack surface, not an escalation, because the player already controls their own command line. It also puts test
code in the shipped product. No checklist, backlog row or errata entry records it.

**Failure scenario:** the first export step (Phase 1 exit, or the Steam build) copies the default preset, and the
tests and probes ship.

**Fix:** record it now as a known gap with a trigger. A row in the step that adds the first export preset: the preset
sets `exclude_filter="tests/*"`, and `tests/test_client_project.py` asserts that every preset in
`export_presets.cfg` excludes `tests/`.

## NIT

- **S2W-N1** `.github/workflows/golden.yml`: there is no `permissions:` block, so the default token permissions
  apply. The job needs none beyond reading contents. Add `permissions: {contents: read}`, as `drift.yml` declares its
  own. (`test.yml` has the same gap, from before this branch.)
- **S2W-N2** `.github/workflows/golden.yml`, `test.yml`, `drift.yml`: `actions/checkout@v4` and
  `actions/upload-artifact@v4` are pinned by a movable major tag, not by commit SHA. They are first-party actions and
  match existing practice, but a SHA pin is the supply-chain norm. Pin them, with the tag in a comment.
- **S2W-N3** `ci/godot-golden/Dockerfile::RUN ln -s "$(/opt/ci/install_godot.sh ...)"`: the command substitution's
  exit status is thrown away. Only `ln`'s status counts. A SHA mismatch fails the build today only because
  `ln -s "" path` happens to fail on Linux. Split it: `RUN godot="$(/opt/ci/install_godot.sh linux-x86_64
  /opt/godot)" && ln -s "$godot" /usr/local/bin/godot`.
- **S2W-N4** `ci/godot-golden/Dockerfile` (the `sed` on `ubuntu.sources`): if a future base image spells the URIs
  differently, `sed` matches nothing and apt quietly uses the live archive. The top-level packages are pinned by
  version, but their dependencies (libllvm, libdrm and others) would then float. After the `sed`, add
  `grep -q snapshot.ubuntu.com /etc/apt/sources.list.d/ubuntu.sources`.
- **S2W-N5** `ci/godot-golden/Dockerfile` (pip): `-c constraints/py3.12.txt` pins versions but not hashes, and it
  doesn't forbid sdists. A missing wheel would run a build backend inside the golden image. Add
  `--only-binary :all:`. Hash locking is a repo-wide question and belongs in O32, not here.
- **S2W-N6** `docs/design/research/godot_probes.md` ("Each probe that can be rerun is committed"): the Origin probe's
  other half, the Python listener that printed the handshake, is not committed. The upgrade branch can't rerun the
  probe as recorded. Either commit the listener in `client/tests/probes/` as a stdlib script on port 0, or say that
  step 7's listener test replaces it. Also, in `ci/install_godot.sh`, delete the zip on a SHA mismatch and use
  `curl --proto '=https'` so a redirect can't downgrade to http. Both are hygiene, because the SHA check already
  covers integrity.
