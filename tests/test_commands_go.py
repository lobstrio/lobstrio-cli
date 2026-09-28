import json as _json

import pytest
import httpx
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio import LobstrClient
from lobstrio.models.crawler import Crawler, CrawlerParams
from lobstrio.models.squid import Squid
from lobstrio.models.task import Task, AddTasksResult
from lobstrio.models.run import Run, RunStats
from lobstrio.models.account import Account


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
    mock.crawlers.iter.return_value = CRAWLERS
    # account_type defaults to None on CRAWLERS[0] (account=False) — must be
    # configured explicitly, otherwise `client.crawlers.get(...)` returns an
    # unconfigured MagicMock whose `.account_type` is truthy and would wrongly
    # trigger the account auto-pick/attach path in every test using this fixture.
    mock.crawlers.get.return_value = CRAWLERS[0]
    # Google Maps Leads Scraper has one optional squid-level param, e.g.
    # `language`; the `go` command must always fill it in (user value or
    # None) so a freshly created squid's update body is never empty.
    mock.crawlers.params.return_value = CrawlerParams.from_api({
        "squid": {"language": {"type": "string", "required": False}},
        "task": {"url": {"type": "string", "required": True}},
    })
    mock.squids.list.return_value = squids_by_name or []
    mock.squids.iter.return_value = squids_by_name or []
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


