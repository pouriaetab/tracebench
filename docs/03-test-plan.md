# 3. Test plan

## Scope

Items under test: the data loader (`bars.py`), the touch definition (`levels.py`),
the three models (`models/reach.py`, `models/strength.py`, `models/magnitude.py`),
the replay harness (`replay.py`) and the V&V runner itself (`report.py`,
`trace.py`). Out of scope: live data feeds, user interfaces, execution.

## Approach by level

| Level | Folder | Approach | Typical size |
|:--|:--|:--|:--|
| Unit | `tests/unit` | Exact values, properties that must always hold, boundary and invalid inputs | milliseconds each |
| Integration | `tests/integration` | Real files through the loader, the model inside replay, records recomputed from themselves | under a second |
| System | `tests/system` | The runner's verdicts, reproducibility, traceability completeness | seconds |
| Validation | `tests/validation` | Seeded scenarios with known truth; thresholds from the requirements | about 10 seconds in total |

## Techniques used, and where

1. **Boundary and invalid input** (equivalence classes): `test_invalid_inputs_give_no_answer`, `test_bad_row_is_rejected_with_its_reason`.
2. **Property-based checks**: probability falls with distance, survival never rises, symmetric touch definition.
3. **Differential and inverse checks**: quantile against tail probability; each replay record recomputed from its own fields.
4. **Metamorphic testing**: transform the input in a way whose effect on the output is known (mirror the price series; change only the future) and check the output moved exactly as expected.
5. **Control tests**: `test_outcomes_do_use_the_future` proves the no lookahead test is able to fail.
6. **Known truth validation**: simulated markets and samples whose parameters are set by the test.
7. **Regression tests** for every defect found (TB-1).

## Entry and exit criteria

Entry: the package imports and `pytest` is installed. If not, the runner reports
**ENVIRONMENT ERROR** (SYS-5) and no verdict about the product.

Exit (release): verdict PASS, meaning no failed test, every requirement VERIFIED
or carrying a recorded known issue, and no requirement NOT TESTED (SYS-6).

## Pass and fail rules

1. A test passes or fails; there is no "mostly passed".
2. An expected failure (`xfail`) must be `strict`: if a known issue starts passing,
   the suite fails, so the record is updated instead of going stale.
3. A known issue needs an id, a reason, and an entry in the issue register.

## Environments

Local: Python 3.10 or newer, `pip install -e ".[test]"`. CI: GitHub Actions on
every push and pull request, Python 3.10 and 3.12
(`.github/workflows/vv.yml`), with the reports uploaded as an artifact.

## Regression

The whole suite is the regression suite. It runs on every change in CI. Validation
studies are seeded, so a change in any reported number is a real change in behaviour.
