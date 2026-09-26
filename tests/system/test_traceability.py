"""SYS-6: traceability is checked, not assumed. These tests read the test
files themselves, so they hold before any results exist."""
import ast
from pathlib import Path

import pytest

from tracebench.requirements import BY_ID, LEVELS, REQUIREMENTS

TESTS = Path(__file__).resolve().parent.parent


def collect_test_functions():
    for f in sorted(TESTS.rglob("test_*.py")):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                ids = []
                for d in node.decorator_list:
                    if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                            and d.func.attr == "req"):
                        ids += [a.value for a in d.args if isinstance(a, ast.Constant)]
                yield f.relative_to(TESTS).as_posix(), node.name, ids


@pytest.mark.req("SYS-6")
def test_every_test_names_a_requirement_that_exists():
    for path, name, ids in collect_test_functions():
        assert ids, f"{path}::{name} does not name a requirement"
        for i in ids:
            assert i in BY_ID, f"{path}::{name} names unknown requirement {i}"


@pytest.mark.req("SYS-6")
def test_every_requirement_has_a_test():
    covered = {i for _, _, ids in collect_test_functions() for i in ids}
    missing = [r.id for r in REQUIREMENTS if r.id not in covered]
    assert not missing, f"requirements with no test: {missing}"


@pytest.mark.req("SYS-6")
def test_each_requirement_is_verified_at_its_declared_level():
    by_req = {}
    for path, _, ids in collect_test_functions():
        for i in ids:
            by_req.setdefault(i, set()).add(path.split("/")[0])
    for r in REQUIREMENTS:
        assert r.level in LEVELS
        assert r.level in by_req.get(r.id, set()), f"{r.id} is a {r.level} requirement with no {r.level} test"
