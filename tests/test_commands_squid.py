import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state


runner = CliRunner()

CRAWLERS = {
    "data": [
        {"id": "crawler1", "name": "Google Maps Leads Scraper", "slug": "google-maps-leads-scraper"},
    ]
}

SQUIDS = {
    "data": [
        {"id": "squid1abc123def456", "name": "My Squid", "crawler_name": "Google Maps"},
    ]
}


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(responses):
    mock = MagicMock()
    if callable(responses):
        mock.get.side_effect = responses
    else:
        mock.get.return_value = responses
    mock.post.return_value = {"id": "squid1abc123def456", "name": "New Squid"}
    mock.delete.return_value = {"id": "squid1abc123def456", "deleted": True}
    return mock


class TestSquidCreate:
    def test_create_squid(self):
        mock = _mock_client(lambda path, **kw: CRAWLERS)
        mock.post.return_value = {"id": "newsquid123", "name": "My New Squid"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "Google Maps"])
        assert result.exit_code == 0
        assert "Created" in result.output

    def test_create_with_name(self):
        mock = _mock_client(lambda path, **kw: CRAWLERS)
        mock.post.return_value = {"id": "newsquid123", "name": "Custom Name"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "Google Maps", "--name", "Custom Name"])
        assert result.exit_code == 0
        mock.post.assert_called_once()
        call_json = mock.post.call_args[1]["json"]
        assert call_json["name"] == "Custom Name"

    def test_create_json_mode(self):
        mock = _mock_client(lambda path, **kw: CRAWLERS)
        mock.post.return_value = {"id": "newsquid123", "name": "Squid"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "squid", "create", "Google Maps"])
        assert result.exit_code == 0
        assert "newsquid123" in result.output

    def test_create_by_crawler_slug(self):
        """Resolve crawler by slug when creating squid."""
        mock = _mock_client(lambda path, **kw: CRAWLERS)
        mock.post.return_value = {"id": "newsquid123", "name": "New Squid"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "Created" in result.output
        call_json = mock.post.call_args[1]["json"]
        assert call_json["crawler"] == "crawler1"

    def test_create_by_crawler_slug_prefix(self):
        """Resolve crawler by slug prefix when creating squid."""
        mock = _mock_client(lambda path, **kw: CRAWLERS)
        mock.post.return_value = {"id": "newsquid123", "name": "New Squid"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "create", "google-maps"])
        assert result.exit_code == 0
        assert "Created" in result.output


class TestSquidLs:
    def test_list_squids(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "ls"])
        assert result.exit_code == 0
        assert "My Squid" in result.output

    def test_list_with_pagination(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "ls", "--limit", "10", "--page", "2"])
        assert result.exit_code == 0
        mock.get.assert_called_once()
        call_params = mock.get.call_args[1]["params"]
        assert call_params["limit"] == 10
        assert call_params["page"] == 2

    def test_list_json(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "squid", "ls"])
        assert result.exit_code == 0


class TestSquidShow:
    SQUID_DETAIL = {
        "id": "squid1abc123def456",
        "name": "My Squid",
        "crawler_name": "Google Maps",
        "is_active": True,
        "is_ready": True,
        "concurrency": 3,
        "to_complete": False,
        "last_run_status": "finished",
        "last_run_at": "2025-01-01",
        "total_runs": 5,
        "export_unique_results": True,
        "params": {"max_results": 100},
    }

    def test_show_by_name(self):
        def get_side_effect(path, **kw):
            if path == "/squids":
                return SQUIDS
            return self.SQUID_DETAIL
        mock = _mock_client(get_side_effect)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "show", "My Squid"])
        assert result.exit_code == 0
        assert "My Squid" in result.output

    def test_show_by_name_substring(self):
        """Unique substring should resolve."""
        def get_side_effect(path, **kw):
            if path == "/squids":
                return SQUIDS
            return self.SQUID_DETAIL
        mock = _mock_client(get_side_effect)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "show", "Squid"])
        assert result.exit_code == 0

    def test_show_by_hash_prefix(self):
        """Hex prefix should resolve via hash matching."""
        squids = {"data": [
            {"id": "aabb11cc22dd33ee44ff5566", "name": "My Squid", "crawler_name": "Google Maps"},
        ]}
        def get_side_effect(path, **kw):
            if path == "/squids":
                return squids
            return {**self.SQUID_DETAIL, "id": "aabb11cc22dd33ee44ff5566"}
        mock = _mock_client(get_side_effect)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "show", "aabb11"])
        assert result.exit_code == 0


class TestSquidUpdate:
    def test_update_concurrency(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        mock.post.return_value = {"id": "squid1abc123def456"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--concurrency", "5"])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["concurrency"] == 5

    def test_update_with_params(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        mock.post.return_value = {"id": "squid1abc123def456"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--param", "max_results=200"])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["params"]["max_results"] == 200

    def test_update_no_options_error(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid"])
        assert result.exit_code == 1


class TestSquidEmpty:
    def test_empty_squid(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        mock.post.return_value = {"deleted_count": 10}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "empty", "My Squid"])
        assert result.exit_code == 0
        assert "10" in result.output


class TestSquidRm:
    def test_delete_with_force(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "rm", "My Squid", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_without_force_prompts(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "rm", "My Squid"], input="y\n")
        assert result.exit_code == 0

    def test_delete_aborted(self):
        mock = _mock_client(lambda path, **kw: SQUIDS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "rm", "My Squid"], input="n\n")
        assert result.exit_code != 0
