import pytest
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


def _mock_client(get_resp=None, post_resp=None):
    mock = MagicMock()
    mock.get.side_effect = get_resp or (lambda path, **kw: SQUIDS)
    mock.post.return_value = post_resp or {}
    return mock


class TestDeliveryEmail:
    def test_configure_email(self):
        mock = _mock_client(post_resp={"email": "user@example.com", "notifications": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "email", "My Squid", "--email", "user@example.com"])
        assert result.exit_code == 0
        assert mock.post.call_args[0][0] == "/delivery"
        assert mock.post.call_args[1]["params"] == {"squid": "squid1abc123def456"}
        call_json = mock.post.call_args[1]["json"]
        assert call_json["email"] == "user@example.com"
        assert call_json["notifications"] is True

    def test_configure_email_no_notifications(self):
        mock = _mock_client(post_resp={"email": "user@example.com", "notifications": False})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "email", "My Squid", "--email", "user@example.com", "--no-notifications"])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["notifications"] is False

    def test_email_json_mode(self):
        mock = _mock_client(post_resp={"email": "user@example.com"})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "delivery", "email", "My Squid", "--email", "user@example.com"])
        assert result.exit_code == 0


class TestDeliveryGoogleSheet:
    def test_configure_googlesheet(self):
        mock = _mock_client(post_resp={"google_sheet_fields": {"url": "https://docs.google.com/spreadsheets/d/123", "is_active": True, "append": False}})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "googlesheet", "My Squid", "--url", "https://docs.google.com/spreadsheets/d/123"])
        assert result.exit_code == 0
        assert "configured" in result.output

    def test_configure_with_append(self):
        mock = _mock_client(post_resp={"google_sheet_fields": {"url": "https://...", "append": True, "is_active": True}})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "googlesheet", "My Squid", "--url", "https://...", "--append"])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["google_sheet_fields"]["append"] is True


class TestDeliveryS3:
    def test_configure_s3(self):
        mock = _mock_client(post_resp={"s3_fields": {"bucket": "mybucket", "target_path": "exports", "is_active": True}})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "s3", "My Squid", "--bucket", "mybucket", "--target-path", "exports"])
        assert result.exit_code == 0
        assert "configured" in result.output

    def test_s3_with_credentials(self):
        mock = _mock_client(post_resp={"s3_fields": {"bucket": "b", "target_path": "p", "is_active": True}})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "delivery", "s3", "My Squid",
                "--bucket", "b", "--target-path", "p",
                "--aws-access-key", "AKIA...", "--aws-secret-key", "secret",
            ])
        assert result.exit_code == 0
        call_json = mock.post.call_args[1]["json"]
        assert call_json["s3_fields"]["aws_access_key"] == "AKIA..."


class TestDeliveryWebhook:
    def test_configure_webhook(self):
        mock = _mock_client(post_resp={"webhook_fields": {"url": "https://hook.example.com", "is_active": True, "retry": True}})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "webhook", "My Squid", "--url", "https://hook.example.com"])
        assert result.exit_code == 0
        assert "configured" in result.output
        call_json = mock.post.call_args[1]["json"]
        assert call_json["webhook_fields"]["events"]["run.done"] is True


class TestDeliverySftp:
    def test_configure_sftp(self):
        mock = _mock_client(post_resp={"ftp_fields": {"host": "sftp.example.com", "port": 22, "is_active": True}})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "delivery", "sftp", "My Squid",
                "--host", "sftp.example.com",
                "--username", "user", "--password", "pass",
                "--directory", "/upload",
            ])
        assert result.exit_code == 0
        assert "configured" in result.output


class TestDeliveryTests:
    def test_test_email_pass(self):
        mock = _mock_client(post_resp={"success": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-email", "--email", "user@example.com"])
        assert result.exit_code == 0
        assert "passed" in result.output

    def test_test_email_fail(self):
        mock = _mock_client(post_resp={"success": False})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-email", "--email", "bad@example.com"])
        assert result.exit_code == 1

    def test_test_googlesheet(self):
        mock = _mock_client(post_resp={"success": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-googlesheet", "--url", "https://docs.google.com/..."])
        assert result.exit_code == 0

    def test_test_s3(self):
        mock = _mock_client(post_resp={"success": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-s3", "--bucket", "mybucket"])
        assert result.exit_code == 0

    def test_test_webhook(self):
        mock = _mock_client(post_resp={"success": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["delivery", "test-webhook", "--url", "https://hook.example.com"])
        assert result.exit_code == 0

    def test_test_sftp(self):
        mock = _mock_client(post_resp={"success": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, [
                "delivery", "test-sftp",
                "--host", "sftp.example.com",
                "--username", "user", "--password", "pass",
                "--directory", "/upload",
            ])
        assert result.exit_code == 0

    def test_test_json_mode(self):
        mock = _mock_client(post_resp={"success": True})
        with patch("lobstr_cli.cli.get_client", return_value=mock):
            result = runner.invoke(app, ["--json", "delivery", "test-email", "--email", "user@example.com"])
        assert result.exit_code == 0
