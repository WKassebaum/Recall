"""The guard in tests/conftest.py is itself under test: a guard nobody tests is
the thing that failed on 2026-09-01."""

import pytest

from tests import conftest as guard


def test_unset_means_no_target(monkeypatch):
    monkeypatch.delenv(guard.ENV_URL, raising=False)
    assert guard._test_target() is None


def test_production_port_refused(monkeypatch):
    monkeypatch.setenv(guard.ENV_URL, "http://127.0.0.1:6333")
    monkeypatch.delenv(guard.ENV_ALLOW_6333, raising=False)
    with pytest.raises(pytest.UsageError):
        guard._test_target()


def test_production_port_allowed_only_explicitly(monkeypatch):
    monkeypatch.setenv(guard.ENV_URL, "127.0.0.1:6333")
    monkeypatch.setenv(guard.ENV_ALLOW_6333, "1")
    assert guard._test_target() == ("127.0.0.1", 6333)


def test_throwaway_target_parsed(monkeypatch):
    monkeypatch.setenv(guard.ENV_URL, "http://localhost:6399")
    assert guard._test_target() == ("localhost", 6399)


def test_malformed_target_rejected(monkeypatch):
    monkeypatch.setenv(guard.ENV_URL, "http://nohost")
    with pytest.raises(pytest.UsageError):
        guard._test_target()
