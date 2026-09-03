import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.squid import Squid
from lobstrio.models.run import Run, RunStats
from lobstrio.models.task import Task, TaskStatus


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

FULL_RUN_HASH = "b" * 32


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client():
    mock = MagicMock()
    mock.squids.list.return_value = SQUIDS
    return mock


def _run(status="running", total_results=0):
    return Run(
        id=FULL_RUN_HASH, status=status, total_results=total_results,
        total_unique_results=0, duration=0, credit_used=0, origin="api",
        done_reason=None, done_reason_desc=None, export_done=False,
        started_at="2025-01-01T00:00:00Z", ended_at=None,
    )


def _stats(is_done, pct="100%"):
    s = MagicMock()
    s.percent_done = pct
    s.total_tasks = 1
    s.total_tasks_done = 1 if is_done else 0
    s.eta = ""
    s.is_done = is_done
    return s


class TestRunStart:
    def test_start_run(self):
        mock = _mock_client()
        mock.runs.start.return_value = Run(
            id=FULL_RUN_HASH, status="running", total_results=0,
            total_unique_results=0, duration=0, credit_used=0,
            origin="api", done_reason=None, done_reason_desc=None,
            export_done=False, started_at="2025-01-01T00:00:00Z", ended_at=None,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "start", "My Squid"])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_start_json_mode(self):
        mock = _mock_client()
        mock.runs.start.return_value = Run(
            id=FULL_RUN_HASH, status="running", total_results=0,
            total_unique_results=0, duration=0, credit_used=0,
            origin="api", done_reason=None, done_reason_desc=None,
            export_done=False, started_at=None, ended_at=None,
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "run", "start", "My Squid"])
        assert result.exit_code == 0
        assert FULL_RUN_HASH in result.output

    def test_start_wait_completes(self):
        mock = _mock_client()
        mock.runs.start.return_value = _run("running")
        mock.runs.stats.return_value = _stats(is_done=True)
        mock.runs.get.return_value = _run("finished", total_results=100)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "start", "My Squid", "--wait", "--poll", "0.01"])
        assert result.exit_code == 0
        assert "finished" in result.output

    def test_start_wait_timeout(self):
        mock = _mock_client()
        mock.runs.start.return_value = _run("running")
        mock.runs.stats.return_value = _stats(is_done=False, pct="10%")  # never finishes
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "start", "My Squid", "--timeout", "0", "--poll", "0.01"])
        assert result.exit_code == 1
        assert "did not finish" in result.output


class TestRunLs:
    def test_list_runs(self):
        mock = _mock_client()
        mock.runs.list.return_value = [
            Run(
                id=FULL_RUN_HASH, status="finished", total_results=100,
                total_unique_results=95, duration=120.5, credit_used=50,
                origin="api", done_reason="completed", done_reason_desc=None,
                export_done=True, started_at="2025-01-01", ended_at="2025-01-01",
            ),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "ls", "My Squid"])
        assert result.exit_code == 0
        assert "finis" in result.output

    def test_list_runs_duration_formatting(self):
        mock = _mock_client()
        mock.runs.list.return_value = [
            Run(
                id=FULL_RUN_HASH, status="finished", total_results=0,
                total_unique_results=0, duration=0, credit_used=0,
                origin="api", done_reason=None, done_reason_desc=None,
                export_done=False, started_at=None, ended_at=None,
            ),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "ls", "My Squid"])
        assert result.exit_code == 0


class TestRunShow:
    def test_show_run(self):
        mock = _mock_client()
        mock.runs.get.return_value = Run(
            id=FULL_RUN_HASH, status="finished", total_results=100,
            total_unique_results=95, duration=120, credit_used=50,
            origin="api", done_reason="completed", done_reason_desc=None,
            export_done=True, started_at="2025-01-01T00:00:00Z",
            ended_at="2025-01-01T00:02:00Z",
        )
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
        mock = _mock_client()
        mock.runs.stats.return_value = RunStats(
            percent_done="100%", total_tasks=10, total_tasks_done=10,
            total_tasks_left=0, total_results=500, duration=60,
            eta="0s", current_task=None, is_done=True,
        )
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
        mock = _mock_client()
        mock.runs.tasks.return_value = [
            Task(
                id="t" * 32, is_active=True,
                params={"url": "https://example.com"},
                status=TaskStatus(status="done", total_results=10, total_pages=1,
                                  done_reason="completed", has_errors=False),
                created_at=None,
            ),
        ]
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
        mock = _mock_client()
        mock.runs.abort.return_value = {"status": "aborted"}
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
        mock = _mock_client()
        mock.runs.download.return_value = None
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "download", FULL_RUN_HASH])
        assert result.exit_code == 0
        assert "Downloaded" in result.output
        mock.runs.download.assert_called_once()

    def test_download_no_url_fails(self):
        mock = _mock_client()
        mock.runs.download.side_effect = KeyError("s3")
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "download", FULL_RUN_HASH])
        assert result.exit_code == 1

    def test_download_partial_hash_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["run", "download", "short"])
        assert result.exit_code != 0
