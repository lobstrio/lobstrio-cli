import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.crawler import Crawler
from lobstrio.models.squid import Squid
from lobstrio.models.task import Task, AddTasksResult
from lobstrio.models.run import Run, RunStats


runner = CliRunner()

CRAWLERS = [
    Crawler(
        id="crawler1abc", name="Google Maps Leads Scraper",
        slug="google-maps-leads-scraper", description=None,
        credits_per_row=3, credits_per_email=None, max_concurrency=5,
        account=False, has_email_verification=False, is_public=True,
        is_premium=False, is_available=True, has_issues=False, rank=1,
    ),
]


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(squids_by_name=None):
    """Create a mock client for go command tests."""
    mock = MagicMock()
    mock.crawlers.list.return_value = CRAWLERS
    mock.squids.list.return_value = squids_by_name or []
    mock.squids.create.return_value = Squid(
        id="newsquid123", name="Test Squid", crawler="crawler1abc",
        crawler_name="Google Maps Leads Scraper", is_active=True, is_ready=False,
        concurrency=1, to_complete=None, last_run_status=None,
        last_run_at=None, total_runs=0, export_unique_results=False,
        params={},
    )
    mock.squids.update.return_value = None
    mock.squids.empty.return_value = {"deleted_count": 0}
    mock.squids.delete.return_value = {}

    def _make_add_result(*, squid, tasks):
        return AddTasksResult(
            tasks=[Task(id=f"t{i}", is_active=True, params=t, status=None, created_at=None)
                   for i, t in enumerate(tasks)],
            duplicated_count=0,
        )
    mock.tasks.add.side_effect = _make_add_result

    mock.runs.start.return_value = Run(
        id="run123", status="running", total_results=0,
        total_unique_results=0, duration=0, credit_used=0,
        origin="api", done_reason=None, done_reason_desc=None,
        export_done=False, started_at=None, ended_at=None,
    )
    mock.runs.stats.return_value = RunStats(
        percent_done="100%", total_tasks=1, total_tasks_done=1,
        total_tasks_left=0, total_results=10, duration=30,
        eta="0s", current_task=None, is_done=True,
    )
    mock.runs.get.return_value = Run(
        id="run123", status="finished", total_results=10,
        total_unique_results=10, duration=30, credit_used=5,
        origin="api", done_reason="completed", done_reason_desc=None,
        export_done=True, started_at=None, ended_at=None,
    )
    mock.runs.download.return_value = None
    return mock


class TestGoBasic:
    def test_go_full_workflow(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://maps.google.com/place1"])
        assert result.exit_code == 0
        assert "Downloaded" in result.output

    def test_go_multiple_inputs(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "https://b.com"])
        assert result.exit_code == 0

    def test_go_no_inputs_fails(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps"])
        assert result.exit_code == 1


class TestGoKey:
    def test_custom_key(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "pizza", "--key", "keyword"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="newsquid123", tasks=[{"keyword": "pizza"}])


class TestGoFile:
    def test_file_input(self, tmp_path):
        f = tmp_path / "urls.txt"
        f.write_text("https://a.com\nhttps://b.com\n# comment\n\n")
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "--file", str(f)])
        assert result.exit_code == 0
        call_args = mock.tasks.add.call_args
        tasks = call_args[1]["tasks"]
        assert len(tasks) == 2  # comment and empty line filtered


class TestGoNoDownload:
    def test_no_download(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--no-download"])
        assert result.exit_code == 0
        mock.runs.download.assert_not_called()


class TestGoDelete:
    def test_delete_after_completion(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--delete"])
        assert result.exit_code == 0
        mock.squids.delete.assert_called_once()


class TestGoReuse:
    def test_reuse_existing_squid(self):
        existing = [
            Squid(
                id="existing123", name="MyScraper", crawler="crawler1abc",
                crawler_name="Google Maps", is_active=True, is_ready=True,
                concurrency=1, to_complete=None, last_run_status=None,
                last_run_at=None, total_runs=0, export_unique_results=False,
                params={},
            ),
        ]
        mock = _mock_client(squids_by_name=existing)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--name", "MyScraper"])
        assert result.exit_code == 0
        # Should NOT have created a new squid
        mock.squids.create.assert_not_called()

    def test_reuse_with_empty(self):
        existing = [
            Squid(
                id="existing123", name="MyScraper", crawler="crawler1abc",
                crawler_name="Google Maps", is_active=True, is_ready=True,
                concurrency=1, to_complete=None, last_run_status=None,
                last_run_at=None, total_runs=0, export_unique_results=False,
                params={},
            ),
        ]
        mock = _mock_client(squids_by_name=existing)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--name", "MyScraper", "--empty"])
        assert result.exit_code == 0
        mock.squids.empty.assert_called_once()


class TestGoParams:
    def test_squid_params(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com",
                                         "--param", "max_results=200", "--param", "language=English"])
        assert result.exit_code == 0
        mock.squids.update.assert_called_once()

    def test_concurrency(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--concurrency", "3"])
        assert result.exit_code == 0


class TestGoCleanup:
    def test_cleanup_orphaned_squid_on_error(self):
        mock = _mock_client()
        mock.tasks.add.side_effect = Exception("Task creation failed")
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code != 0
        mock.squids.delete.assert_called_once()
