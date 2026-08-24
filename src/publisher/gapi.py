"""publisher.gapi — every Google API call goes through here, with backoff on blips.

Google answers a healthy request with 503/500/429 now and then (seen live 2026-08-25: the
schedule sheet read failed, the immediate retry succeeded). Without a retry such a blip is
indistinguishable from a real failure: the leg is recorded `error` in the git-tracked
`published:` block and a whole run exits non-zero because a datacentre hiccuped.

``googleapiclient`` already implements randomized exponential backoff for exactly those
status codes — it just has to be asked, per call, via ``execute(num_retries=…)``. This
module is the one place that asks, so no call site can forget.

The count is configured once per process from ``settings/publish.yml → api.retries``
(``settings.load()`` applies it); tests set :data:`RETRIES` directly.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

DEFAULT_RETRIES = 4  # ≈15s of randomized exponential backoff; overridden from publish.yml
RETRIES = DEFAULT_RETRIES
BASE_DELAY = 0.5  # seconds; doubles per attempt in `call` (`run` uses the client's own backoff)
# Google's own "try again" set. 403/404 are NEVER here: those are policy, and retrying a
# quota or permission failure only delays the message that says what a human must fix.
TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})
_TRANSIENT_TEXT = (
    "backenderror",
    "internal error encountered",
    "service is currently unavailable",
    "the service is currently unavailable",
)


def set_retries(n: int | None) -> None:
    """Apply the configured count; ``None``/negative keeps the default.

    Read the value off the module (``g.RETRIES``), never as a bare name: a doctest runs
    against a *copy* of the module globals, so a bare ``RETRIES`` would show the stale one.

    >>> import publisher.gapi as g
    >>> set_retries(2); g.RETRIES
    2
    >>> set_retries(None); g.RETRIES
    4
    """
    global RETRIES
    RETRIES = DEFAULT_RETRIES if n is None or int(n) < 0 else int(n)


def run(request: Any) -> Any:
    """``request.execute()`` retried on transient 5xx/429."""
    return request.execute(num_retries=RETRIES)


def is_transient(exc: BaseException) -> bool:
    """A blip worth retrying — never a policy failure (403 quota / 404 / permissions).

    >>> is_transient(RuntimeError("<HttpError 503 ... The service is currently unavailable"))
    True
    >>> is_transient(RuntimeError("<HttpError 403 ... storage quota has been exceeded"))
    False
    """
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status is not None:
        return int(status) in TRANSIENT_STATUS
    low = str(exc).lower()
    if any(t in low for t in _TRANSIENT_TEXT):
        return True
    return any(f"httperror {s}" in low for s in TRANSIENT_STATUS)


def call(fn: Callable[..., Any], *args: Any, retries: int | None = None, **kwargs: Any) -> Any:
    """Retry a helper that executes internally (the hardlinked read-lane ``sheets.utils``).

    Same policy as :func:`run`, applied where ``num_retries`` cannot be passed down.
    """
    attempts = RETRIES if retries is None else retries
    for i in range(attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 — re-raised unless it is a known blip
            if i == attempts or not is_transient(e):
                raise
            time.sleep(BASE_DELAY * 2**i)
    raise AssertionError("unreachable")  # pragma: no cover
