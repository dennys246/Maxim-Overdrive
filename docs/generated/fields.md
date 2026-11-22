# Field registry (generated)

Generated from `src/simcore/core/fields.py` by `simcore.core.fields.render()`; `tests/test_fields.py`
compares it byte for byte. Edit the code, never this file. The contract is `docs/design/sim_core.md` §6.

| Field | dtype | units | container | saved | digested | writers, in order |
|---|---|---|---|---|---|---|
| `material` | uint8 | material id | cells | yes | yes | topology, construction |
| `original_material` | uint8 | material id | cells | yes | yes | topology, construction |
| `integrity` | float32 | 1 | cells | yes | yes | damage.loads, damage.thermal, topology, construction |
| `temperature` | float64 | degC | cells | yes | yes | heat, construction |
| `regions` | region table | - | table | yes | yes | topology, construction |

| Input | appended by | resolved by |
|---|---|---|
| `sources` | applier | heat |
| `loads` | applier | damage.loads |
