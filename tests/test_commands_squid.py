import json as _json

import httpx
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio import LobstrClient
from lobstrio.models.account import Account
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
    mock.squids.iter.return_value = SQUIDS
    mock.crawlers.list.return_value = CRAWLERS
    mock.crawlers.iter.return_value = CRAWLERS
    # CRAWLERS[0].account_type is None (account=False) — set explicitly,
    # otherwise client.crawlers.get(...) returns an unconfigured MagicMock
    # whose .account_type is truthy and would misfire the --account checks.
    mock.crawlers.get.return_value = CRAWLERS[0]
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
        mock.squids.iter.return_value = squids
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

    def test_update_new_fields(self):
        mock = _mock_client()
        mock.squids.update.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "squid", "update", "My Squid",
                "--inactive", "--to-complete", "50", "--no-line-breaks",
                "--cron", "0 9 * * 1", "--timezone", "Europe/Paris",
            ])
        assert result.exit_code == 0
        kwargs = mock.squids.update.call_args[1]
        assert kwargs["is_active"] is False
        assert kwargs["to_complete"] == 50
        assert kwargs["no_line_breaks"] is True
        assert kwargs["cron_expression"] == "0 9 * * 1"
        assert kwargs["timezone"] == "Europe/Paris"


class TestSquidUpdateAccounts:
    """`squid update --account` — see docs/agents/api/squids.md: `accounts` on
    `POST /squids/{id}` is full-replace, so attach_accounts() (merge by
    default) must be used, never a raw update(accounts=...) with just the new
    hash."""

    def _mock_with_account_crawler(self, account_type="sales-nav-sync"):
        mock = _mock_client()
        mock.squids.get.return_value = Squid(
            id="squid1abc123def456", name="My Squid", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=True,
            concurrency=3, to_complete=0, last_run_status="finished",
            last_run_at="2025-01-01", total_runs=5, export_unique_results=True,
            params={}, accounts=[],
        )
        mock.crawlers.get.return_value = Crawler(
            id="crawler1", name="Sales Nav Scraper", slug="sales-nav-scraper",
            description=None, credits_per_row=1, credits_per_email=None,
            max_concurrency=5, account=True, has_email_verification=False,
            is_public=True, is_premium=False, is_available=True,
            has_issues=False, rank=1, account_type=account_type,
        )
        return mock

    def test_update_with_account_merges_by_default(self):
        from lobstrio.models.account import Account

        mock = self._mock_with_account_crawler()
        mock.accounts.iter.return_value = [
            Account(
                id="ac1", username="user@example.com", type="sales-nav-sync",
                status_code_info="ok", status_code_description=None, baseurl=None,
                created_at=None, updated_at=None, last_synchronization_time=None,
                squids=[], params={}, status="200",
            ),
        ]
        mock.squids.attach_accounts.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--account", "user@example.com"])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_called_once_with(
            "squid1abc123def456", ["ac1"], replace=False
        )

    def test_update_with_replace_accounts_flag(self):
        mock = self._mock_with_account_crawler()
        mock.squids.attach_accounts.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--replace-accounts"])
        assert result.exit_code == 0, result.output
        mock.squids.attach_accounts.assert_called_once_with(
            "squid1abc123def456", [], replace=True
        )

    def test_update_replace_accounts_with_no_account_warns_before_detaching_all(self):
        """The one destructive path: --replace-accounts with no --account at
        all detaches everything. Must name what's being lost before doing it,
        not just report success afterwards."""
        mock = self._mock_with_account_crawler()
        mock.squids.get.return_value = Squid(
            id="squid1abc123def456", name="My Squid", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=True,
            concurrency=3, to_complete=0, last_run_status="finished",
            last_run_at="2025-01-01", total_runs=5, export_unique_results=True,
            params={}, accounts=[{"id": "ac_old1", "status": "ok"}, {"id": "ac_old2", "status": "ok"}],
        )
        mock.squids.attach_accounts.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--replace-accounts"])
        assert result.exit_code == 0, result.output
        assert "ac_old1"[:12] in result.output
        assert "ac_old2"[:12] in result.output
        assert "2 account" in result.output
        mock.squids.attach_accounts.assert_called_once_with(
            "squid1abc123def456", [], replace=True
        )

    def test_update_replace_accounts_keeping_the_same_set_does_not_warn(self):
        mock = self._mock_with_account_crawler()
        mock.squids.get.return_value = Squid(
            id="squid1abc123def456", name="My Squid", crawler="crawler1",
            crawler_name="Google Maps", is_active=True, is_ready=True,
            concurrency=3, to_complete=0, last_run_status="finished",
            last_run_at="2025-01-01", total_runs=5, export_unique_results=True,
            params={}, accounts=[{"id": "ac1", "status": "ok"}],
        )
        mock.accounts.iter.return_value = [
            Account(
                id="ac1", username="jane", type="sales-nav-sync", status_code_info="ok",
                status_code_description=None, baseurl=None, created_at=None, updated_at=None,
                last_synchronization_time=None, squids=[], params={}, status="200",
            ),
        ]
        mock.squids.attach_accounts.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "squid", "update", "My Squid", "--replace-accounts", "--account", "jane",
            ])
        assert result.exit_code == 0, result.output
        assert "Warning" not in result.output
        mock.squids.attach_accounts.assert_called_once_with(
            "squid1abc123def456", ["ac1"], replace=True
        )

    def test_update_account_wrong_type_fails_with_clear_message(self):
        from lobstrio.models.account import Account

        mock = self._mock_with_account_crawler(account_type="sales-nav-sync")
        mock.accounts.iter.return_value = [
            Account(
                id="ac1", username="linkedin-user", type="linkedin-sync",
                status_code_info="ok", status_code_description=None, baseurl=None,
                created_at=None, updated_at=None, last_synchronization_time=None,
                squids=[], params={}, status="200",
            ),
        ]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--account", "linkedin-user"])
        assert result.exit_code == 1
        assert "linkedin-sync" in result.output
        assert "sales-nav-sync" in result.output
        mock.squids.attach_accounts.assert_not_called()

    def test_update_account_when_crawler_needs_none_fails_with_clear_message(self):
        mock = _mock_client()  # CRAWLERS[0] has account=False, account_type=None
        mock.squids.get.return_value = SQUIDS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "update", "My Squid", "--account", "someone"])
        assert result.exit_code == 1
        assert "does not use an account" in result.output
        mock.squids.attach_accounts.assert_not_called()


