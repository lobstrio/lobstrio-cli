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

FULL_RUN_HASH = "b" * 32


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(get_resp=None, post_resp=None):
    mock = MagicMock()
    mock.get.side_effect = get_resp or (lambda path, **kw: SQUIDS)
    mock.post.return_value = post_resp or {"id": FULL_RUN_HASH}
    mock.download.return_value = None
    return mock


class TestRunStart:
    def test_start_run(self):
        mock = _mock_client(post_resp={"id": FULL_RUN_HASH, "status": "running"})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "start", "My Squid"])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_start_json_mode(self):
        mock = _mock_client(post_resp={"id": FULL_RUN_HASH, "status": "running"})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "run", "start", "My Squid"])
        assert result.exit_code == 0
        assert FULL_RUN_HASH in result.output


class TestRunLs:
    def test_list_runs(self):
        def get_resp(path, **kw):
            if path == "/squids":
                return SQUIDS
            return {"data": [
                {"id": FULL_RUN_HASH, "status": "finished", "total_results": 100,
                 "duration": 120.5, "credit_used": 50, "done_reason": "completed"},
            ]}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "ls", "My Squid"])
        assert result.exit_code == 0
        assert "finis" in result.output

    def test_list_runs_duration_formatting(self):
        def get_resp(path, **kw):
            if path == "/squids":
                return SQUIDS
            return {"data": [
                {"id": FULL_RUN_HASH, "status": "finished", "total_results": 0,
                 "duration": None, "credit_used": 0, "done_reason": None},
            ]}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "ls", "My Squid"])
        assert result.exit_code == 0


class TestRunShow:
    def test_show_run(self):
        def get_resp(path, **kw):
            return {
                "id": FULL_RUN_HASH,
                "status": "finished",
                "total_results": 100,
                "total_unique_results": 95,
                "duration": 120,
                "credit_used": 50,
                "origin": "api",
                "done_reason": "completed",
                "done_reason_desc": None,
                "export_done": True,
                "started_at": "2025-01-01T00:00:00Z",
                "ended_at": "2025-01-01T00:02:00Z",
            }
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "show", FULL_RUN_HASH])
        assert result.exit_code == 0
        assert "finished" in result.output

    def test_show_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "show", "abc123"])
        assert result.exit_code != 0


class TestRunStats:
    def test_run_stats(self):
        def get_resp(path, **kw):
            return {
                "percent_done": "100%",
                "total_tasks_done": 10,
                "total_tasks": 10,
                "total_tasks_left": 0,
                "total_results": 500,
                "duration": 60,
                "eta": "0s",
                "current_task": None,
                "is_done": True,
            }
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "stats", FULL_RUN_HASH])
        assert result.exit_code == 0
        assert "100%" in result.output

    def test_stats_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "stats", "short"])
        assert result.exit_code != 0


class TestRunTasks:
    def test_list_run_tasks(self):
        def get_resp(path, **kw):
            return {"data": [
                {"id": "t" * 32, "status": "done", "total_results": 10,
                 "params": {"url": "https://example.com"}, "done_reason": "completed"},
            ]}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "tasks", FULL_RUN_HASH])
        assert result.exit_code == 0
        assert "done" in result.output

    def test_tasks_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "tasks", "short"])
        assert result.exit_code != 0


class TestRunAbort:
    def test_abort_run(self):
        mock = _mock_client(post_resp={"status": "aborted"})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "abort", FULL_RUN_HASH])
        assert result.exit_code == 0
        assert "Aborted" in result.output

    def test_abort_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "abort", "short"])
        assert result.exit_code != 0


class TestRunDownload:
    def test_download_run(self):
        def get_resp(path, **kw):
            return {"s3": "https://s3.example.com/results.csv"}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "download", FULL_RUN_HASH])
        assert result.exit_code == 0
        assert "Downloaded" in result.output
        mock.download.assert_called_once()

    def test_download_no_url_fails(self):
        def get_resp(path, **kw):
            return {"s3": ""}
        mock = _mock_client(get_resp=get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "download", FULL_RUN_HASH])
        assert result.exit_code == 1

    def test_download_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "download", "short"])
        assert result.exit_code != 0
