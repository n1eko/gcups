"""Minimal client for the GC UPS app's REST API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class GcupsApiError(Exception):
    """The API could not be reached, rejected the request, or returned garbage."""


class GcupsClient:
    """Logs in once and reuses the token until the API rejects it."""

    def __init__(self, base_url: str, password: str, timeout_seconds: float) -> None:
        self._api_url = f"{base_url}/api"
        self._password = password
        self._timeout = timeout_seconds
        self._token: str | None = None

    def get(self, path: str) -> Any:
        """GET an API path, logging in first or again if needed.

        Returns None for an empty body, which the app sends for UPS endpoints
        while no UPS is attached.
        """
        try:
            if self._token is None:
                self._login()
            try:
                return self._request(path)
            except urllib.error.HTTPError as e:
                if e.code != 401:
                    raise
                self._login()
                return self._request(path)
        except (OSError, ValueError, KeyError) as e:  # URLError/HTTPError are OSErrors
            raise GcupsApiError(f"GET {path}: {e}") from e

    def _login(self) -> None:
        response = self._request("/login", body={"password": self._password}, authenticated=False)
        self._token = response["access_token"]

    def _request(self, path: str, body: dict | None = None, authenticated: bool = True) -> Any:
        headers = {"Content-Type": "application/json"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self._token}"
        data = json.dumps(body).encode() if body is not None else None

        request = urllib.request.Request(f"{self._api_url}{path}", data=data, headers=headers)
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            body = response.read()
        return json.loads(body) if body.strip() else None
