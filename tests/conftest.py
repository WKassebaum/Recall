"""
Test-suite guard rails.

WHY THIS FILE EXISTS
--------------------
On 2026-09-01 a full `pytest` run deleted the production Recall store: 1,505
memories, nine days unnoticed. Two integration fixtures built
``QdrantBackend(host="localhost", port=6333)`` and called ``delete_collection``
on the production names ``recall_384d`` / ``recall_768d`` / ``recall_1024d``,
each wrapped in ``except Exception: pass``. Run from the Windows VM, where
localhost:6333 is an SSH tunnel to the Mac's store, the suite passed and the
data was gone.

Three rules, enforced here so no individual test can opt out:

1. Integration and benchmark tests run only when ``RECALL_TEST_QDRANT_URL`` names a
   throwaway Qdrant. Unset, they are SKIPPED with the reason printed. They are
   also excluded from a bare ``pytest`` by the ``-m "not integration"`` default
   in pyproject; select them with ``pytest -m integration``.
2. Every ``QdrantBackend`` an integration test constructs in network mode is
   redirected to that URL, whatever host/port the test asked for. Embedded
   mode (``path=``) is left alone. A test cannot reach production by accident,
   because the thing it would connect with has been pointed elsewhere.
3. The test target may not sit on port 6333 (production on both machines)
   unless ``RECALL_TEST_ALLOW_PORT_6333=1`` is set deliberately.

Cleanup helpers here never swallow errors: a delete that fails for any reason
other than "collection does not exist" fails the test.

Start a throwaway instance for local runs, e.g.::

    qdrant --config-path /tmp/qdrant-test.yaml    # service.http_port: 6399
    RECALL_TEST_QDRANT_URL=http://127.0.0.1:6399 pytest -m integration
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

# Both of these talk to a live Qdrant. The benchmark harness ingests its corpus through
# load_config("config.yaml"), i.e. straight into the production store (10 chunks landed
# there during the guard's own first test run on 2026-09-10).
GUARDED_DIRS = (Path(__file__).parent / "integration", Path(__file__).parent / "benchmark")
ENV_URL = "RECALL_TEST_QDRANT_URL"
ENV_ALLOW_6333 = "RECALL_TEST_ALLOW_PORT_6333"
PRODUCTION_PORT = 6333


def _test_target() -> tuple[str, int] | None:
    raw = os.environ.get(ENV_URL, "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = "http://" + raw
    u = urlparse(raw)
    if not u.hostname or not u.port:
        raise pytest.UsageError(f"{ENV_URL} must look like http://host:port, got {raw!r}")
    if u.port == PRODUCTION_PORT and os.environ.get(ENV_ALLOW_6333) != "1":
        raise pytest.UsageError(
            f"{ENV_URL} points at port {PRODUCTION_PORT}, which is the production Recall store "
            f"on both machines. Start a throwaway Qdrant on another port, or set "
            f"{ENV_ALLOW_6333}=1 if you really mean it."
        )
    return u.hostname, u.port


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    target = _test_target()
    skip = pytest.mark.skip(
        reason=f"integration test: set {ENV_URL}=http://host:port to a THROWAWAY Qdrant "
        f"(never the production store) and run with -m integration"
    )
    for item in items:
        if any(d in Path(str(item.fspath)).parents for d in GUARDED_DIRS):
            item.add_marker(pytest.mark.integration)
            if target is None:
                item.add_marker(skip)


@pytest.fixture(autouse=True)
def _redirect_network_backends(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """For integration tests only: every network-mode QdrantBackend goes to the test target."""
    if not request.node.get_closest_marker("integration"):
        yield
        return
    target = _test_target()
    assert target is not None  # collection hook skipped us otherwise
    host, port = target

    from recall.backends import qdrant as qdrant_module

    original_init = qdrant_module.QdrantBackend.__init__

    def redirected_init(self, *args, **kwargs):
        # Signature: (host=None, port=6333, path=None). Positional use is rare but real.
        if len(args) >= 1:
            kwargs.setdefault("host", args[0])
        if len(args) >= 2:
            kwargs.setdefault("port", args[1])
        if len(args) >= 3:
            kwargs.setdefault("path", args[2])
        if kwargs.get("path"):
            return original_init(self, **kwargs)  # embedded mode: nothing to redirect
        kwargs["host"], kwargs["port"] = host, port
        return original_init(self, **kwargs)

    monkeypatch.setattr(qdrant_module.QdrantBackend, "__init__", redirected_init)
    yield


@pytest.fixture
def integration_backend():
    """A QdrantBackend on the throwaway test target (redirect makes the args irrelevant)."""
    from recall.backends.qdrant import QdrantBackend

    return QdrantBackend(host="test-target", port=0)


def drop_collections(backend, names) -> None:
    """Delete the named collections on the TEST backend. Missing is fine; any other
    failure raises, because a cleanup that cannot report failure is how the
    production store was lost."""
    for name in names:
        if backend.client.collection_exists(name):
            backend.client.delete_collection(collection_name=name)
