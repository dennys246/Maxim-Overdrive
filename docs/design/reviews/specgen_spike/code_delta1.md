# Spec generator spike, code delta 1 (2026-11-22)

A condensed record of one independent reader's hand-back on the fold of code round 1 (`code1_protocol.md`,
`code1_exec_determinism.md`), read from the uncommitted tree on top of 20ebc44.

**What the reader ran:**
- the 61 spike tests, which pass;
- `mypy --strict`, clean;
- 25 single mutations, of which 22 went red;
- B1 measured directly: the decision was identical with 92 extra records scored first, Δ = −0.0761, [−0.2174, 0.0543];
- bash tests of the window at hours 21, 22, 23, 00, 07, 08 and 09, and of the EXIT trap under SIGTERM.

**The reader's statuses:**
- **Fixed:**
  - in `code1_protocol.md`: BLOCKER 1 and SF1 to SF7, plus NITs 2, 3 and 5 to 9;
  - in `code1_exec_determinism.md`: B1, S1, S2, S4, S5, S6 and S9, plus N1, N3 and N4.
- **Open by choice:** protocol NIT 1 (unsent samplers left at the pinned build's defaults) and NIT 4 (renamed
  `mean_of_specs`), and exec N2 (a dead branch).
- **Open by design:** S3's generator half. A sample that always fails stops the run, per E14.
- **Tests exist but weren't mutation-checked:** S7 and S8.
- **E10 to E17** are true of the frozen text and the code. They are the author's readings until the owner confirms
  them.

**Findings:**
- **BLOCKER 1, `run_window.sh`:** the server's log redirect wrote llama-server's listening line (the Tailscale address)
  and the model's full path (the home directory) into a file, against `arms.yaml`'s "never written".
- **SHOULD-FIX 1:** the resume keys include the spike tree and HEAD, so any commit or edit on the mini between nights
  refuses every later resume. S takes several nights. Commit first, run from that commit, and leave the checkout alone
  until R finishes.
- **SHOULD-FIX 2:** under `set -e`, a failing cell ends the script without saying which cell.
- **SHOULD-FIX 3:** the malformed-middle-line refusal had no test.
- **NIT:**
  - `in_window` is wrong when the window doesn't cross midnight;
  - no `caffeinate`;
  - the EXIT trap doesn't kill the generator;
  - `repair_tail` truncates before the header is checked;
  - add an n_ctx 32768 case;
  - an unknown sheet id raises KeyError;
  - a cell with no samples is never "short";
  - the errata's E-order.

**The verdict:** the generator is safe to run S tonight once BLOCKER 1 is fixed and everything is committed.

## The author's folds (author's claims)

- **BLOCKER 1:** the server's output passes through a `sed` mask that replaces the address and `$HOME` before it
  reaches the log. Tested on the mini's bash 3.2 with a made-up address: both masked, and a look-alike string left
  alone. On the mini, two earlier probe logs (bound to loopback) did carry a listening line and a home path.
- **SHOULD-FIX 1:** everything is committed before the run. The mini's checkout is fast-forwarded once and not touched
  until R finishes.
- **SHOULD-FIX 2:** a failing cell prints its model, arm and split, then stops.
- **SHOULD-FIX 3:** a test corrupts line 2; making the code skip it instead turns the test red.
- **NITs:**
  - `in_window` handles a window that doesn't cross midnight;
  - the n_ctx 32768 case was added, and weakening `!=` to `<` turns it red;
  - `caffeinate` isn't needed, because the mini's `pmset` reads `sleep 0`;
  - the others are left for after the run.
