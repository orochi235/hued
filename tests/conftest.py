import pytest


@pytest.fixture(autouse=True)
def _own_cache(tmp_path, monkeypatch):
    """Keep the .hued index each test writes out of the real one."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / ".cache"))
