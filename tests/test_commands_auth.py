import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state
from lobstrio.models.user import User, Balance


runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


class TestSetToken:
    def test_saves_token(self, tmp_path):
        with patch("lobstr_cli.commands.auth.save_token") as mock_save, \
             patch("lobstr_cli.commands.auth.get_config_path", return_value=tmp_path / "config.toml"):
            result = runner.invoke(app, ["config", "set-token", "my-api-token"])
        assert result.exit_code == 0
        mock_save.assert_called_once_with("my-api-token")


class TestShowConfig:
    def test_shows_masked_token(self):
        with patch("lobstr_cli.commands.auth.load_config", return_value={
            "auth": {"token": "abcdefghijklmnop"},
        }), patch("lobstr_cli.commands.auth.get_config_path", return_value="/fake/path"):
            result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "abcdefgh..." in result.output

    def test_no_token_set(self):
        with patch("lobstr_cli.commands.auth.load_config", return_value={}), \
             patch("lobstr_cli.commands.auth.get_config_path", return_value="/fake/path"):
            result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "not set" in result.output

    def test_json_mode(self):
        with patch("lobstr_cli.commands.auth.load_config", return_value={
            "auth": {"token": "abcdefghijklmnop"},
        }), patch("lobstr_cli.commands.auth.get_config_path", return_value="/fake"):
            result = runner.invoke(app, ["--json", "config", "show"])
        assert result.exit_code == 0
        assert "abcdefgh..." in result.output

    def test_shows_aliases(self):
        with patch("lobstr_cli.commands.auth.load_config", return_value={
            "auth": {"token": "abcdefghijklmnop"},
            "aliases": {"maps": "abc123def456"},
        }), patch("lobstr_cli.commands.auth.get_config_path", return_value="/fake"):
            result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "@maps" in result.output


class TestSetAlias:
    def test_creates_alias(self):
        with patch("lobstr_cli.commands.auth.save_alias") as mock_save:
            result = runner.invoke(app, ["config", "set-alias", "myalias", "abc123def456"])
        assert result.exit_code == 0
        mock_save.assert_called_once_with("myalias", "abc123def456")


class TestWhoami:
    def _mock_client(self):
        mock = MagicMock()
        mock.me.return_value = User(
            first_name="John", last_name="Doe",
            email="john@example.com", is_staff=False,
            plan=[{"name": "Pro", "status": "active"}],
        )
        mock.balance.return_value = Balance(
            available=1000, consumed=500, used_slots=2, total_available_slots=5,
        )
        return mock

    def test_whoami_display(self):
        mock = self._mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 0
        assert "John Doe" in result.output
        assert "john@example.com" in result.output
        assert "Pro" in result.output
        assert "1000 credits" in result.output

    def test_whoami_json(self):
        mock = self._mock_client()
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "whoami"])
        assert result.exit_code == 0
        assert "john@example.com" in result.output

    def test_whoami_no_plan(self):
        mock = MagicMock()
        mock.me.return_value = User(
            first_name="", last_name="", email="a@b.com", is_staff=False, plan=[],
        )
        mock.balance.return_value = Balance(available=0, consumed=0, used_slots=0, total_available_slots=0)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 0
