import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.crawler import Crawler, CrawlerParams


runner = CliRunner()

SAMPLE_CRAWLERS = [
    Crawler(
        id="abc123def456", name="Google Maps Leads Scraper",
        slug="google-maps-leads-scraper", description=None,
        credits_per_row=3, credits_per_email=None, max_concurrency=5,
        account=False, has_email_verification=False, is_public=True,
        is_premium=False, is_available=True, has_issues=False, rank=1,
    ),
    Crawler(
        id="def789abc012", name="LinkedIn Profile Scraper",
        slug="linkedin-profile-scraper", description=None,
        credits_per_row=2, credits_per_email=None, max_concurrency=3,
        account=True, has_email_verification=False, is_public=True,
        is_premium=True, is_available=True, has_issues=False, rank=2,
    ),
]


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client():
    mock = MagicMock()
    mock.crawlers.list.return_value = SAMPLE_CRAWLERS
    return mock


class TestCrawlersLs:
    def test_list_crawlers(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "ls"])
        assert result.exit_code == 0
        assert "Google Maps" in result.output
        assert "LinkedIn" in result.output

    def test_list_crawlers_json(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "ls"])
        assert result.exit_code == 0
        assert "abc123def456" in result.output

    def test_shows_status_flags(self):
        crawlers = [
            Crawler(
                id="a1", name="C1", slug="c1", description=None,
                credits_per_row=1, credits_per_email=None, max_concurrency=1,
                account=False, has_email_verification=False, is_public=True,
                is_premium=False, is_available=True, has_issues=True, rank=None,
            ),
            Crawler(
                id="a2", name="C2", slug="c2", description=None,
                credits_per_row=1, credits_per_email=None, max_concurrency=1,
                account=False, has_email_verification=False, is_public=True,
                is_premium=False, is_available=False, has_issues=False, rank=None,
            ),
        ]
        mock = MagicMock()
        mock.crawlers.list.return_value = crawlers
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "ls"])
        assert result.exit_code == 0


class TestCrawlersShow:
    CRAWLER_DETAIL = Crawler(
        id="abc123def456", name="Google Maps Leads Scraper",
        slug="google-maps-leads-scraper", description="Scrape Google Maps",
        credits_per_row=3, credits_per_email=None, max_concurrency=5,
        account=False, has_email_verification=False, is_public=True,
        is_premium=False, is_available=True, has_issues=False, rank=1,
        input_params=[{"name": "url", "level": "task", "type": "string", "required": "true", "default": ""}],
        result_fields=["name", "address", "phone"],
    )

    def test_show_by_slug(self):
        mock = _mock_client()
        mock.crawlers.get.return_value = self.CRAWLER_DETAIL
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "show", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "Google Maps Leads Scraper" in result.output
        assert "google-maps-leads-scraper" in result.output

    def test_show_by_name(self):
        detail = Crawler(
            id="def789abc012", name="LinkedIn Profile Scraper",
            slug="linkedin-profile-scraper", description=None,
            credits_per_row=2, credits_per_email=None, max_concurrency=3,
            account=True, has_email_verification=False, is_public=True,
            is_premium=True, is_available=True, has_issues=False, rank=2,
        )
        mock = _mock_client()
        mock.crawlers.get.return_value = detail
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "show", "LinkedIn Profile"])
        assert result.exit_code == 0
        assert "LinkedIn Profile Scraper" in result.output

    def test_show_json(self):
        mock = _mock_client()
        mock.crawlers.get.return_value = self.CRAWLER_DETAIL
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "show", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "abc123def456" in result.output

    def test_show_displays_input_params(self):
        mock = _mock_client()
        mock.crawlers.get.return_value = self.CRAWLER_DETAIL
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "show", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_show_displays_result_fields(self):
        mock = _mock_client()
        mock.crawlers.get.return_value = self.CRAWLER_DETAIL
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "show", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "phone" in result.output
        assert "name, address, phone" in result.output


class TestCrawlersSearch:
    def test_search_finds_match(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "search", "Google"])
        assert result.exit_code == 0
        assert "Google Maps" in result.output

    def test_search_no_match(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "search", "Facebook"])
        assert result.exit_code == 0

    def test_search_json(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "search", "LinkedIn"])
        assert result.exit_code == 0
        assert "LinkedIn" in result.output


class TestCrawlersParams:
    def test_shows_params(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams(
            task_params={"url": {"type": "string", "required": True, "default": "", "regex": ""}},
            squid_params={"max_results": {"default": 100, "required": False, "allowed": [50, 100, 200]}},
            functions={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "Google Maps"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_params_with_functions(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams(
            task_params={},
            squid_params={},
            functions={"email_finder": {"credits_per_function": {"current": 5}, "default": False}},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "Google Maps"])
        assert result.exit_code == 0

    def test_params_json(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams(
            task_params={}, squid_params={}, functions={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "crawlers", "params", "Google Maps"])
        assert result.exit_code == 0

    def test_allowed_with_int_values(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams(
            task_params={},
            squid_params={"max_results": {"default": 100, "required": False, "allowed": [10, 20, 50, 100]}},
            functions={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "Google Maps"])
        assert result.exit_code == 0
        assert "10" in result.output

    def test_params_by_exact_slug(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams(
            task_params={"url": {"type": "string", "required": True, "default": "", "regex": ""}},
            squid_params={}, functions={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "google-maps-leads-scraper"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_params_by_slug_prefix(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams(
            task_params={"url": {"type": "string", "required": True, "default": "", "regex": ""}},
            squid_params={}, functions={},
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "linkedin-profile"])
        assert result.exit_code == 0

    def test_params_ambiguous_slug(self):
        crawlers = [
            Crawler(
                id="c1", name="Google Maps Leads", slug="google-maps-leads",
                description=None, credits_per_row=1, credits_per_email=None,
                max_concurrency=1, account=False, has_email_verification=False,
                is_public=True, is_premium=False, is_available=True, has_issues=False, rank=None,
            ),
            Crawler(
                id="c2", name="Google Maps Reviews", slug="google-maps-reviews",
                description=None, credits_per_row=1, credits_per_email=None,
                max_concurrency=1, account=False, has_email_verification=False,
                is_public=True, is_premium=False, is_available=True, has_issues=False, rank=None,
            ),
        ]
        mock = MagicMock()
        mock.crawlers.list.return_value = crawlers
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["crawlers", "params", "google-maps"])
        assert result.exit_code != 0
