"""
tests_api/test_api_auth.py
─────────────────────────────────────────────────────────────────────────────
Integration tests — AuthController  (POST /api/auth/login, POST /api/auth/register)

These tests send REAL HTTP requests to the running .NET backend.
Every assertion hits the actual database through the real controller.

Technique : EC (Equivalence Partitioning) + BVA (Boundary Value Analysis)
Level     : Integration
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from helpers import api, unique_email


class TestAuthLogin:

    # TC-API-L01 | EC — valid class | Integration
    def test_login_valid_credentials_returns_200_and_token(self):
        """TC-API-L01 | EC — valid class: correct email + password
        POST /api/auth/login must return 200 and a JWT token."""
        res = api("POST", "/api/auth/login", {
            "email":    "admin@shopverse.com",
            "password": "admin123"
        })
        assert res.status_code == 200
        body = res.json()
        assert "token"  in body, "Response must contain 'token'"
        assert "email"  in body
        assert "role"   in body
        assert len(body["token"]) > 20, "Token must be a non-trivial JWT string"

    # TC-API-L02 | EC — invalid class: wrong password | Integration
    def test_login_wrong_password_returns_401(self):
        """TC-API-L02 | EC — invalid class: correct email, wrong password
        POST /api/auth/login must return 401 Unauthorized."""
        res = api("POST", "/api/auth/login", {
            "email":    "admin@shopverse.com",
            "password": "totallyWrongPassword"
        })
        assert res.status_code == 401

    # TC-API-L03 | EC — invalid class: non-existent user | Integration
    def test_login_unknown_email_returns_401(self):
        """TC-API-L03 | EC — invalid class: email not in DB
        POST /api/auth/login must return 401 for an unknown email."""
        res = api("POST", "/api/auth/login", {
            "email":    "nobody@nowhere.com",
            "password": "doesntmatter"
        })
        assert res.status_code == 401

    # TC-API-L04 | BVA — boundary: empty fields | Integration
    def test_login_empty_email_returns_400_or_401(self):
        """TC-API-L04 | BVA — boundary: empty email (length = 0)
        POST /api/auth/login with empty email must not return 200."""
        res = api("POST", "/api/auth/login", {
            "email":    "",
            "password": "Admin123"
        })
        assert res.status_code in (400, 401)

    # TC-API-L05 | BVA — boundary: empty password | Integration
    def test_login_empty_password_returns_400_or_401(self):
        """TC-API-L05 | BVA — boundary: empty password (length = 0)
        POST /api/auth/login with empty password must not return 200."""
        res = api("POST", "/api/auth/login", {
            "email":    "admin@shopverse.com",
            "password": ""
        })
        assert res.status_code in (400, 401)

    # TC-API-L06 | EC — invalid class: suspended account | Integration
    def test_login_suspended_user_returns_401(self, admin_token, registered_user):
        """TC-API-L06 | EC — invalid class: suspended account
        A suspended user must get 401 on login even with correct credentials.
        Tests the interaction: AuthController → DB (User.Status check)."""
        user_id = registered_user["id"]

        # Admin suspends the user
        suspend_res = api("PATCH", f"/api/users/{user_id}/status",
                          {"status": "suspended"}, token=admin_token)
        assert suspend_res.status_code == 200

        # Suspended user tries to log in
        login_res = api("POST", "/api/auth/login", {
            "email":    registered_user["email"],
            "password": registered_user["password"],
        })
        assert login_res.status_code == 401
        assert "suspended" in login_res.json().get("message", "").lower()

    # TC-API-L07 | EC — valid class: response shape | Integration
    def test_login_response_contains_all_required_fields(self):
        """TC-API-L07 | EC — valid class: AuthResponse DTO completeness
        Login response must contain id, name, email, role, status, token."""
        res = api("POST", "/api/auth/login", {
            "email":    "admin@shopverse.com",
            "password": "Admin123"
        })
        assert res.status_code == 200
        body = res.json()
        for field in ("id", "name", "email", "role", "status", "token"):
            assert field in body, f"Missing field '{field}' in AuthResponse"

    # TC-API-L08 | EC — valid class: admin role | Integration
    def test_login_admin_returns_role_admin(self):
        """TC-API-L08 | EC — valid class: admin credentials must return role='admin'."""
        res = api("POST", "/api/auth/login", {
            "email":    "admin@shopverse.com",
            "password": "admin123"
        })
        assert res.status_code == 200
        assert res.json()["role"] == "admin"


class TestAuthRegister:

    # TC-API-R01 | EC — valid class | Integration
    def test_register_new_user_returns_201_and_token(self):
        """TC-API-R01 | EC — valid class: all required fields provided
        POST /api/auth/register must return 201 with a token."""
        res = api("POST", "/api/auth/register", {
            "name":     "New User",
            "email":    unique_email("register"),
            "password": "SecurePass123",
        })
        assert res.status_code == 201
        body = res.json()
        assert "token" in body
        assert body["role"] == "user"

    # TC-API-R02 | EC — invalid class: duplicate email | Integration
    def test_register_duplicate_email_returns_409(self, registered_user):
        """TC-API-R02 | EC — invalid class: email already in DB
        POST /api/auth/register with an existing email must return 409 Conflict."""
        res = api("POST", "/api/auth/register", {
            "name":     "Another User",
            "email":    registered_user["email"],  # already registered
            "password": "AnotherPass123",
        })
        assert res.status_code == 409

    # TC-API-R03 | BVA — boundary: missing required fields | Integration
    def test_register_missing_name_returns_400(self):
        """TC-API-R03 | BVA — boundary: name field absent
        POST /api/auth/register without name must return 400."""
        res = api("POST", "/api/auth/register", {
            "email":    unique_email("noname"),
            "password": "Pass123",
        })
        assert res.status_code == 400

    # TC-API-R04 | EC — valid class: registered user can immediately log in | Integration
    def test_register_then_login_works(self):
        """TC-API-R04 | EC — valid class: register → login chain
        A newly registered user must be able to log in immediately.
        Tests the module interaction: AuthController.Register → DB → AuthController.Login."""
        email    = unique_email("chaintest")
        password = "ChainPass123"

        reg = api("POST", "/api/auth/register", {
            "name": "Chain User", "email": email, "password": password
        })
        assert reg.status_code == 201

        login = api("POST", "/api/auth/login", {
            "email": email, "password": password
        })
        assert login.status_code == 200
        assert "token" in login.json()

    # TC-API-R05 | EC — valid class: response shape | Integration
    def test_register_response_shape(self):
        """TC-API-R05 | EC — valid class: AuthResponse DTO completeness after register."""
        res = api("POST", "/api/auth/register", {
            "name":     "Shape User",
            "email":    unique_email("shape"),
            "password": "ShapePass123",
        })
        assert res.status_code == 201
        body = res.json()
        for field in ("id", "name", "email", "role", "status", "token"):
            assert field in body, f"Missing field '{field}' in register response"
        assert body["status"] == "active"
        assert body["role"]   == "user"
