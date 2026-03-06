import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state


runner = CliRunner()

SQUIDS = {
    "data": [
        {"id": "squid1abc123def456", "name": "My Squid"},
    ]
}

FULL_TASK_HASH = "a" * 32


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(get_resp=None, post_resp=None, delete_resp=None):
    mock = MagicMock()
    mock.get.side_effect = get_resp or (lambda path, **kw: SQUIDS)
    mock.post.return_value = post_resp or {}
    mock.delete.return_value = delete_resp or {}
    return mock


class TestTaskAdd:
    def test_add_tasks(self):
        mock = _mock_client(
            post_resp={"tasks": [{"id": "t1"}, {"id": "t2"}], "duplicated_count": 0}
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "add", "My Squid", "https://a.com", "https://b.com"])
        assert result.exit_code == 0
        assert "Added 2 tasks" in result.output

    def test_add_with_custom_key(self):
        mock = _mock_client(
            post_resp={"tasks": [{"id": "t1"}], "duplicated_count": 0}
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "add", "My Squid", "pizza nyc", "--key", "keyword"])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["tasks"] == [{"keyword": "pizza nyc"}]

    def test_add_with_duplicates(self):
        mock = _mock_client(
            post_resp={"tasks": [{"id": "t1"}], "duplicated_count": 3}
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "add", "My Squid", "https://a.com"])
        assert result.exit_code == 0
        assert "3 duplicates" in result.output

    def test_add_json_mode(self):
        mock = _mock_client(
            post_resp={"tasks": [{"id": "t1"}], "duplicated_count": 0}
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "task", "add", "My Squid", "https://a.com"])
        assert result.exit_code == 0


class TestTaskLs:
    def test_list_tasks(self):
        def get_resp(path, **kw):
            if path == "/squids":
                return SQUIDS
            return {"data": [
                {"id": FULL_TASK_HASH, "is_active": True, "params": {"url": "https://a.com"}, "created_at": "2025-01-01T00:00:00Z"},
            ]}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "ls", "My Squid"])
        assert result.exit_code == 0
        assert "https://a.com" in result.output

    def test_list_tasks_pagination(self):
        def get_resp(path, **kw):
            if path == "/squids":
                return SQUIDS
            return {"data": []}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "ls", "My Squid", "--limit", "10", "--page", "3"])
        assert result.exit_code == 0


class TestTaskShow:
    def test_show_task(self):
        def get_resp(path, **kw):
            return {
                "hash_value": FULL_TASK_HASH,
                "is_active": True,
                "status": {"status": "done", "total_results": 42, "total_pages": 5,
                           "done_reason": "completed", "has_errors": False},
                "params": {"url": "https://example.com"},
            }
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "show", FULL_TASK_HASH])
        assert result.exit_code == 0
        assert "42" in result.output

    def test_show_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "show", "abc123"])
        assert result.exit_code != 0


class TestTaskRm:
    def test_delete_task(self):
        mock = _mock_client(delete_resp={"id": FULL_TASK_HASH, "deleted": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "rm", FULL_TASK_HASH])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "rm", "short"])
        assert result.exit_code != 0


class TestTaskUpload:
    def test_upload_tasks(self, tmp_path):
        csv_file = tmp_path / "tasks.csv"
        csv_file.write_text("url\nhttps://a.com\nhttps://b.com\n")
        mock = _mock_client(post_resp={"id": "upload123"})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "upload", "My Squid", str(csv_file)])
        assert result.exit_code == 0
        assert "upload123" in result.output


class TestTaskUploadStatus:
    def test_upload_status(self):
        def get_resp(path, **kw):
            return {
                "state": "completed",
                "meta": {"valid": 100, "inserted": 95, "duplicates": 5, "invalid": 0},
            }
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "upload-status", "upload123"])
        assert result.exit_code == 0
        assert "95" in result.output
