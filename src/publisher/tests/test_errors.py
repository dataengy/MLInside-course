"""errors: the field failures of this pipeline, each mapped to its unblocking action."""

import pytest

from publisher import errors, runner
from publisher import state as st


@pytest.mark.parametrize(
    ("raw", "needle"),
    [
        ("<HttpError 403 ...> The user's Drive storage quota has been exceeded.", "место, а не права"),
        ("RefreshError: ('invalid_grant: Bad Request')", "adc-login"),
        ("<HttpError 403> Request had insufficient authentication scopes.", "auth.scopes"),
        ("<HttpError 403> The caller does not have permission", "роль Редактор"),
        ("Google Drive API has not been used in project tg2gcal before", "quota_project"),
        ("The drive.googleapis.com API requires a quota project", "auth.quota_project"),
    ],
)
def test_known_failures_name_the_action(raw, needle):
    got = errors.explain(raw)
    assert needle in got
    assert raw in got, "the original message must survive for debugging"


def test_unknown_failure_passes_through_unchanged():
    assert errors.explain(ValueError("something new")) == "something new"


def test_leg_failures_are_recorded_explained(monkeypatch, tmp_path):
    """The hint must reach the leg state — that is what the operator and the plan block show."""
    quota = "<HttpError 403> The user's Drive storage quota has been exceeded."

    def boom(self, built, ds):
        raise RuntimeError(quota)

    monkeypatch.setattr(runner.Runner, "_leg_drive", boom)
    r = runner.Runner.__new__(runner.Runner)  # no config needed: only the drive leg runs
    r.cfg, r._services, r._sheet_ctx = None, {}, None
    built = runner.detect.BuiltDeck("D", tmp_path / "d.pptx", 1, 2, 0, "", "sig")
    ds = st.DeckState(version="1.2", slides=10)
    out = r.publish_one({}, built, ds, only={"drive"}, force=False)
    assert out.failed and "место, а не права" in ds.drive.error and quota in ds.drive.error
