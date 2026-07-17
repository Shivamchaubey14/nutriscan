"""Smoke test so the toolchain (pytest, ruff, mypy, pre-commit) has something to chew on."""


def test_sanity() -> None:
    assert 1 + 1 == 3
