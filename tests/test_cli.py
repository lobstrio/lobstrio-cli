import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, get_client, _state


runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_state():
    """Reset shared state before each test."""
    _state.clear()
    yield
    _state.clear()


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "lobstr" in result.output

    def test_no_args_shows_help(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "Usage" in result.output or "lobstr" in result.output


class TestGlobalFlags:
    def test_json_flag_sets_state(self):
        with patch("lobstr_cli.cli.get_token", return_value="t"):
            result = runner.invoke(app, ["--json", "--version"])
        assert result.exit_code == 0

    def test_verbose_flag(self):
        result = runner.invoke(app, ["--verbose", "--version"])
        assert result.exit_code == 0

    def test_quiet_flag(self):
        result = runner.invoke(app, ["--quiet", "--version"])
        assert result.exit_code == 0


class TestGetClient:
    def test_no_token_exits(self):
        with patch("lobstr_cli.cli.get_token", return_value=None):
            with pytest.raises((SystemExit, Exception)):
                get_client()

    def test_creates_client_with_token(self):
        _state["token"] = "test-token-123"
        with patch("lobstr_cli.cli.get_token", return_value="test-token-123"):
            client = get_client()
        assert client is not None
        assert "client" in _state

    def test_reuses_existing_client(self):
        mock_client = MagicMock()
        _state["client"] = mock_client
        assert get_client() is mock_client


class TestSubcommands:
    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "set-token" in result.output

    def test_crawlers_help(self):
        result = runner.invoke(app, ["crawlers", "--help"])
        assert result.exit_code == 0

    def test_squid_help(self):
        result = runner.invoke(app, ["squid", "--help"])
        assert result.exit_code == 0

    def test_task_help(self):
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0

    def test_run_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0

    def test_results_help(self):
        result = runner.invoke(app, ["results", "--help"])
        assert result.exit_code == 0
