import pytest
import json
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from lobstr_cli.cli import app, _state


runner = CliRunner()

SQUIDS = {
    "data": [
        {"id": "squid1abc123def456", "name": "My Squid"},
    ]
}


@pytest.fixture(autouse=True)
def clean_state():
    _state.clear()
    yield
    _state.clear()


def _mock_client(get_resp):
    mock = MagicMock()
    mock.get.side_effect = get_resp
    return mock


class TestResultsGet:
    def _get_resp(self, path, **kw):
        if path == "/squids":
            return SQUIDS
        return {"data": [
            {"id": "r1", "url": "https://a.com", "title": "Page A", "squid": "s1"},
            {"id": "r2", "url": "https://b.com", "title": "Page B", "squid": "s1"},
        ]}

    def test_get_json_format(self):
        mock = _mock_client(self._get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid"])
        assert result.exit_code == 0
        assert "https://a.com" in result.output

    def test_get_csv_format(self):
        mock = _mock_client(self._get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--format", "csv"])
        assert result.exit_code == 0
        assert "url" in result.output

    def test_get_save_json(self, tmp_path):
        out_file = tmp_path / "out.json"
        mock = _mock_client(self._get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert len(data["data"]) == 2

    def test_get_save_csv(self, tmp_path):
        out_file = tmp_path / "out.csv"
        mock = _mock_client(self._get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--format", "csv", "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "url" in content
        assert "https://a.com" in content

    def test_get_empty_results(self):
        def get_resp(path, **kw):
            if path == "/squids":
                return SQUIDS
            return {"data": []}
        mock = _mock_client(get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--format", "csv"])
        assert result.exit_code == 0

    def test_get_with_pagination(self):
        mock = _mock_client(self._get_resp)
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["results", "get", "My Squid", "--page", "2", "--page-size", "10"])
        assert result.exit_code == 0
        # Check params passed to API
        calls = mock.get.call_args_list
        results_call = [c for c in calls if c[0][0] == "/results"][0]
        assert results_call[1]["params"]["page"] == 2
        assert results_call[1]["params"]["page_size"] == 10
