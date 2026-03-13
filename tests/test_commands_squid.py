import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.crawler import Crawler
from lobstrio.models.squid import Squid


runner = CliRunner()

CRAWLERS = [
    Crawler(
        id="crawler1", name="Google Maps Leads Scraper",
        slug="google-maps-leads-scraper", description=None,
        credits_per_row=3, credits_per_email=None, max_concurrency=5,
        account=False, has_email_verification=False, is_public=True,
        is_premium=False, is_available=True, has_issues=False, rank=1,
    ),
]

SQUIDS = [
    Squid(
        id="squid1abc123def456", name="My Squid", crawler="crawler1",
        crawler_name="Google Maps", is_active=True, is_ready=True,
        concurrency=3, to_complete=0, last_run_status="finished",
        last_run_at="2025-01-01", total_runs=5, export_unique_results=True,
        params={"max_results": 100},
    ),
]


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client():
    mock = MagicMock()
    mock.squids.list.return_value = SQUIDS
    mock.crawlers.list.return_value = CRAWLERS
    return mock


class TestSquidCreate:
    def test_create_squid(self):
        mock = _mock_client()
        mock.squids.create.return_value = Squid(
            id="newsquid123", name="My New Squid", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=False,
            concurrency=1, to_complete=None, last_run_status=None,
            last_run_at=None, total_runs=0, export_unique_results=False,
            params={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "Google Maps"])
        assert result.exit_code == 0
        assert "Created" in result.output

    def test_create_with_name(self):
        mock = _mock_client()
        mock.squids.create.return_value = Squid(
            id="newsquid123", name="Custom Name", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=False,
            concurrency=1, to_complete=None, last_run_status=None,
            last_run_at=None, total_runs=0, export_unique_results=False,
            params={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "Google Maps", "--name", "Custom Name"])
        assert result.exit_code == 0
        mock.squids.create.assert_called_once_with("crawler1", name="Custom Name")

    def test_create_json_mode(self):
        mock = _mock_client()
        mock.squids.create.return_value = Squid(
            id="newsquid123", name="Squid", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=False,
            concurrency=1, to_complete=None, last_run_status=None,
            last_run_at=None, total_runs=0, export_unique_results=False,
            params={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "squid", "create", "Google Maps"])
        assert result.exit_code == 0
        assert "newsquid123" in result.output

    def test_create_by_crawler_slug(self):
        mock = _mock_client()
        mock.squids.create.return_value = Squid(
            id="newsquid123", name="New Squid", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=False,
            concurrency=1, to_complete=None, last_run_status=None,
            last_run_at=None, total_runs=0, export_unique_results=False,
            params={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "Created" in result.output
        mock.squids.create.assert_called_once_with("crawler1", name=None)


class TestSquidLs:
    def test_list_squids(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "ls"])
        assert result.exit_code == 0
        assert "My Squid" in result.output

    def test_list_with_pagination(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "ls", "--limit", "10", "--page", "2"])
        assert result.exit_code == 0
        mock.squids.list.assert_called_once_with(limit=10, page=2, name=None)

    def test_list_json(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "squid", "ls"])
        assert result.exit_code == 0


class TestSquidShow:
    SQUID_DETAIL = Squid(
        id="squid1abc123def456", name="My Squid", crawler="crawler1",
        crawler_name="Google Maps", is_active=True, is_ready=True,
        concurrency=3, to_complete=0, last_run_status="finished",
        last_run_at="2025-01-01", total_runs=5, export_unique_results=True,
        params={"max_results": 100},
    )

    def test_show_by_name(self):
        mock = _mock_client()
        mock.squids.get.return_value = self.SQUID_DETAIL
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "show", "My Squid"])
        assert result.exit_code == 0
        assert "My Squid" in result.output

    def test_show_by_name_substring(self):
        mock = _mock_client()
        mock.squids.get.return_value = self.SQUID_DETAIL
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "show", "Squid"])
        assert result.exit_code == 0

    def test_show_by_hash_prefix(self):
        squids = [
            Squid(
                id="aabb11cc22dd33ee44ff5566", name="My Squid", crawler="c1",
                crawler_name="Google Maps", is_active=True, is_ready=True,
                concurrency=1, to_complete=None, last_run_status=None,
                last_run_at=None, total_runs=0, export_unique_results=False,
                params={},
            ),
        ]
        mock = MagicMock()
        mock.squids.list.return_value = squids
        mock.squids.get.return_value = squids[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "show", "aabb11"])
        assert result.exit_code == 0


class TestSquidUpdate:
    def test_update_concurrency(self):
        mock = _mock_client()
        mock.squids.update.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--concurrency", "5"])
        assert result.exit_code == 0
        mock.squids.update.assert_called_once()
        call_kwargs = mock.squids.update.call_args
        assert call_kwargs[1]["concurrency"] == 5

    def test_update_with_params(self):
        mock = _mock_client()
        mock.squids.update.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--param", "max_results=200"])
        assert result.exit_code == 0
        call_kwargs = mock.squids.update.call_args
        assert call_kwargs[1]["params"]["max_results"] == 200

    def test_update_no_options_error(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid"])
        assert result.exit_code == 1


class TestSquidEmpty:
    def test_empty_squid(self):
        mock = _mock_client()
        mock.squids.empty.return_value = {"deleted_count": 10}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "empty", "My Squid"])
        assert result.exit_code == 0
        assert "10" in result.output


class TestSquidRm:
    def test_delete_with_force(self):
        mock = _mock_client()
        mock.squids.delete.return_value = {"id": "squid1abc123def456", "deleted": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "rm", "My Squid", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_without_force_prompts(self):
        mock = _mock_client()
        mock.squids.delete.return_value = {"id": "squid1abc123def456", "deleted": True}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "rm", "My Squid"], input="y\n")
        assert result.exit_code == 0

    def test_delete_aborted(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "rm", "My Squid"], input="n\n")
        assert result.exit_code != 0
