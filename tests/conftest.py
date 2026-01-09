"""Shared pytest fixtures for the test suite."""

import pytest
from pathlib import Path


@pytest.fixture
def allow_tmp_dir(monkeypatch, tmp_path):
    """
    Allow pytest tmp_path for file reading tests.
    
    For backwards compatibility with tests that expect path validation.
    Note: Path validation has been removed from production code.
    """
    return tmp_path
