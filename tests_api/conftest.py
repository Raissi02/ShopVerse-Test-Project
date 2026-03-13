"""
tests_api/conftest.py
─────────────────────────────────────────────────────────────────────────────
Shared fixtures and helpers for all API-level pytest tests.

Every test in this folder sends REAL HTTP requests to the running .NET backend.
Start the backend first:
    cd ShopVerseAPI && dotnet run          (listens on http://localhost:5000)

Tool     : pytest  (listed in guideline §5.1)
Library  : requests (standard HTTP client — no mocking)
Level    : Integration + System
─────────────────────────────────────────────────────────────────────────────
"""

import pytest

from config import ADMIN_EMAIL, ADMIN_PASSWORD, TEST_USER_PASSWORD
from helpers import api, unique_email


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_token() -> str:
    """
    Log in as the seeded demo admin once per test session.
    Returns the JWT token string.
    scope="session" — one login shared across all tests in the session.
    """
    res = api("POST", "/api/auth/login", {
        "email":    ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
    })
    assert res.status_code == 200, (
        f"Admin login failed ({res.status_code}). "
        "Make sure the backend is running and the demo admin is seeded."
    )
    return res.json()["token"]


@pytest.fixture(scope="function")
def user_token() -> str:
    """
    Register a brand-new user for this test function, then return its JWT.
    scope="function" — unique user per test, no shared state.
    """
    email    = unique_email("user")
    res = api("POST", "/api/auth/register", {
        "name":     "Test User",
        "email":    email,
        "password": TEST_USER_PASSWORD,
    })
    assert res.status_code == 201, f"Registration failed: {res.text}"
    return res.json()["token"]


@pytest.fixture(scope="function")
def registered_user() -> dict:
    """
    Register a brand-new user and return credentials + token as a dict.
    Useful when a test needs both the token and the email/password afterwards.
    """
    email    = unique_email("reguser")
    res = api("POST", "/api/auth/register", {
        "name":     "Reg User",
        "email":    email,
        "password": TEST_USER_PASSWORD,
    })
    assert res.status_code == 201, f"Registration failed: {res.text}"
    data = res.json()
    return {
        "id":       data["id"],
        "email":    email,
        "password": TEST_USER_PASSWORD,
        "token":    data["token"],
        "name":     data["name"],
        "role":     data["role"],
    }


@pytest.fixture(scope="session")
def first_product(admin_token) -> dict:
    """
    Fetch the first active product from the catalogue.
    Used by order tests that need a valid productId.
    """
    res = api("GET", "/api/products?pageSize=1")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) > 0, "No products in DB — seed the database first."
    return data[0]


@pytest.fixture(scope="session")
def first_category() -> dict:
    """Fetch the first category from the catalogue."""
    res = api("GET", "/api/categories")
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) > 0, "No categories in DB."
    return cats[0]
