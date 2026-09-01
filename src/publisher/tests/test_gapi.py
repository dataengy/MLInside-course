"""gapi: blips are retried, policy failures are not (no sleeping, no network)."""

import pytest

from publisher import gapi


class _Resp:
    def __init__(self, status):
        self.status = status


def _http_error(status, msg="boom"):
    e = RuntimeError(f"<HttpError {status} ... {msg}>")
    e.resp = _Resp(status)  # ty: ignore[unresolved-attribute]  # форма HttpError
    return e


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(gapi.time, "sleep", lambda _s: None)


@pytest.fixture(autouse=True)
def _restore_retries():
    before = gapi.RETRIES
    yield
    gapi.RETRIES = before


@pytest.mark.parametrize("status", sorted(gapi.TRANSIENT_STATUS))
def test_transient_statuses_are_retried(status):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise _http_error(status)
        return "ok"

    gapi.set_retries(4)
    assert gapi.call(flaky) == "ok"
    assert len(calls) == 3


@pytest.mark.parametrize("status", [403, 404, 401])
def test_policy_failures_fail_immediately(status):
    """Retrying a quota/permission failure only delays the message that names the fix."""
    calls = []

    def denied():
        calls.append(1)
        raise _http_error(status, "storage quota has been exceeded")

    with pytest.raises(RuntimeError):
        gapi.call(denied)
    assert len(calls) == 1


def test_exhausted_retries_reraise_the_original():
    calls = []

    def always_503():
        calls.append(1)
        raise _http_error(503)

    gapi.set_retries(2)
    with pytest.raises(RuntimeError, match="503"):
        gapi.call(always_503)
    assert len(calls) == 3  # initial attempt + 2 retries


def test_transient_detected_without_a_resp_object():
    """Errors that reach us as plain text (wrapped/re-raised) must still be recognised."""
    assert gapi.is_transient(RuntimeError("<HttpError 503> The service is currently unavailable"))
    assert gapi.is_transient(RuntimeError("Internal error encountered"))
    assert not gapi.is_transient(RuntimeError("<HttpError 403> insufficient permissions"))


def test_run_passes_the_configured_retry_count():
    seen = {}

    class Req:
        def execute(self, num_retries=0):
            seen["n"] = num_retries
            return "done"

    gapi.set_retries(7)
    assert gapi.run(Req()) == "done" and seen == {"n": 7}
