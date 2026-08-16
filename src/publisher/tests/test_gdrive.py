"""gdrive: update-not-create / adopt-by-name / 404 fallback, against a mocked service."""

from unittest.mock import ANY, MagicMock

import pytest

from publisher import gdrive

googleapiclient = pytest.importorskip("googleapiclient")  # tests build real HttpError objects


def _http_error(status: int):
    import httplib2
    from googleapiclient.errors import HttpError

    return HttpError(resp=httplib2.Response({"status": status}), content=b"gone")


@pytest.fixture()
def pptx(tmp_path):
    p = tmp_path / "MLInside_X_v1.2.pptx"
    p.write_bytes(b"pptx-bytes")
    return p


def _service(update_result=None, list_files=None, perms=None):
    svc = MagicMock()
    svc.files().update().execute.return_value = update_result or {"id": "F1", "webViewLink": "https://v/F1"}
    svc.files().create().execute.return_value = {"id": "NEW", "webViewLink": "https://v/NEW"}
    svc.files().list().execute.return_value = {"files": list_files or []}
    svc.permissions().list().execute.return_value = {"permissions": perms or []}
    svc.files.reset_mock()
    svc.permissions.reset_mock()
    return svc


def test_known_id_updates_in_place(pptx):
    svc = _service()
    res = gdrive.upload_or_update(
        svc, file_path=pptx, folder_id="D", filename="MLInside_X.pptx",
        description="v1.2", existing_file_id="F1",
    )
    assert res.file_id == "F1" and res.web_view_link == "https://v/F1"
    svc.files().update.assert_called_once_with(
        fileId="F1", body={"name": "MLInside_X.pptx", "description": "v1.2"},
        media_body=ANY, fields="id,webViewLink",
    )
    svc.files().create.assert_not_called()


def test_lost_cursor_adopts_by_name_never_duplicates(pptx):
    svc = _service(list_files=[{"id": "F1", "name": "MLInside_X.pptx"}])
    res = gdrive.upload_or_update(
        svc, file_path=pptx, folder_id="D", filename="MLInside_X.pptx",
        description="v1.2", existing_file_id=None,
    )
    assert res.file_id == "F1"
    svc.files().create.assert_not_called()
    q = svc.files().list.call_args.kwargs["q"]
    assert "name = 'MLInside_X.pptx'" in q and "'D' in parents" in q and "trashed = false" in q


def test_first_publish_creates_in_folder_and_shares(pptx):
    svc = _service()
    res = gdrive.upload_or_update(
        svc, file_path=pptx, folder_id="D", filename="MLInside_X.pptx",
        description="v1.2", existing_file_id=None,
    )
    assert res.file_id == "NEW"
    body = svc.files().create.call_args.kwargs["body"]
    assert body["parents"] == ["D"]
    svc.permissions().create.assert_called_once_with(
        fileId="NEW", body={"type": "anyone", "role": "reader"}
    )


def test_stale_id_404_falls_back_to_name(pptx):
    svc = _service(list_files=[{"id": "F2", "name": "MLInside_X.pptx"}])
    svc.files().update().execute.side_effect = [_http_error(404), {"id": "F2", "webViewLink": "https://v/F2"}]
    res = gdrive.upload_or_update(
        svc, file_path=pptx, folder_id="D", filename="MLInside_X.pptx",
        description="v1.2", existing_file_id="GONE",
    )
    assert res.file_id == "F2"
    svc.files().create.assert_not_called()


def test_non_404_errors_propagate(pptx):
    svc = _service()
    svc.files().update().execute.side_effect = _http_error(403)
    with pytest.raises(Exception, match="403|gone|HttpError"):
        gdrive.upload_or_update(
            svc, file_path=pptx, folder_id="D", filename="X.pptx",
            description="v", existing_file_id="F1",
        )


def test_ensure_shared_is_idempotent():
    svc = _service(perms=[{"type": "anyone", "role": "reader"}])
    gdrive.ensure_shared(svc, "F1", "anyone_reader")
    svc.permissions().create.assert_not_called()
    gdrive.ensure_shared(svc, "F1", "none")
    svc.permissions().list.assert_called_once()  # only the first call listed


def test_ensure_folder_search_then_create():
    svc = _service(list_files=[{"id": "D1", "name": "Decks"}])
    assert gdrive.ensure_folder(svc, name="Decks", parent_id="root") == "D1"
    svc = _service()
    svc.files().create().execute.return_value = {"id": "D2"}
    assert gdrive.ensure_folder(svc, name="Decks", parent_id="root") == "D2"
    body = svc.files().create.call_args.kwargs["body"]
    assert body["mimeType"] == gdrive.FOLDER_MIME
