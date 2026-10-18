import subprocess
import sys
from threading import Event

import pytest

from sage.runtime.dependency_verifier import DependencyRejected, DependencyVerifier
from sage.runtime.flownet.runtime.operator_runtime.stateful import (
    StatefulProcessRuntime,
)


@pytest.fixture
def store(tmp_path):
    instance = StatefulProcessRuntime(backend="sqlite", sqlite_path=str(tmp_path / "state.db"))
    yield instance
    instance.close()


def verifier(store, probe):
    return DependencyVerifier(store, name="integration", probe=probe,
                              retry_delay=0.01, max_retry_delay=0.02, poll_interval=0.01)


def finished(instance):
    return instance._work.wait(instance._binding, timeout=5)


def test_start_returns_while_probe_blocked_and_close_drains(store):
    entered, release = Event(), Event()

    def probe():
        entered.set()
        assert release.wait(5)
        return True

    instance = verifier(store, probe)
    try:
        assert instance.status() == {"state": "not_started"}
        instance.start()
        assert entered.wait(3)
        assert instance.status() == {"state": "pending"}
        assert not instance.ready()
        with pytest.raises(TimeoutError, match="drain_timeout"):
            instance.close(timeout=0)
        assert not instance.ready()
        assert store.peek(instance._slot)["state"] == "pending"
    finally:
        release.set()
        instance.close()
    assert store.peek(instance._slot)["state"] == "verified"
    assert instance.status() == {"state": "closed"}


def test_transient_failure_recovers_without_persisting_error_or_credentials(store):
    attempts = []

    def probe():
        attempts.append(True)
        if len(attempts) == 1:
            raise OSError("secret-not-to-persist DNS unavailable")
        return True

    instance = verifier(store, probe)
    try:
        instance.start()
        record = finished(instance)
        assert record["tasks"]["verify"]["attempt"] == 2
        assert instance.ready()
        assert "secret-not-to-persist" not in repr(record)
        assert "DNS unavailable" not in repr(record)
        assert set(store.peek(instance._slot)) == {"binding", "state"}
        instance.start()
        assert len(attempts) == 2
    finally:
        instance.close()


@pytest.mark.parametrize("response", [False, None, {}, "True", 1])
def test_only_exact_true_can_verify(store, response):
    instance = verifier(store, lambda: response)
    try:
        instance.start()
        assert finished(instance)["tasks"]["verify"]["attempt"] == 1
        assert instance.status() == {"state": "rejected"}
        assert not instance.ready()
    finally:
        instance.close()


def test_permanent_rejection_is_not_retried_or_leaked(store):
    def reject():
        raise DependencyRejected("private workspace identifier")

    instance = verifier(store, reject)
    try:
        instance.start()
        record = finished(instance)
        assert record["tasks"]["verify"]["result"] == "rejected"
        assert record["tasks"]["verify"]["attempt"] == 1
        assert "private workspace" not in repr(record)
        assert not instance.ready()
    finally:
        instance.close()


def test_restart_never_trusts_historical_success(store):
    first = verifier(store, lambda: True)
    first.start()
    finished(first)
    assert first.ready()
    first.close()
    entered, release = Event(), Event()

    def new_probe():
        entered.set()
        assert release.wait(5)
        return False

    second = verifier(store, new_probe)
    try:
        assert not second.ready()
        second.start()
        assert entered.wait(3)
        assert not second.ready()
        release.set()
        finished(second)
        assert second.status() == {"state": "rejected"}
    finally:
        release.set()
        second.close()


def test_superseded_inflight_success_cannot_unlock_replacement(store):
    entered, release = Event(), Event()

    def old_probe():
        entered.set()
        assert release.wait(5)
        return True

    first = verifier(store, old_probe)
    first.start()
    assert entered.wait(3)
    second = verifier(store, lambda: False)
    try:
        second.start()
        finished(second)
        assert second.status() == {"state": "rejected"}
        release.set()
        first.close()
        task = first.journal.read(first._binding)["tasks"]["verify"]
        assert task["status"] == "failed"
        assert task["failure_code"] == "request_cancelled"
        assert not first.ready()
        assert second.status() == {"state": "rejected"}
    finally:
        release.set()
        first.close()
        second.close()


def test_lost_registration_ack_replays_without_resetting_state(store, monkeypatch):
    instance = verifier(store, lambda: True)
    commit = instance.journal.commit

    def lost_ack(*args, **kwargs):
        commit(*args, **kwargs)
        raise OSError("lost acknowledgement")

    try:
        monkeypatch.setattr(instance.journal, "commit", lost_ack)
        with pytest.raises(OSError, match="lost acknowledgement"):
            instance.start()
        assert not instance.ready()
        monkeypatch.setattr(instance.journal, "commit", commit)
        instance.start()
        finished(instance)
        assert instance.ready()
        instance.start()
        assert instance.ready()
    finally:
        instance.close()


def test_delayed_registration_cannot_overwrite_newer_binding(store):
    delayed = verifier(store, lambda: True)
    newer = verifier(store, lambda: False)
    try:
        newer.start()
        finished(newer)
        with pytest.raises(RuntimeError, match="binding_superseded"):
            delayed.start()
        assert delayed.journal.read(delayed._binding) is None
        assert not delayed.ready()
        assert newer.status() == {"state": "rejected"}
    finally:
        delayed.close()
        newer.close()


def test_process_death_after_pending_commit_requires_new_probe(tmp_path):
    path = str(tmp_path / "crash.db")
    script = """
import os, sys
from sage.runtime.dependency_verifier import DependencyVerifier
from sage.runtime.flownet.runtime.operator_runtime.stateful import StatefulProcessRuntime
store = StatefulProcessRuntime(backend="sqlite", sqlite_path=sys.argv[1])
instance = DependencyVerifier(store, name="integration", probe=lambda: True)
instance._work.start = lambda: os._exit(37)
instance.start()
"""
    result = subprocess.run([sys.executable, "-c", script, path], check=False, timeout=10)
    assert result.returncode == 37
    store = StatefulProcessRuntime(backend="sqlite", sqlite_path=path)
    entered, release = Event(), Event()

    def probe():
        entered.set()
        assert release.wait(5)
        return True

    instance = verifier(store, probe)
    old_binding = store.peek(instance._slot)["binding"]
    try:
        assert not instance.ready()
        instance.start()
        assert entered.wait(3)
        old_task = instance.journal.read(old_binding)["tasks"]["verify"]
        assert old_task["status"] == "failed"
        assert old_task["failure_code"] == "request_cancelled"
        assert not instance.ready()
        release.set()
        finished(instance)
        assert instance.ready()
    finally:
        release.set()
        instance.close()
        store.close()