class TestGoKeyDefault:
    """Card #Oy4yNR7I: `go` used to hardcode the task key `url`, so a crawler
    like `1stdibs-iter-categories` (task param `department`) failed every
    time with `[400] Invalid param: url`, after already creating (and then
    deleting) a squid for nothing. `--key` now defaults from the crawler's
    own declared task params (`crawlers.params().task_params`, real examples
    checked against `matrix/modules/*/lobstr.json`), and an explicit --key
    still always wins."""

    def test_single_declared_task_param_becomes_the_default(self):
        # 1stdibs-iter-categories: one task param, `department`, not `url`.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {},
            "task": {"department": {"type": "string", "required": False}},
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "jewellery"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="newsquid123", tasks=[{"department": "jewellery"}])

    def test_a_bare_max_tasks_int_is_not_mistaken_for_a_second_param(self):
        # A crawler with `max_tasks` set in lobstr.json carries a bare int
        # under `task["max"]` (build.py ~l.694) alongside the one real field;
        # that must not turn a single-param crawler into an "ambiguous, several
        # declared" one.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {},
            "task": {"department": {"type": "string", "required": False}, "max": 1},
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "jewellery"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="newsquid123", tasks=[{"department": "jewellery"}])

    def test_several_declared_task_params_keep_url_when_present(self):
        # artcurial-iter-results: `url` and `department` both declared.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {},
            "task": {
                "url": {"type": "string", "required": True},
                "department": {"type": "string", "required": False},
            },
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="newsquid123", tasks=[{"url": "https://a.com"}])

    def test_several_declared_task_params_without_url_requires_explicit_key(self):
        # amazon-asin-collector: `asin` and `marketplace`, no `url` — go must
        # refuse to guess and name the choices, rather than create an orphan
        # squid that a 400 on tasks.add would then have to clean up.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {},
            "task": {
                "asin": {"type": "string", "required": True},
                "marketplace": {"type": "string", "required": False},
            },
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "B0EXAMPLE"])
        assert result.exit_code != 0
        assert "asin" in result.output and "marketplace" in result.output
        mock.squids.create.assert_not_called()
        mock.tasks.add.assert_not_called()

    def test_no_declared_task_params_falls_back_to_url(self):
        # christies-pm-iter-auctions and similar: no task-level param declared
        # at all. Keeps the historical default so nothing changes for these.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {"max_days": {"type": "integer", "required": False}},
            "task": {},
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="newsquid123", tasks=[{"url": "https://a.com"}])

    def test_explicit_key_overrides_the_declared_default(self):
        # The crawler's only declared task param is `department`, but the
        # caller passed --key explicitly: the explicit value must win.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {},
            "task": {"department": {"type": "string", "required": False}},
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "custom-value", "--key", "custom_field"])
        assert result.exit_code == 0
        mock.tasks.add.assert_called_once_with(squid="newsquid123", tasks=[{"custom_field": "custom-value"}])

    def test_params_fetched_once_for_a_freshly_created_squid(self):
        # Defaulting the key and validating squid-level required params both
        # need `crawlers.params()`; a newly created squid must not fetch it
        # twice.
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {},
            "task": {"department": {"type": "string", "required": False}},
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "jewellery"])
        assert result.exit_code == 0
        assert mock.crawlers.params.call_count == 1

    def test_function_is_sent_under_functions(self):
        mock = _mock_client()
        mock.crawlers.params.return_value = CrawlerParams.from_api({
            "squid": {
                "language": {"type": "string", "required": False},
                "functions": {"get_videos": {"default": False}},
            },
            "task": {"url": {"type": "string", "required": True}},
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--function", "get_videos"])
        assert result.exit_code == 0
        assert mock.squids.update.call_args[1]["params"] == {"language": None, "functions": {"get_videos": True}}

    def test_unknown_function_fails_before_creating_a_squid(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--function", "get_reels"])
        assert result.exit_code == 1
        mock.squids.create.assert_not_called()


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
        # `max_results` isn't a declared squid-level param here, but a user
        # value is still passed through (the API validates/rejects it);
        # `language` is declared and the user's value wins over the None
        # `go` would otherwise fill it with.
        _, kwargs = mock.squids.update.call_args
        assert kwargs["params"] == {"language": "English", "max_results": 200}

    def test_concurrency(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--concurrency", "3"])
        assert result.exit_code == 0


ACCOUNT_CRAWLER_HASH = "d" * 32

ACCOUNT_CRAWLER = Crawler(
    id=ACCOUNT_CRAWLER_HASH, name="Sales Nav Scraper", slug="sales-nav-scraper",
    description=None, credits_per_row=1, credits_per_email=None,
    max_concurrency=5, account=True, has_email_verification=False,
    is_public=True, is_premium=False, is_available=True, has_issues=False,
    rank=1, account_type="sales-nav-sync",
)


def _account(id, username, type="sales-nav-sync", status="200", resets_in=None,
             squids=None, status_code_info="ok"):
    return Account(
        id=id, username=username, type=type, status_code_info=status_code_info,
        status_code_description=None, baseurl=None, created_at=None,
        updated_at=None, last_synchronization_time=None,
        squids=squids or [], params={}, status=status, resets_in=resets_in,
    )


class TestGoAccountTypeMissing:
    """`crawler.account` true but `crawler.account_type` falsy (the API/SDK
    couldn't parse a usable slug) must fail loudly, not silently fall through
    to the pre-fix "no account needed" path — that silent fallthrough is
    exactly the bug in card #HuwPdi7D."""

    def test_fails_before_creating_a_squid(self):
        mock = _mock_client()
        broken_crawler = Crawler(
            id="crawler_broken", name="Broken Account Crawler", slug="broken-account-crawler",
            description=None, credits_per_row=1, credits_per_email=None,
            max_concurrency=5, account=True, has_email_verification=False,
            is_public=True, is_premium=False, is_available=True, has_issues=False,
            rank=1, account_type=None,
        )
        mock.crawlers.get.return_value = broken_crawler
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--no-download"])
        assert result.exit_code != 0
        assert "account" in result.output.lower()
        mock.squids.create.assert_not_called()


class TestGoAccounts:
    """`go --account` / auto-pick for account-backed crawlers. Card #HuwPdi7D:
    `go` on a crawler needing a synced account created a squid with no
    accounts attached at all, and the run died silently as `no_accounts`."""

    def _mock_with_account_crawler(self, accounts_on_create=None):
        mock = _mock_client()
        mock.crawlers.get.return_value = ACCOUNT_CRAWLER
        mock.squids.create.return_value = Squid(
            id="newsquid123", name="Test Squid", crawler=ACCOUNT_CRAWLER_HASH,
            crawler_name="Sales Nav Scraper", is_active=True, is_ready=False,
            concurrency=1, to_complete=None, last_run_status=None,
            last_run_at=None, total_runs=0, export_unique_results=False,
            params={}, accounts=accounts_on_create or [],
        )
        mock.squids.attach_accounts.return_value = None
        return mock

    def test_go_autopicks_single_healthy_account(self):
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [_account("ac1", "user1")]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
            ])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_called_once_with("newsquid123", ["ac1"])
        assert "Auto-picked account: user1" in result.output

    def test_go_ignores_wrong_type_and_locked_accounts_when_autopicking(self):
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            _account("ac_wrong_type", "linkedin-user", type="linkedin-sync"),
            _account("ac_locked", "locked-user", resets_in=120),
            _account("ac_bad_status", "unhealthy-user", status="429"),
            _account("ac_expired_cookies", "expired-user", status_code_info="cookies_expired"),
            _account("ac_good", "healthy-user"),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
            ])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_called_once_with("newsquid123", ["ac_good"])

    def test_go_excludes_cookies_expired_account_from_autopick(self):
        """A `status == "200"` account with expired cookies must not be
        picked — status alone is not the worker's full condition (see
        `resolve.healthy_account_candidates`)."""
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            _account("ac_expired", "expired-user", status_code_info="cookies_expired"),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
            ])
        assert result.exit_code != 0
        mock.squids.attach_accounts.assert_not_called()

    def test_go_fails_with_no_healthy_candidates_and_cleans_up_squid(self):
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            _account("ac_locked", "locked-user", resets_in=60),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
            ])
        assert result.exit_code != 0
        assert "sales-nav-sync" in result.output
        mock.squids.attach_accounts.assert_not_called()
        # No orphaned squid left behind after the failure.
        mock.squids.delete.assert_called_once_with("newsquid123")

    def test_go_fails_with_multiple_candidates_listing_them_and_cleans_up_squid(self):
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            _account("ac1", "user1"),
            _account("ac2", "user2"),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
            ])
        assert result.exit_code != 0
        assert "user1" in result.output and "user2" in result.output
        assert "--account" in result.output
        mock.squids.attach_accounts.assert_not_called()
        mock.squids.delete.assert_called_once_with("newsquid123")

    def test_go_explicit_account_skips_autopick(self):
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            _account("ac1", "user1"),
            _account("ac2", "user2"),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
                "--account", "user2",
            ])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_called_once_with("newsquid123", ["ac2"])

    def test_go_explicit_account_wrong_type_fails_before_creating_squid(self):
        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            _account("ac1", "linkedin-user", type="linkedin-sync"),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
                "--account", "linkedin-user",
            ])
        assert result.exit_code != 0
        assert "linkedin-sync" in result.output
        assert "sales-nav-sync" in result.output
        mock.squids.create.assert_not_called()

    def test_go_never_autopicks_onto_a_squid_that_already_has_accounts(self):
        existing = [
            Squid(
                id="existing123", name="MyScraper", crawler=ACCOUNT_CRAWLER_HASH,
                crawler_name="Sales Nav Scraper", is_active=True, is_ready=True,
                concurrency=1, to_complete=None, last_run_status=None,
                last_run_at=None, total_runs=0, export_unique_results=False,
                params={},
            ),
        ]
        mock = self._mock_with_account_crawler()
        mock.squids.list.return_value = existing
        mock.squids.iter.return_value = existing
        mock.squids.get.return_value = Squid(
            id="existing123", name="MyScraper", crawler=ACCOUNT_CRAWLER_HASH,
            crawler_name="Sales Nav Scraper", is_active=True, is_ready=True,
            concurrency=1, to_complete=None, last_run_status=None,
            last_run_at=None, total_runs=0, export_unique_results=False,
            params={}, accounts=[{"id": "ac_existing", "status": "ok"}],
        )
        mock.accounts.iter.return_value = [_account("ac1", "user1")]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "go", ACCOUNT_CRAWLER_HASH, "https://a.com", "--no-download",
                "--name", "MyScraper",
            ])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_not_called()
        assert "already has" in result.output

    def test_go_crawler_with_no_account_type_ignores_account_logic(self):
        """Baseline: an account-less crawler (CRAWLERS[0]) never calls
        attach_accounts, with or without --account (the latter is caught by
        resolve_accounts_with_type_check before anything is created)."""
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com", "--no-download"])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_not_called()