class TestSquidUpdateAccountsEndToEnd:
    """End-to-end regression for the merge itself, against a fake transport
    (not a mocked call shape): a squid already carrying one real account,
    given a second one via `--account` — the outgoing `POST /squids/{hash}`
    body must carry both hashes, driven through the real SDK
    `attach_accounts()` merge (GET current squid -> union -> POST)."""

    SQUID_HASH = "b" * 32
    CRAWLER_HASH = "c" * 32
    EXISTING_ACCOUNT_HASH = "5" * 32
    NEW_ACCOUNT_HASH = "6" * 32

    def _fake_server(self):
        calls: list[tuple[str, str, bytes]] = []
        state = {"accounts": [self.EXISTING_ACCOUNT_HASH]}

        def _squid_json():
            return {
                "id": self.SQUID_HASH, "name": "My Squid", "crawler": self.CRAWLER_HASH,
                "crawler_name": "Sales Nav Scraper", "is_active": True, "is_ready": True,
                "concurrency": 1, "params": {},
                "accounts": [{"id": h, "status": "ok"} for h in state["accounts"]],
            }

        def handler(request: httpx.Request) -> httpx.Response:
            method, path = request.method, request.url.path
            calls.append((method, path, request.content))

            if method == "GET" and path == "/v1/squids":
                return httpx.Response(200, json={"data": [_squid_json()], "total_pages": 1})
            if method == "GET" and path == f"/v1/squids/{self.SQUID_HASH}":
                return httpx.Response(200, json=_squid_json())
            if method == "GET" and path == f"/v1/crawlers/{self.CRAWLER_HASH}":
                return httpx.Response(200, json={
                    "id": self.CRAWLER_HASH, "name": "Sales Nav Scraper", "slug": "sales-nav-scraper",
                    "account": {"type": "sales-nav-sync", "baseurl": "", "cookies": [], "icon": ""},
                })
            if method == "GET" and path == "/v1/accounts":
                return httpx.Response(200, json={"data": [
                    {"id": self.NEW_ACCOUNT_HASH, "username": "second-user",
                     "type": "sales-nav-sync", "status": "200"},
                ], "total_pages": 1})
            if method == "POST" and path == f"/v1/squids/{self.SQUID_HASH}":
                body = _json.loads(request.content or b"{}")
                if "accounts" in body:
                    state["accounts"] = body["accounts"]
                return httpx.Response(200, json={})

            raise AssertionError(f"unexpected request: {method} {path}")

        return handler, calls

    def test_update_merges_explicit_account_with_existing_one(self):
        handler, calls = self._fake_server()
        client = LobstrClient(token="t", transport=httpx.MockTransport(handler))
        with patch("lobstr_cli.cli.get_client", return_value=client):
            result = runner.invoke(app, [
                "squid", "update", self.SQUID_HASH, "--account", "second-user",
            ])

        assert result.exit_code == 0, result.output
        update_body = next(
            _json.loads(b) for m, p, b in calls
            if m == "POST" and p == f"/v1/squids/{self.SQUID_HASH}" and b"accounts" in (b or b"")
        )
        assert set(update_body["accounts"]) == {self.EXISTING_ACCOUNT_HASH, self.NEW_ACCOUNT_HASH}, update_body


class TestSquidEstimate:
    ESTIMATE = {
        "services": [{"name": "Google Maps data", "results": 300, "credits": 300}],
        "total_credits": 300, "estimated_time": "5 mins - 12 mins",
        "max_results": 800, "tasks": {"count": 8, "preview": []},
        "recommended_upgrade_plan": None,
    }

    def test_estimate(self):
        mock = _mock_client()
        mock.squids.estimate.return_value = self.ESTIMATE
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["squid", "estimate", "My Squid"])
        assert result.exit_code == 0
        mock.squids.estimate.assert_called_once_with("squid1abc123def456")
        assert "300" in result.output

    def test_estimate_json(self):
        mock = _mock_client()
        mock.squids.estimate.return_value = self.ESTIMATE
        _state["json"] = True
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "squid", "estimate", "My Squid"])
        assert result.exit_code == 0
        assert '"total_credits"' in result.output


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
