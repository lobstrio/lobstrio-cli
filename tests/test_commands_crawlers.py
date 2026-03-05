import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state


runner = CliRunner()

SAMPLE_CRAWLERS = {
    "data": [
        {
            "id": "abc123def456",
            "name": "Google Maps Leads Scraper",
            "credits_per_row": {"current": 3},
            "max_concurrency": 5,
            "account": None,
            "has_issues": False,
            "is_available": True,
            "is_premium": False,
        },
        {
            "id": "def789abc012",
            "name": "LinkedIn Profile Scraper",
            "credits_per_row": 2,
            "max_concurrency": 3,
            "account": True,
            "has_issues": False,
            "is_available": True,
            "is_premium": True,
        },
    ]
}


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(get_responses=None):
    mock = MagicMock()
    if get_responses:
        mock.get.side_effect = get_responses
    return mock


class TestCrawlersLs:
    def test_list_crawlers(self):
        mock = _mock_client(lambda path, **kw: SAMPLE_CRAWLERS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "ls"])
        assert result.exit_code == 0
        assert "Google Maps" in result.output
        assert "LinkedIn" in result.output

    def test_list_crawlers_json(self):
        mock = _mock_client(lambda path, **kw: SAMPLE_CRAWLERS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "ls"])
        assert result.exit_code == 0
        assert "abc123def456" in result.output

    def test_shows_status_flags(self):
        data = {"data": [
            {"id": "a1", "name": "C1", "credits_per_row": 1, "max_concurrency": 1,
             "account": None, "has_issues": True, "is_available": True, "is_premium": False},
            {"id": "a2", "name": "C2", "credits_per_row": 1, "max_concurrency": 1,
             "account": None, "has_issues": False, "is_available": False, "is_premium": False},
        ]}
        mock = _mock_client(lambda path, **kw: data)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "ls"])
        assert result.exit_code == 0


class TestCrawlersSearch:
    def test_search_finds_match(self):
        mock = _mock_client(lambda path, **kw: SAMPLE_CRAWLERS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "search", "Google"])
        assert result.exit_code == 0
        assert "Google Maps" in result.output

    def test_search_no_match(self):
        mock = _mock_client(lambda path, **kw: SAMPLE_CRAWLERS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "search", "Facebook"])
        assert result.exit_code == 0

    def test_search_json(self):
        mock = _mock_client(lambda path, **kw: SAMPLE_CRAWLERS)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "search", "LinkedIn"])
        assert result.exit_code == 0
        assert "LinkedIn" in result.output


class TestCrawlersParams:
    def test_shows_params(self):
        responses = {
            "/crawlers": SAMPLE_CRAWLERS,
            "/crawlers/abc123def456/params": {
                "task": {
                    "url": {"type": "string", "required": True, "default": "", "regex": ""},
                },
                "squid": {
                    "max_results": {"default": 100, "required": False, "allowed": [50, 100, 200]},
                },
            },
        }
        mock = _mock_client(lambda path, **kw: responses[path])
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "Google Maps"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_params_with_functions(self):
        responses = {
            "/crawlers": SAMPLE_CRAWLERS,
            "/crawlers/abc123def456/params": {
                "task": {},
                "squid": {
                    "functions": {
                        "email_finder": {"credits_per_function": {"current": 5}, "default": False},
                    },
                },
            },
        }
        mock = _mock_client(lambda path, **kw: responses[path])
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "Google Maps"])
        assert result.exit_code == 0

    def test_params_json(self):
        responses = {
            "/crawlers": SAMPLE_CRAWLERS,
            "/crawlers/abc123def456/params": {"task": {}, "squid": {}},
        }
        mock = _mock_client(lambda path, **kw: responses[path])
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "params", "Google Maps"])
        assert result.exit_code == 0

    def test_allowed_with_int_values(self):
        """Ensure integer allowed values don't crash join."""
        responses = {
            "/crawlers": SAMPLE_CRAWLERS,
            "/crawlers/abc123def456/params": {
                "task": {},
                "squid": {
                    "max_results": {"default": 100, "required": False, "allowed": [10, 20, 50, 100]},
                },
            },
        }
        mock = _mock_client(lambda path, **kw: responses[path])
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "Google Maps"])
        assert result.exit_code == 0
        assert "10" in result.output