class TestGoCleanup:
    def test_cleanup_orphaned_squid_on_error(self):
        mock = _mock_client()
        mock.tasks.add.side_effect = Exception("Task creation failed")
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code != 0
        mock.squids.delete.assert_called_once()

    def test_cleanup_orphaned_squid_on_interrupt(self):
        """Ctrl-C between squid creation and the run starting must not leave
        an orphan any more than any other failure there does — same cleanup
        rule as test_cleanup_orphaned_squid_on_error, just via
        KeyboardInterrupt instead of an ordinary exception."""
        mock = _mock_client()
        mock.tasks.add.side_effect = KeyboardInterrupt()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code == 0
        mock.squids.delete.assert_called_once()
        assert "Interrupted" in result.output
        assert "Cleaned up" in result.output

    def test_no_cleanup_on_interrupt_after_run_started(self):
        """Once the run has started, an interrupt (e.g. during the download
        poll loop) must not delete the squid — it's no longer an
        orphan-in-progress, it's a live run."""
        mock = _mock_client()
        mock.runs.stats.side_effect = KeyboardInterrupt()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["go", "Google Maps", "https://a.com"])
        assert result.exit_code == 0
        mock.squids.delete.assert_not_called()
        assert "Run: run123" in result.output


CRAWLER_HASH = "a" * 32
SQUID_HASH = "b" * 32


