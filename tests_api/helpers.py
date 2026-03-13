"""
tests_api/helpers.py
─────────────────────────────────────────────────────────────────────────────
Plain helper functions for the API test suite.

These are NOT pytest fixtures — they are regular Python functions imported
explicitly by test files that need them.

    from helpers import api, unique_email

Keeping helpers separate from conftest.py means:
  - conftest.py contains only fixtures (pytest's job)
  - helpers.py contains only utility functions (your code's job)
  - test files have explicit, readable imports
─────────────────────────────────────────────────────────────────────────────
"""

import uuid
import requests

from config import API_URL


def api(method: str, path: str, json=None, token: str = None) -> requests.Response:
    """
    Send a real HTTP request to the .NET backend and return the Response.

    Usage:
        res = api("GET",  "/api/products")
        res = api("POST", "/api/auth/login", {"email": ..., "password": ...})
        res = api("POST", "/api/orders",     {...},  token=admin_token)
    """
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(
        method,
        f"{API_URL}{path}",
        json=json,
        headers=headers,
        timeout=10,
    )


def unique_email(prefix: str = "test") -> str:
    """
    Generate a unique email address so each test run never collides with
    existing rows in the database.

    Example:  unique_email("register") → "register_a3f2c1b0@shopverse-test.com"
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}@shopverse-test.com"
