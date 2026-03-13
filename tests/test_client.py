"""Tests for SDK client integration (error types and basic connectivity)."""
import pytest
from lobstrio.exceptions import APIError, AuthError, NotFoundError, RateLimitError


class TestErrorTypes:
    def test_auth_error_is_api_error(self):
        assert issubclass(AuthError, APIError)

    def test_not_found_error_is_api_error(self):
        assert issubclass(NotFoundError, APIError)

    def test_rate_limit_error_is_api_error(self):
        assert issubclass(RateLimitError, APIError)

    def test_api_error_has_status_code(self):
        e = APIError(400, "Bad request", {"error": "Bad request"})
        assert e.status_code == 400
        assert "Bad request" in str(e)

    def test_auth_error_message(self):
        e = AuthError(401, "Invalid token", {})
        assert e.status_code == 401
        assert "Invalid token" in str(e)


class TestClientImport:
    def test_can_import_client(self):
        from lobstrio import LobstrClient
        assert LobstrClient is not None

    def test_client_requires_token(self):
        from lobstrio import LobstrClient
        from unittest.mock import patch
        import os
        # Remove env var and mock config to ensure no token found
        old = os.environ.pop("LOBSTR_TOKEN", None)
        try:
            with patch("lobstrio.client._resolve_token", return_value=None):
                with pytest.raises(ValueError, match="No API token"):
                    LobstrClient(token=None)
        finally:
            if old:
                os.environ["LOBSTR_TOKEN"] = old