def _fake_api_server(squid_params: dict | None = None):
    """A tiny stateful fake of the parts of the API `go` touches.

    Mirrors the real API's ``UpdateDeleteClustersView.update()`` (see
    ``docs/agents/api/squids.md`` and the Test Server probes on card
    Lygj81O9): a squid is created with ``is_ready=False``, and a
    ``POST /squids/{hash}`` update only calls ``cluster.save()`` — which is
    what persists ``is_ready`` — when it built a non-empty ``json_data``.
    That happens for a non-empty ``params`` dict (even one made only of
    ``None`` values, since the handler's ``if params:`` guard checks the
    dict is non-empty, not the values) or for a ``name``; an empty body or
    ``{"params": {}}`` are no-ops, same as an empty body. ``POST /runs`` on a
    not-ready squid answers 400 ``SquidNotReady``. Records every request
    (method, path, body) in order.

    ``squid_params`` is served from ``GET /crawlers/{hash}/params`` under
    the ``squid`` key, standing in for the Test Server's
    ``1stdibs-iter-categories`` (one optional squid param, ``max_days``)
    when non-empty, or ``httpbin-get-json`` (no squid-level params at all)
    when empty/omitted.
    """
    calls: list[tuple[str, str, bytes]] = []
    state = {"is_ready": False}
    squid_params = squid_params or {}

    def handler(request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        calls.append((method, path, request.content))

        if method == "GET" and path == f"/v1/crawlers/{CRAWLER_HASH}":
            return httpx.Response(200, json={
                "id": CRAWLER_HASH, "name": "Test Crawler", "slug": "test-crawler",
            })
        if method == "GET" and path == f"/v1/crawlers/{CRAWLER_HASH}/params":
            return httpx.Response(200, json={
                "squid": squid_params,
                "task": {"url": {"type": "string", "required": True}},
            })
        if method == "POST" and path == "/v1/squids":
            return httpx.Response(200, json={
                "id": SQUID_HASH, "name": "go-squid", "crawler": CRAWLER_HASH,
                "crawler_name": "Test Crawler",
                "is_active": True, "is_ready": state["is_ready"], "concurrency": 1,
                "params": {},
            })
        if method == "POST" and path == f"/v1/squids/{SQUID_HASH}":
            body = _json.loads(request.content or b"{}")
            # Mirrors UpdateDeleteClustersView.update(): a non-empty
            # `params` dict, or a `name`, builds json_data and calls
            # cluster.save(); an empty body or `{"params": {}}` does not.
            if body.get("params") or body.get("name"):
                state["is_ready"] = True
            return httpx.Response(200, json={})
        if method == "GET" and path == f"/v1/squids/{SQUID_HASH}":
            return httpx.Response(200, json={
                "id": SQUID_HASH, "name": "go-squid", "crawler": CRAWLER_HASH,
                "crawler_name": "Test Crawler",
                "is_active": True, "is_ready": state["is_ready"], "concurrency": 1,
                "params": {},
            })
        if method == "POST" and path == "/v1/tasks":
            tasks = _json.loads(request.content)["tasks"]
            return httpx.Response(200, json={
                "tasks": [{"id": f"t{i}", "params": t} for i, t in enumerate(tasks)],
                "duplicated_count": 0,
            })
        if method == "POST" and path == "/v1/runs":
            if not state["is_ready"]:
                return httpx.Response(400, json={"error": "SquidNotReady: squid is not ready"})
            return httpx.Response(200, json={
                "id": "c" * 32, "status": "running", "total_results": 0,
                "total_unique_results": 0, "duration": 0, "credit_used": 0,
                "origin": "api", "export_done": False,
            })
        if method == "DELETE" and path == f"/v1/squids/{SQUID_HASH}":
            return httpx.Response(200, json={})

        raise AssertionError(f"unexpected request: {method} {path}")

    return handler, calls


class TestGoSquidReadiness:
    """`go` on a freshly created squid must always leave it ready before the
    run starts, whatever shape the crawler's squid-level params take
    (Ijaz's `linkedin-profile-email-scraper-no-login` report, reproduced on
    the Test Server with `httpbin-get-json` and `1stdibs-iter-categories`)."""

    @staticmethod
    def _update_body(calls):
        for method, path, content in calls:
            if method == "POST" and path == f"/v1/squids/{SQUID_HASH}":
                return _json.loads(content or b"{}")
        return None

    @staticmethod
    def _assert_ready_before_run(calls):
        update_idx = next(
            (i for i, (m, p, _b) in enumerate(calls) if m == "POST" and p == f"/v1/squids/{SQUID_HASH}"),
            None,
        )
        run_idx = next(i for i, (m, p, _b) in enumerate(calls) if m == "POST" and p == "/v1/runs")
        assert update_idx is not None, (
            "no POST /v1/squids/{hash} update was ever sent — the squid stays "
            "is_ready=false and POST /v1/runs raises SquidNotReady"
        )
        assert update_idx < run_idx, "squid update must happen before the run is started"

    def test_go_with_optional_squid_params_sends_them_and_makes_the_squid_ready(self):
        # 1stdibs-iter-categories stand-in: one optional squid-level param.
        handler, calls = _fake_api_server(squid_params={
            "max_days": {"type": "integer", "required": False},
        })
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", CRAWLER_HASH, "https://example.com/cat", "--no-download",
            ])

        assert result.exit_code == 0, result.output
        self._assert_ready_before_run(calls)
        body = self._update_body(calls)
        assert body.get("params") == {"max_days": None}, body

    def test_go_without_squid_params_falls_back_to_name_and_makes_the_squid_ready(self):
        # httpbin-get-json stand-in: no squid-level params at all.
        handler, calls = _fake_api_server(squid_params={})
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", CRAWLER_HASH, "https://example.com/thing", "--no-download",
            ])

        assert result.exit_code == 0, result.output
        self._assert_ready_before_run(calls)
        body = self._update_body(calls)
        assert body.get("name") == "go-squid", body
        assert not body.get("params"), body

    def test_go_with_squid_params_and_user_value_overrides_only_that_key(self):
        handler, calls = _fake_api_server(squid_params={
            "max_days": {"type": "integer", "required": False},
            "language": {"type": "string", "required": False},
        })
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", CRAWLER_HASH, "https://example.com/cat", "--no-download",
                "--param", "max_days=7",
            ])

        assert result.exit_code == 0, result.output
        self._assert_ready_before_run(calls)
        body = self._update_body(calls)
        assert body.get("params") == {"max_days": 7, "language": None}, body

    def test_go_missing_required_squid_param_fails_before_creating_squid(self):
        # A required squid param sent as null raises ParamsNeeded from the
        # API (apiviews.py ~l.5608); `go` must catch this itself and fail
        # before POSTing /squids, not send null and surface the API error.
        handler, calls = _fake_api_server(squid_params={
            "api_key": {"type": "string", "required": True},
        })
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", CRAWLER_HASH, "https://example.com/thing", "--no-download",
            ])

        assert result.exit_code != 0
        assert "api_key" in result.output
        assert not any(m == "POST" and p == "/v1/squids" for m, p, _b in calls), (
            "a squid must not be created when a required squid param is missing"
        )

    def test_go_with_required_squid_param_value_sends_it_and_makes_the_squid_ready(self):
        handler, calls = _fake_api_server(squid_params={
            "api_key": {"type": "string", "required": True},
        })
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", CRAWLER_HASH, "https://example.com/thing", "--no-download",
                "--param", "api_key=secret",
            ])

        assert result.exit_code == 0, result.output
        self._assert_ready_before_run(calls)
        body = self._update_body(calls)
        assert body.get("params") == {"api_key": "secret"}, body


