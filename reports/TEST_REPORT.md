# Test report

**Verdict: PASS**

| Level | Passed | Failed | Known issue (xfail) | Other |
|:--|--:|--:|--:|--:|
| unit | 55 | 0 | 0 | 0 |
| integration | 6 | 0 | 0 | 0 |
| system | 16 | 0 | 0 | 0 |
| validation | 12 | 0 | 1 | 0 |

## Known issues (accepted deviations)

- `tests/validation/test_strength_validation.py::test_false_alarm_rate_at_inherited_threshold`: KI-1: the inherited 0.75 threshold labels 19-27% of unchanged levels as strengthening; replaced by 0.95 (CR-1)
