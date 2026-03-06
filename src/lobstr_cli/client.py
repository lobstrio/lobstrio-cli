from __future__ import annotations

import httpx


class APIError(Exception):
    def __init__(self, status_code: int, message: str, body: dict | None = None):
        self.status_code = status_code
        self.message = message
        self.body = body or {}
        super().__init__(f"[{status_code}] {message}")


class AuthError(APIError):
    pass


class NotFoundError(APIError):
    pass


class RateLimitError(APIError):
    pass


BASE_URL = "https://api.lobstr.io/v1/"


class LobstrClient:
    def __init__(self, token: str, verbose: bool = False):
        self.verbose = verbose
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"authorization": f"Token {token}"},
            timeout=30.0,
        )

    def _handle_response(self, resp: httpx.Response) -> dict:
        if self.verbose:
            import sys
            print(f"  {resp.request.method} {resp.request.url} -> {resp.status_code}", file=sys.stderr)

        body = {}
        try:
            body = resp.json()
        except Exception:
            pass

        if resp.status_code >= 400:
            # API returns errors in different shapes
            msg = (
                body.get("error")
                or (body.get("errors", {}).get("message") if isinstance(body.get("errors"), dict) else None)
                or resp.text
            )
            if resp.status_code == 401:
                raise AuthError(401, msg or "Authentication failed", body)
            if resp.status_code == 404:
                raise NotFoundError(404, msg or "Not found", body)
            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after", "?")
                raise RateLimitError(429, f"Rate limited. Retry after {retry_after}s", body)
            raise APIError(resp.status_code, msg, body)

        return body

    def get(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(path, params=params)
        return self._handle_response(resp)

    def post(self, path: str, json: dict | None = None, data: dict | None = None, files: dict | None = None, params: dict | None = None) -> dict:
        resp = self._client.post(path, json=json, data=data, files=files, params=params)
        return self._handle_response(resp)

    def delete(self, path: str) -> dict:
        resp = self._client.delete(path)
        return self._handle_response(resp)

    def download(self, url: str, dest: str) -> None:
        """Download a file from a full URL (e.g., S3 signed URL) to dest path."""
        with httpx.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)

    def close(self) -> None:
        self._client.close()