ACCT_CRAWLER_HASH = "e" * 32
ACCT_SQUID_HASH = "f" * 32
ACCOUNT_HASH = "1" * 32


def _fake_api_server_with_account(account_type="sales-nav-sync", accounts=None,
                                   seed_accounts=None, reuse_name=None):
    """Like `_fake_api_server`, extended to cover the account-attach path:
    `GET /crawlers/{hash}` reports an account type, `GET /accounts` serves the
    candidate list, and `POST/GET /squids/{hash}` track the `accounts` field —
    end-to-end coverage of card #HuwPdi7D's `go` fix against a fake transport,
    matching the SDK's own `attach_accounts()` contract (merge, not replace).

    `seed_accounts` pre-populates the squid's `accounts` (real account hashes
    already attached, standing in for a squid set up before this `go` call —
    exercises the SDK's `attach_accounts()` merge through real code, not a
    mocked call shape). `reuse_name` serves the squid from `GET /squids`
    too, so `go --name` finds it via `_find_squid_by_name` instead of
    creating a new one.
    """
    calls: list[tuple[str, str, bytes]] = []
    state = {"is_ready": True if seed_accounts else False, "accounts": list(seed_accounts or [])}
    accounts = accounts if accounts is not None else [
        {"id": ACCOUNT_HASH, "username": "sales-nav-user", "type": account_type, "status": "200"},
    ]

    def _squid_json(name="go-squid"):
        return {
            "id": ACCT_SQUID_HASH, "name": name, "crawler": ACCT_CRAWLER_HASH,
            "crawler_name": "Test Account Crawler",
            "is_active": True, "is_ready": state["is_ready"], "concurrency": 1,
            "params": {},
            "accounts": [{"id": h, "status": "ok"} for h in state["accounts"]],
        }

    def handler(request: httpx.Request) -> httpx.Response:
        method, path = request.method, request.url.path
        calls.append((method, path, request.content))

        if method == "GET" and path == f"/v1/crawlers/{ACCT_CRAWLER_HASH}":
            return httpx.Response(200, json={
                "id": ACCT_CRAWLER_HASH, "name": "Test Account Crawler", "slug": "test-account-crawler",
                "account": {"type": account_type, "baseurl": "", "cookies": [], "icon": ""},
            })
        if method == "GET" and path == f"/v1/crawlers/{ACCT_CRAWLER_HASH}/params":
            return httpx.Response(200, json={
                "squid": {}, "task": {"url": {"type": "string", "required": True}},
            })
        if method == "GET" and path == "/v1/accounts":
            return httpx.Response(200, json={"data": accounts, "total_pages": 1})
        if method == "GET" and path == "/v1/squids":
            rows = [_squid_json(name=reuse_name)] if reuse_name else []
            return httpx.Response(200, json={"data": rows, "total_pages": 1})
        if method == "POST" and path == "/v1/squids":
            return httpx.Response(200, json={
                "id": ACCT_SQUID_HASH, "name": "go-squid", "crawler": ACCT_CRAWLER_HASH,
                "crawler_name": "Test Account Crawler",
                "is_active": True, "is_ready": state["is_ready"], "concurrency": 1,
                "params": {}, "accounts": [],
            })
        if method == "POST" and path == f"/v1/squids/{ACCT_SQUID_HASH}":
            body = _json.loads(request.content or b"{}")
            if body.get("params") or body.get("name"):
                state["is_ready"] = True
            if "accounts" in body:
                state["accounts"] = body["accounts"]
            return httpx.Response(200, json={})
        if method == "GET" and path == f"/v1/squids/{ACCT_SQUID_HASH}":
            return httpx.Response(200, json=_squid_json(name=reuse_name or "go-squid"))
        if method == "POST" and path == "/v1/tasks":
            tasks = _json.loads(request.content)["tasks"]
            return httpx.Response(200, json={
                "tasks": [{"id": f"t{i}", "params": t} for i, t in enumerate(tasks)],
                "duplicated_count": 0,
            })
        if method == "POST" and path == "/v1/runs":
            if not state["is_ready"]:
                return httpx.Response(400, json={"error": "SquidNotReady: squid is not ready"})
            if not state["accounts"]:
                # Mirrors the real worker's no_accounts done reason — should
                # never be hit once `go` attaches an account correctly.
                return httpx.Response(200, json={
                    "id": "c" * 32, "status": "done", "total_results": 0,
                    "total_unique_results": 0, "duration": 0, "credit_used": 0,
                    "origin": "api", "export_done": False, "done_reason": "no_accounts",
                })
            return httpx.Response(200, json={
                "id": "c" * 32, "status": "running", "total_results": 0,
                "total_unique_results": 0, "duration": 0, "credit_used": 0,
                "origin": "api", "export_done": False,
            })
        if method == "DELETE" and path == f"/v1/squids/{ACCT_SQUID_HASH}":
            return httpx.Response(200, json={})

        raise AssertionError(f"unexpected request: {method} {path}")

    return handler, calls


