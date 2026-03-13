"""
tests_api/test_api_users.py
─────────────────────────────────────────────────────────────────────────────
Integration tests — UsersController  (admin-only endpoints)
  GET    /api/users
  GET    /api/users/:id
  PATCH  /api/users/:id/status
  PATCH  /api/users/:id/role

Every test sends a REAL HTTP request to the running .NET backend.

Technique : EC + Security + Requirements-based
Level     : Integration
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from helpers import api, unique_email


class TestGetUsers:

    # TC-API-U01 | Security — admin only | Integration
    def test_get_all_users_as_admin_returns_200(self, admin_token):
        """TC-API-U01 | Security — admin role
        GET /api/users with admin JWT must return 200 and a list of users."""
        res = api("GET", "/api/users", token=admin_token)
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert len(res.json()) > 0

    # TC-API-U02 | Security — non-admin blocked | Integration
    def test_get_all_users_as_regular_user_returns_403(self, user_token):
        """TC-API-U02 | Security — regular user role must be blocked
        GET /api/users with non-admin JWT must return 403."""
        res = api("GET", "/api/users", token=user_token)
        assert res.status_code == 403

    # TC-API-U03 | Security — unauthenticated blocked | Integration
    def test_get_all_users_without_token_returns_401(self):
        """TC-API-U03 | Security — no token
        GET /api/users without JWT must return 401."""
        res = api("GET", "/api/users")
        assert res.status_code == 401

    # TC-API-U04 | Requirements-based | Integration
    def test_user_dto_contains_required_fields(self, admin_token):
        """TC-API-U04 | Requirements-based
        Each UserDto must contain id, name, email, role, status, createdAt."""
        res = api("GET", "/api/users", token=admin_token)
        assert res.status_code == 200
        users = res.json()
        u = users[0]
        for field in ("id", "name", "email", "role", "status", "createdAt"):
            assert field in u, f"Missing field '{field}' in UserDto"

    # TC-API-U05 | Requirements-based | Integration
    def test_get_user_by_id_returns_correct_user(self, admin_token, registered_user):
        """TC-API-U05 | Requirements-based
        GET /api/users/:id must return the user with the matching id."""
        uid = registered_user["id"]
        res = api("GET", f"/api/users/{uid}", token=admin_token)
        assert res.status_code == 200
        assert res.json()["id"] == uid
        assert res.json()["email"] == registered_user["email"]

    # TC-API-U06 | EC — invalid class: non-existent id | Integration
    def test_get_user_by_nonexistent_id_returns_404(self, admin_token):
        """TC-API-U06 | EC — invalid class: id not in DB
        GET /api/users/999999 must return 404."""
        res = api("GET", "/api/users/999999", token=admin_token)
        assert res.status_code == 404


class TestUserStatus:

    # TC-API-U07 | State Transition: active → suspended | Integration
    def test_admin_can_suspend_user(self, admin_token, registered_user):
        """TC-API-U07 | State Transition: active → suspended
        PATCH /api/users/:id/status with status='suspended' must return 200."""
        uid = registered_user["id"]
        res = api("PATCH", f"/api/users/{uid}/status",
                  {"status": "suspended"}, token=admin_token)
        assert res.status_code == 200
        assert res.json()["status"] == "suspended"

    # TC-API-U08 | State Transition: suspended → active | Integration
    def test_admin_can_reactivate_user(self, admin_token, registered_user):
        """TC-API-U08 | State Transition: suspended → active
        Admin must be able to re-activate a previously suspended user."""
        uid = registered_user["id"]

        # Suspend first
        api("PATCH", f"/api/users/{uid}/status",
            {"status": "suspended"}, token=admin_token)

        # Reactivate
        res = api("PATCH", f"/api/users/{uid}/status",
                  {"status": "active"}, token=admin_token)
        assert res.status_code == 200
        assert res.json()["status"] == "active"

    # TC-API-U09 | Security — suspension blocks login | Integration
    def test_suspended_user_cannot_login(self, admin_token, registered_user):
        """TC-API-U09 | Security + State Transition
        After admin suspends a user, that user must get 401 on login.
        Tests the full cross-module chain: UsersController → DB → AuthController."""
        uid = registered_user["id"]

        # Suspend
        api("PATCH", f"/api/users/{uid}/status",
            {"status": "suspended"}, token=admin_token)

        # Suspended user tries to log in
        login_res = api("POST", "/api/auth/login", {
            "email":    registered_user["email"],
            "password": registered_user["password"],
        })
        assert login_res.status_code == 401
        assert "suspended" in login_res.json().get("message", "").lower()

    # TC-API-U10 | Security — regular user cannot suspend | Integration
    def test_regular_user_cannot_change_status(self, user_token, registered_user):
        """TC-API-U10 | Security — role enforcement
        A regular user must get 403 when trying to change another user's status."""
        uid = registered_user["id"]
        res = api("PATCH", f"/api/users/{uid}/status",
                  {"status": "suspended"}, token=user_token)
        assert res.status_code == 403


class TestUserRole:

    # TC-API-U11 | Requirements-based | Integration
    def test_admin_can_promote_user_to_admin(self, admin_token, registered_user):
        """TC-API-U11 | Requirements-based
        PATCH /api/users/:id/role with role='admin' must return 200 and updated role."""
        uid = registered_user["id"]
        res = api("PATCH", f"/api/users/{uid}/role",
                  {"role": "admin"}, token=admin_token)
        assert res.status_code == 200
        assert res.json()["role"] == "admin"

    # TC-API-U12 | Security — regular user cannot change roles | Integration
    def test_regular_user_cannot_change_role(self, user_token, registered_user):
        """TC-API-U12 | Security — role enforcement
        A regular user must get 403 when attempting to change a user's role."""
        uid = registered_user["id"]
        res = api("PATCH", f"/api/users/{uid}/role",
                  {"role": "admin"}, token=user_token)
        assert res.status_code == 403
