# Delta round 4, step 3b(a): Executor and Wire integrity

**Range:** `git diff d9b22d8 3b0918a`.

**Method:** a `git archive 3b0918a` copy with the worktree's venv. The unmutated baseline is green: corpus,
planted-import tests, contract-shape test and knife-edge test (166 tests). Harness:
`_durable/3b_review/delta4_mutate.py`.

## Status of N-f: fixed

The knife-edge test now also asserts `mask.sum() == (20 if r**2 != r*r else 24)`. Two mutations prove it:

- **`r*r` in `Cylinder.mask`:** red.
- **Cell centres shifted by 1e-9 m:** red. The mask and the test's expected array both come from `g.mesh()`, so only
  the new count assertion can see this. The count has teeth of its own.

B28 records the real fix, voxelizing by volume overlap, with a trigger.

## Can the new tests fail?

### Planted-import tests

Yes. Dropping one family from `input-primitives` turned that family's row red each time:

| family dropped | red |
|---|---|
| `pathlib` | the encoding row, plus `test_only_the_file_gates_read_input_or_decode`, plus a corpus row |
| `urllib` | the `data.py` row, plus a corpus row |
| `subprocess` | the tiers row |
| `asyncio` | the encoding row, plus a corpus row |
| `posix` | the bridge row, plus a corpus row |

**The gate's extra import (`loaders -> importlib`):** adding that ignore turned 10 tests red, but broadly.
import-linter refuses an ignore line that matches no import, so every planted case failed its baseline check.
`test_only_the_file_gates_read_input_or_decode` (`ignore_imports == GATE_IMPORTS`) holds the row specifically.

### The corpus's joint contract-plus-lint check

Yes:

- **`sqlite3` or `pkgutil` removed from the contract:** only that row went red. The joint judge is their only guard,
  and it works.
- **The fixture's contract regex broken:** 40 rows went red. So the rows really depend on the gate's import command,
  not on the lint alone.
- **The `NOT_COVERED` rows:** they would catch an unannounced gain, not a loss. That is their stated purpose.

## New findings: 1 SHOULD-FIX

### S-d. `pyproject.toml::input-primitives` + `scripts/lint_inputs.py`: a module with a `pathlib` ignore can read files undetected

The rewrite dropped the lint's method rule (`.read_text`, `.read_bytes`, `.open`, `.recv` on anything). The contract
now carries the rule for modules, but `simcore.protocol.tiers` and `maxim_overdrive.data` are allowed `pathlib` by an
ignore line. The ignore's comment says tiers "opens nothing itself", which is kept by luck.

**Proof:** I appended this to the copy's `src/simcore/protocol/tiers.py`:

```python
def sneak(path: Path) -> str:
    return Path(path).read_text()
```

`input_findings` returned `[]` and `lint-imports` reported "8 kept, 0 broken". d9b22d8's lint flagged the same
spelling ("calls .read_text()").

The engine-wide case (`def f(p): p.read_text()` anywhere in `src/`) is also unflagged now. It is recorded in
`NOT_COVERED` as a design choice, so I note it but don't score it.

**Fix:** flag the path-reading methods (`read_text`, `read_bytes`, `open`, `iterdir`, `glob`) at least in the modules
that hold a `pathlib` ignore. The old blanket method rule had no false positives on the repository. Pin `sneak` in the
corpus as flagged.

## Wire integrity

| Contract | Change | Consumers | Effect |
|---|---|---|---|
| `input-primitives` | 5 → 50 forbidden modules; 4 ignores | `lint-imports` | The repository still passes. A future `os`, `sys` or `io` import in `simcore` or `maxim_overdrive` (logging, argv) is now a contract break by design. |
| `lint_inputs` scope | narrowed to builtins, numpy IO and decoders | `check_inputs`, the corpus | Method reads on handed-in objects are unseen (S-d). |
| CLAUDE.md guard | cites `test_only_the_file_gates_read_input_or_decode` | `lint_guards` | The cited test goes red when the contract is weakened (shown above). |
| `Cylinder.mask` | comment only | — | Cells unchanged. |