class TestGoAccountsEndToEnd:
    """`go` on an account-backed crawler, against a fake transport standing in
    for the real API contract (see docs/agents/api/squids.md): the squid must
    end up with the account attached — `accounts` non-empty — before the run
    starts, not the `no_accounts` failure from card #HuwPdi7D."""

    def test_go_autopicks_and_attaches_before_run_starts(self):
        handler, calls = _fake_api_server_with_account()
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", ACCT_CRAWLER_HASH, "https://example.com/thing", "--no-download",
            ])

        assert result.exit_code == 0, result.output

        update_idx = next(
            i for i, (m, p, _b) in enumerate(calls)
            if m == "POST" and p == f"/v1/squids/{ACCT_SQUID_HASH}"
            and ACCOUNT_HASH.encode() in (_b or b"")
        )
        run_idx = next(i for i, (m, p, _b) in enumerate(calls) if m == "POST" and p == "/v1/runs")
        assert update_idx < run_idx, "account must be attached before the run starts"

        run_call = next(b for m, p, b in calls if m == "POST" and p == "/v1/runs")
        assert run_call is not None

    def test_go_with_no_healthy_account_fails_and_cleans_up(self):
        handler, calls = _fake_api_server_with_account(accounts=[])
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", ACCT_CRAWLER_HASH, "https://example.com/thing", "--no-download",
            ])

        assert result.exit_code != 0
        assert any(m == "DELETE" and p == f"/v1/squids/{ACCT_SQUID_HASH}" for m, p, _b in calls), (
            "a squid created but never made runnable must be cleaned up, not left orphaned"
        )
        assert not any(m == "POST" and p == "/v1/runs" for m, p, _b in calls), (
            "must never start a run once account resolution fails"
        )

    def test_go_reused_squid_merges_explicit_account_with_existing_one(self):
        """End-to-end regression for the merge itself: a squid seeded with one
        real account already attached, reused by `--name`, given a second
        account explicitly — the outgoing `POST /squids/{hash}` body must
        carry both hashes, driven through the real SDK `attach_accounts()`
        merge (GET current -> union -> POST), not a mocked call shape."""
        existing_hash = "3" * 32
        new_hash = "4" * 32
        handler, calls = _fake_api_server_with_account(
            accounts=[
                {"id": new_hash, "username": "second-user", "type": "sales-nav-sync", "status": "200"},
            ],
            seed_accounts=[existing_hash],
            reuse_name="MyReusedSquid",
        )
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "go", ACCT_CRAWLER_HASH, "https://example.com/thing", "--no-download",
                "--name", "MyReusedSquid", "--account", "second-user",
            ])

        assert result.exit_code == 0, result.output
        update_body = next(
            _json.loads(b) for m, p, b in calls
            if m == "POST" and p == f"/v1/squids/{ACCT_SQUID_HASH}" and b"accounts" in (b or b"")
        )
        assert set(update_body["accounts"]) == {existing_hash, new_hash}, update_body
