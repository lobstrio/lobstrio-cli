import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state


runner = CliRunner()

ACCOUNTS = {
    "data": [
        {
            "id": "acc1abc123def456",
            "username": "johndoe",
            "type": "twitter-sync",
            "status_code_info": "synchronized",
            "status_code_description": "Account is synced",
            "last_synchronization_time": "2025-01-15T10:00:00Z",
            "baseurl": "https://twitter.com",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": None,
            "squids": [{"name": "Twitter Scraper", "hash_value": "squid1"}],
        },
    ]
}

ACCOUNT_TYPES = [
    {
        "id": "type1",
        "name": "twitter-sync",
        "domain": "Twitter",
        "baseurl": "https://twitter.com",
        "cookies": [{"name": "auth_token", "required": True}],
    },
]


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(get_resp=None):
    mock = MagicMock()
    if callable(get_resp):
        mock.get.side_effect = get_resp
    else:
        mock.get.return_value = get_resp or ACCOUNTS
    mock.post.return_value = {"id": "sync123", "object": "synchronize-cookies", "status_code": 100, "status_text": "created"}
    mock.delete.return_value = {"id": "acc1abc123def456", "object": "account", "deleted": "true"}
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
        single_account = {"data": [ACCOUNTS["data"][0]]}
        def get_resp(path, **kw):
            if path == "/accounts":
                return ACCOUNTS
            return single_account
        mock = _mock_client(get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "show", "johndoe"])
        assert result.exit_code == 0
        assert "johndoe" in result.output
        assert "twitter-sync" in result.output

    def test_show_json(self):
        single_account = {"data": [ACCOUNTS["data"][0]]}
        def get_resp(path, **kw):
            if path == "/accounts":
                return ACCOUNTS
            return single_account
        mock = _mock_client(get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "show", "johndoe"])
        assert result.exit_code == 0
        assert "acc1abc123def456" in result.output


class TestAccountsRm:
    def test_delete_with_force(self):
        mock = _mock_client()
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
        mock = _mock_client(lambda path, **kw: ACCOUNT_TYPES)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "types"])
        assert result.exit_code == 0
        assert "twitter-sync" in result.output
        assert "Twitter" in result.output

    def test_types_json(self):
        mock = _mock_client(lambda path, **kw: ACCOUNT_TYPES)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "types"])
        assert result.exit_code == 0


class TestAccountsSync:
    def test_sync_new(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "sync", "twitter-sync", "--cookie", "auth_token=abc123"])
        assert result.exit_code == 0
        assert "Sync started" in result.output
        call_json = mock.post.call_args[1]["json"]
        assert call_json["type"] == "twitter-sync"
        assert call_json["cookies"]["auth_token"] == "abc123"

    def test_sync_refresh(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "sync", "twitter-sync",
                "--account", "acc1abc123def456",
                "--cookie", "auth_token=newtoken",
            ])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["account"] == "acc1abc123def456"
        assert call_json["cookies"]["auth_token"] == "newtoken"

    def test_sync_json_cookies(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "sync", "twitter-sync",
                "--cookies-json", '{"auth_token": "abc", "ct0": "xyz"}',
            ])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["cookies"]["auth_token"] == "abc"
        assert call_json["cookies"]["ct0"] == "xyz"

    def test_sync_file_cookies(self, tmp_path):
        cookie_file = tmp_path / "cookies.json"
        cookie_file.write_text('{"auth_token": "fromfile"}')
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "sync", "twitter-sync",
                "--cookies-file", str(cookie_file),
            ])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["cookies"]["auth_token"] == "fromfile"

    def test_sync_no_cookies_error(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "sync", "twitter-sync"])
        assert result.exit_code != 0

    def test_sync_json_mode(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "accounts", "sync", "twitter-sync", "--cookie", "auth_token=abc"])
        assert result.exit_code == 0
        assert "sync123" in result.output


class TestAccountsSyncStatus:
    def test_sync_status(self):
        mock = _mock_client(lambda path, **kw: {
            "id": "sync123", "status_code": 200, "status_text": "synchronized", "account_hash": "acc1abc123def456"
        })
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "sync-status", "sync123"])
        assert result.exit_code == 0
        assert "synchronized" in result.output


class TestAccountsUpdate:
    def test_update_limits(self):
        mock = _mock_client()
        mock.post.return_value = {"params": {"default": {}, "user": {}}}
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "accounts", "update", "johndoe",
                "--type", "sales-nav-sync",
                "--param", "batch=20",
                "--param", "profiles=150",
            ])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["params"]["batch"] == 20
        assert call_json["params"]["profiles"] == 150

    def test_update_no_params_error(self):
        mock = _mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["accounts", "update", "johndoe", "--type", "twitter-sync"])
        assert result.exit_code != 0
