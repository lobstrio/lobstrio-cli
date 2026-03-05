import pytest
import httpx
from pytest_httpx import HTTPXMock
from lobstr_cli.client import LobstrClient, AuthError, NotFoundError, RateLimitError, APIError


@pytest.fixture
def client():
    return LobstrClient(token="test-token")


# --- Client setup ---

class TestClientSetup:
    def test_auth_header(self, client: LobstrClient):
        assert client._client.headers["authorization"] == "Token test-token"

    def test_base_url(self, client: LobstrClient):
        assert str(client._client.base_url) == "https://api.lobstr.io/v1/"

    def test_timeout(self, client: LobstrClient):
        assert client._client.timeout.read == 30.0

    def test_verbose_default_false(self, client: LobstrClient):
        assert client.verbose is False

    def test_verbose_enabled(self):
        c = LobstrClient(token="t", verbose=True)
        assert c.verbose is True


# --- GET requests ---

class TestGet:
    def test_get_me(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/me",
            json={"id": "u1", "email": "test@example.com"},
        )
        result = client.get("/me")
        assert result["email"] == "test@example.com"

    def test_get_with_params(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/squids?limit=10&page=2",
            json={"data": [], "total": 0},
        )
        result = client.get("/squids", params={"limit": 10, "page": 2})
        assert result["data"] == []

    def test_get_returns_dict(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/crawlers",
            json={"data": [{"id": "c1"}]},
        )
        result = client.get("/crawlers")
        assert isinstance(result, dict)


# --- POST requests ---

class TestPost:
    def test_post_json(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/squids",
            json={"id": "sq1", "name": "Test Squid"},
        )
        result = client.post("/squids", json={"crawler": "abc123"})
        assert result["id"] == "sq1"

    def test_post_without_body(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/runs/r1/abort",
            json={"status": "aborted"},
        )
        result = client.post("/runs/r1/abort")
        assert result["status"] == "aborted"


# --- DELETE requests ---

class TestDelete:
    def test_delete(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/squids/abc123",
            json={"id": "abc123", "deleted": True},
        )
        result = client.delete("/squids/abc123")
        assert result["deleted"] is True


# --- Error handling ---

class TestErrors:
    def test_auth_error_401(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/me",
            status_code=401,
            json={"error": "Invalid token"},
        )
        with pytest.raises(AuthError) as exc_info:
            client.get("/me")
        assert exc_info.value.status_code == 401
        assert "Invalid token" in str(exc_info.value)

    def test_not_found_error_404(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/squids/nonexist",
            status_code=404,
            json={"error": "Not found"},
        )
        with pytest.raises(NotFoundError) as exc_info:
            client.get("/squids/nonexist")
        assert exc_info.value.status_code == 404

    def test_rate_limit_error_429(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/crawlers",
            status_code=429,
            headers={"retry-after": "30"},
            json={},
        )
        with pytest.raises(RateLimitError) as exc_info:
            client.get("/crawlers")
        assert "30" in str(exc_info.value)

    def test_api_error_400(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/runs",
            status_code=400,
            json={"error": "Squid has no tasks"},
        )
        with pytest.raises(APIError, match="Squid has no tasks"):
            client.post("/runs", json={"squid": "abc"})

    def test_api_error_500(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/runs/bad",
            status_code=500,
            json={"error": "Something went wrong"},
        )
        with pytest.raises(APIError) as exc_info:
            client.get("/runs/bad")
        assert exc_info.value.status_code == 500

    def test_errors_dict_format(self, client: LobstrClient, httpx_mock: HTTPXMock):
        """API returns errors as {"errors": {"message": "...", "type": "...", "code": N}}"""
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/tasks",
            status_code=400,
            json={"errors": {"message": "Invalid param: url.", "type": "validation_error", "code": 400}},
        )
        with pytest.raises(APIError, match="Invalid param: url"):
            client.post("/tasks", json={"squid": "s1", "tasks": []})

    def test_error_plain_text_fallback(self, client: LobstrClient, httpx_mock: HTTPXMock):
        """When response isn't JSON, use resp.text as error message."""
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/broken",
            status_code=502,
            text="Bad Gateway",
        )
        with pytest.raises(APIError, match="Bad Gateway"):
            client.get("/broken")

    def test_error_body_preserved(self, client: LobstrClient, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/runs",
            status_code=400,
            json={"error": "msg", "extra": "data"},
        )
        with pytest.raises(APIError) as exc_info:
            client.post("/runs", json={})
        assert exc_info.value.body == {"error": "msg", "extra": "data"}

    def test_auth_error_is_api_error(self):
        assert issubclass(AuthError, APIError)

    def test_not_found_error_is_api_error(self):
        assert issubclass(NotFoundError, APIError)

    def test_rate_limit_error_is_api_error(self):
        assert issubclass(RateLimitError, APIError)


# --- Verbose mode ---

class TestVerbose:
    def test_verbose_prints_request(self, httpx_mock: HTTPXMock, capsys):
        client = LobstrClient(token="t", verbose=True)
        httpx_mock.add_response(
            url="https://api.lobstr.io/v1/me",
            json={"id": "1"},
        )
        client.get("/me")
        captured = capsys.readouterr()
        assert "GET" in captured.err
        assert "200" in captured.err
