import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.squid import Squid
from lobstrio.models.task import Task, TaskStatus, AddTasksResult, UploadStatus, UploadMeta


runner = CliRunner()

SQUIDS = [
    Squid(
        id="squid1abc123def456", name="My Squid", crawler="c1",
        crawler_name="Google Maps", is_active=True, is_ready=True,
        concurrency=1, to_complete=None, last_run_status=None,
        last_run_at=None, total_runs=0, export_unique_results=False,
        params={},
    ),
]

FULL_TASK_HASH = "a" * 32


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client():
    mock = MagicMock()
    mock.squids.list.return_value = SQUIDS
    return mock


class TestTaskAdd:
    def test_add_tasks(self):
        mock = _mock_client()
        mock.tasks.add.return_value = AddTasksResult(
            tasks=[Task(id="t1", is_active=True, params={"url": "https://a.com"}, status=None, created_at=None),
                   Task(id="t2", is_active=True, params={"url": "https://b.com"}, status=None, created_at=None)],
            duplicated_count=0,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "add", "My Squid", "https://a.com", "https://b.com"])
        assert result.exit_code == 0
        assert "Added 2 tasks" in result.output

    def test_add_with_custom_key(self):
        mock = _mock_client()
        mock.tasks.add.return_value = AddTasksResult(
            tasks=[Task(id="t1", is_active=True, params={"keyword": "pizza nyc"}, status=None, created_at=None)],
            duplicated_count=0,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "add", "My Squid", "pizza nyc", "--key", "keyword"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="squid1abc123def456", tasks=[{"keyword": "pizza nyc"}])

    def test_add_with_duplicates(self):
        mock = _mock_client()
        mock.tasks.add.return_value = AddTasksResult(
            tasks=[Task(id="t1", is_active=True, params={}, status=None, created_at=None)],
            duplicated_count=3,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "add", "My Squid", "https://a.com"])
        assert result.exit_code == 0
        assert "3 duplicates" in result.output

    def test_add_json_mode(self):
        mock = _mock_client()
        mock.tasks.add.return_value = AddTasksResult(
            tasks=[Task(id="t1", is_active=True, params={}, status=None, created_at=None)],
            duplicated_count=0,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "task", "add", "My Squid", "https://a.com"])
        assert result.exit_code == 0


class TestTaskLs:
    def test_list_tasks(self):
        mock = _mock_client()
        mock.tasks.list.return_value = [
            Task(id=FULL_TASK_HASH, is_active=True, params={"url": "https://a.com"},
                 status=None, created_at="2025-01-01T00:00:00Z"),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "ls", "My Squid"])
        assert result.exit_code == 0
        assert "https://a.com" in result.output

    def test_list_tasks_pagination(self):
        mock = _mock_client()
        mock.tasks.list.return_value = []
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "ls", "My Squid", "--limit", "10", "--page", "3"])
        assert result.exit_code == 0


class TestTaskShow:
    def test_show_task(self):
        mock = _mock_client()
        mock.tasks.get.return_value = Task(
            id=FULL_TASK_HASH, is_active=True, params={"url": "https://example.com"},
            status=TaskStatus(status="done", total_results=42, total_pages=5,
                              done_reason="completed", has_errors=False),
            created_at="2025-01-01",
        )
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
        mock = _mock_client()
        mock.tasks.delete.return_value = {"id": FULL_TASK_HASH, "deleted": True}
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
        mock = _mock_client()
        mock.tasks.upload.return_value = {"id": "upload123"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "upload", "My Squid", str(csv_file)])
        assert result.exit_code == 0
        assert "upload123" in result.output


class TestTaskUploadStatus:
    def test_upload_status(self):
        mock = _mock_client()
        mock.tasks.upload_status.return_value = UploadStatus(
            state="completed",
            meta=UploadMeta(valid=100, inserted=95, duplicates=5, invalid=0),
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["task", "upload-status", "upload123"])
        assert result.exit_code == 0
        assert "95" in result.output
