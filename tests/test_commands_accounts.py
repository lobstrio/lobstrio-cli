import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.account import Account, AccountType, SyncStatus


runner = CliRunner()

ACCOUNTS = [
    Account(
        id="acc1abc123def456", username="johndoe", type="twitter-sync",
        status_code_info="synchronized", status_code_description="Account is synced",
        baseurl="https://twitter.com", created_at="2025-01-01T00:00:00Z",
        updated_at=None, last_synchronization_time="2025-01-15T10:00:00Z",
        squids=[{"name": "Twitter Scraper", "hash_value": "squid1"}],
        params={},
    ),
]

ACCOUNT_TYPES = [
    AccountType(
        name="twitter-sync", domain="Twitter",
        baseurl="https://twitter.com",
        cookies=[{"name": "auth_token", "required": True}],
    ),
]


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client():
    mock = MagicMock()
    mock.accounts.list.return_value = ACCOUNTS
    return mock


class TestAccountsLs:
    def test_list_accounts(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "ls"])
        assert result.exit_code == 0
        assert "johndoe" in result.output

    def test_list_json(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "ls"])
        assert result.exit_code == 0
        assert "acc1abc123def456" in result.output


class TestAccountsShow:
    def test_show_by_username(self):
        mock = _mock_client()
        mock.accounts.get.return_value = ACCOUNTS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "show", "johndoe"])
        assert result.exit_code == 0
        assert "johndoe" in result.output
        assert "twitter-sync" in result.output

    def test_show_json(self):
        mock = _mock_client()
        mock.accounts.get.return_value = ACCOUNTS[0]
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "show", "johndoe"])
        assert result.exit_code == 0
        assert "acc1abc123def456" in result.output


class TestAccountsRm:
    def test_delete_with_force(self):
        mock = _mock_client()
        mock.accounts.delete.return_value = {"id": "acc1abc123def456", "deleted": "true"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "rm", "johndoe", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_aborted(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "rm", "johndoe"], input="n\n")
        assert result.exit_code != 0


class TestAccountsTypes:
    def test_list_types(self):
        mock = _mock_client()
        mock.accounts.types.return_value = ACCOUNT_TYPES
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "types"])
        assert result.exit_code == 0
        assert "twitter-sync" in result.output
        assert "Twitter" in result.output

    def test_types_json(self):
        mock = _mock_client()
        mock.accounts.types.return_value = ACCOUNT_TYPES
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "types"])
        assert result.exit_code == 0


class TestAccountsSync:
    def test_sync_new(self):
        mock = _mock_client()
        mock.accounts.sync.return_value = {"id": "sync123", "status_text": "created"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "sync", "twitter-sync", "--cookie", "auth_token=abc123"])
        assert result.exit_code == 0
        assert "Sync started" in result.output
        mock.accounts.sync.assert_called_once_with("twitter-sync", {"auth_token": "abc123"}, account=None)

    def test_sync_refresh(self):
        mock = _mock_client()
        mock.accounts.sync.return_value = {"id": "sync123", "status_text": "created"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "sync", "twitter-sync",
                "--account", "acc1abc123def456",
                "--cookie", "auth_token=newtoken",
            ])
        assert result.exit_code == 0
        mock.accounts.sync.assert_called_once_with(
            "twitter-sync", {"auth_token": "newtoken"}, account="acc1abc123def456",
        )

    def test_sync_json_cookies(self):
        mock = _mock_client()
        mock.accounts.sync.return_value = {"id": "sync123", "status_text": "created"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "sync", "twitter-sync",
                "--cookies-json", '{"auth_token": "abc", "ct0": "xyz"}',
            ])
        assert result.exit_code == 0
        call_args = mock.accounts.sync.call_args
        assert call_args[0][1]["auth_token"] == "abc"
        assert call_args[0][1]["ct0"] == "xyz"

    def test_sync_file_cookies(self, tmp_path):
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text('{"auth_token": "fromfile"}')
        mock = _mock_client()
        mock.accounts.sync.return_value = {"id": "sync123", "status_text": "created"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "sync", "twitter-sync",
                "--cookies-file", str(cookie_file),
            ])
        assert result.exit_code == 0
        call_args = mock.accounts.sync.call_args
        assert call_args[0][1]["auth_token"] == "fromfile"

    def test_sync_no_cookies_error(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "sync", "twitter-sync"])
        assert result.exit_code != 0

    def test_sync_json_mode(self):
        mock = _mock_client()
        mock.accounts.sync.return_value = {"id": "sync123", "status_text": "created"}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "sync", "twitter-sync", "--cookie", "auth_token=abc"])
        assert result.exit_code == 0
        assert "sync123" in result.output


class TestAccountsSyncStatus:
    def test_sync_status(self):
        mock = _mock_client()
        mock.accounts.sync_status.return_value = SyncStatus(
            id="sync123", status_code="200",
            status_text="synchronized", account_hash="acc1abc123def456",
        )
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "sync-status", "sync123"])
        assert result.exit_code == 0
        assert "synchronized" in result.output


class TestAccountsUpdate:
    def test_update_limits(self):
        mock = _mock_client()
        mock.accounts.update.return_value = {"params": {"default": {}, "user": {}}}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "update", "johndoe",
                "--type", "sales-nav-sync",
                "--param", "batch=20",
                "--param", "profiles=150",
            ])
        assert result.exit_code == 0
        mock.accounts.update.assert_called_once_with(
            "acc1abc123def456", type="sales-nav-sync",
            params={"batch": 20, "profiles": 150},
        )

    def test_update_no_params_error(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "update", "johndoe", "--type", "twitter-sync"])
        assert result.exit_code != 0
