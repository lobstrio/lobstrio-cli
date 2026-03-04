import pytest
import httpx
from pytest_httpx import HTTPXMock
from lobstr_cli.client import LobstrClient, AuthError, NotFoundError, APIError


@pytest.fixture
def client():
    return LobstrClient(token="test-token")


def test_client_auth_header(client: LobstrClient):
    assert client._client.headers["authorization"] == "Token test-token"


def test_client_base_url(client: LobstrClient):
    assert str(client._client.base_url) == "https://api.lobstr.io/v1/"


def test_get_me(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/me",
        json={"id": "u1", "email": "test@example.com", "name": "Test"},
    )
    result = client.get("/me")
    assert result["email"] == "test@example.com"


def test_post_json(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/squids",
        json={"id": "sq1", "name": "Test Squid"},
    )
    result = client.post("/squids", json={"crawler": "abc123"})
    assert result["id"] == "sq1"


def test_auth_error(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/me",
        status_code=401,
        json={"error": "Invalid token"},
    )
    with pytest.raises(AuthError):
        client.get("/me")


def test_not_found_error(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/squids/nonexist",
        status_code=404,
        json={"error": "Not found"},
    )
    with pytest.raises(NotFoundError):
        client.get("/squids/nonexist")


def test_api_error(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/runs",
        status_code=400,
        json={"error": "Squid has no tasks"},
    )
    with pytest.raises(APIError, match="Squid has no tasks"):
        client.post("/runs", json={"squid": "abc"})


def test_delete(client: LobstrClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.lobstr.io/v1/squids/abc123",
        json={"id": "abc123", "deleted": True},
    )
    result = client.delete("/squids/abc123")
    assert result["deleted"] is True
