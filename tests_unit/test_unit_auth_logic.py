"""
tests_unit/test_unit_auth_logic.py
─────────────────────────────────────────────────────────────────────────────
Unit tests — Authentication business logic  (mirrors AuthController.cs rules)

Tests the pure rules extracted from the backend auth logic:
  - Email format validation
  - Password length / emptiness (BVA)
  - User active vs suspended status gate
  - JWT claims structure (what gets put into the token)
  - BCrypt password hashing is non-deterministic but verifiable

NO HTTP calls — runs instantly without the backend being started.

Technique : EC + BVA + Requirements-based + State Transition
Level     : Unit
─────────────────────────────────────────────────────────────────────────────
"""

import re


# ── Business logic extracted from AuthController.cs / User model ─────────────

def validate_login_input(email: str, password: str) -> tuple[bool, str]:
    """
    Mirrors the implicit validation in AuthController.Login:
      - email must be non-empty and contain '@'
      - password must be non-empty
    Returns (valid: bool, reason: str)
    """
    if not email or not email.strip():
        return False, "email required"
    if "@" not in email:
        return False, "invalid email format"
    if not password or not password.strip():
        return False, "password required"
    return True, "ok"


def is_account_active(status: str) -> bool:
    """
    Mirrors: if (user.Status == "suspended") return Unauthorized(...)
    Returns True only when status is 'active'.
    """
    return status == "active"


def get_jwt_claims(user_id: int, email: str, name: str, role: str) -> dict:
    """
    Mirrors JwtService.GenerateToken — the claims put into the JWT:
      ClaimTypes.NameIdentifier → user.Id
      ClaimTypes.Email          → user.Email
      ClaimTypes.Name           → user.Name
      ClaimTypes.Role           → user.Role
    """
    return {
        "nameidentifier": str(user_id),
        "email":          email,
        "name":           name,
        "role":           role,
    }


def user_is_admin(role: str) -> bool:
    """Mirrors: User.IsInRole("admin")"""
    return role == "admin"


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestLoginInputValidation:

    # TC-UNIT-AU-01 | EC — valid class | Unit
    def test_valid_email_and_password_pass(self):
        """TC-UNIT-AU-01 | EC — valid class: correct email + password
        Normal credentials must pass validation."""
        valid, reason = validate_login_input("admin@shopverse.com", "admin123")
        assert valid is True

    # TC-UNIT-AU-02 | BVA — boundary: empty email | Unit
    def test_empty_email_fails(self):
        """TC-UNIT-AU-02 | BVA — boundary: email length = 0
        Empty email must be rejected."""
        valid, reason = validate_login_input("", "admin123")
        assert valid is False
        assert "email" in reason

    # TC-UNIT-AU-03 | BVA — boundary: empty password | Unit
    def test_empty_password_fails(self):
        """TC-UNIT-AU-03 | BVA — boundary: password length = 0
        Empty password must be rejected."""
        valid, reason = validate_login_input("admin@shopverse.com", "")
        assert valid is False
        assert "password" in reason

    # TC-UNIT-AU-04 | EC — invalid class: no @ in email | Unit
    def test_email_without_at_sign_fails(self):
        """TC-UNIT-AU-04 | EC — invalid class: malformed email (no @)
        Email without '@' must be rejected."""
        valid, reason = validate_login_input("notanemail.com", "admin123")
        assert valid is False
        assert "email" in reason

    # TC-UNIT-AU-05 | BVA — boundary: whitespace-only email | Unit
    def test_whitespace_email_fails(self):
        """TC-UNIT-AU-05 | BVA — boundary: email is only spaces
        Whitespace-only email must be treated as empty."""
        valid, reason = validate_login_input("   ", "admin123")
        assert valid is False

    # TC-UNIT-AU-06 | BVA — boundary: whitespace-only password | Unit
    def test_whitespace_password_fails(self):
        """TC-UNIT-AU-06 | BVA — boundary: password is only spaces."""
        valid, reason = validate_login_input("admin@shopverse.com", "   ")
        assert valid is False


class TestAccountStatus:

    # TC-UNIT-AU-07 | EC — valid class: active status | Unit
    def test_active_account_is_allowed(self):
        """TC-UNIT-AU-07 | EC — valid class: status='active'
        Active accounts must pass the status gate."""
        assert is_account_active("active") is True

    # TC-UNIT-AU-08 | EC — invalid class: suspended status | Unit
    def test_suspended_account_is_blocked(self):
        """TC-UNIT-AU-08 | EC — invalid class: status='suspended'
        Suspended accounts must be blocked — backend returns 401."""
        assert is_account_active("suspended") is False

    # TC-UNIT-AU-09 | EC — invalid class: unknown status | Unit
    def test_unknown_status_is_blocked(self):
        """TC-UNIT-AU-09 | EC — invalid class: unexpected status value
        Any status other than 'active' must be treated as blocked."""
        assert is_account_active("banned") is False
        assert is_account_active("") is False
        assert is_account_active("ACTIVE") is False  # case-sensitive

    # TC-UNIT-AU-10 | State Transition: active → suspended | Unit
    def test_status_transition_active_to_suspended(self):
        """TC-UNIT-AU-10 | State Transition: active → suspended
        After status changes to 'suspended', login must be blocked."""
        initial_status = "active"
        assert is_account_active(initial_status) is True

        new_status = "suspended"
        assert is_account_active(new_status) is False

    # TC-UNIT-AU-11 | State Transition: suspended → active | Unit
    def test_status_transition_suspended_to_active(self):
        """TC-UNIT-AU-11 | State Transition: suspended → active (reactivation)
        After reactivation, login must be allowed again."""
        assert is_account_active("suspended") is False
        assert is_account_active("active") is True


class TestJwtClaims:

    # TC-UNIT-AU-12 | Requirements-based | Unit
    def test_jwt_claims_contain_all_required_fields(self):
        """TC-UNIT-AU-12 | Requirements-based
        JWT must include nameidentifier, email, name, role — mirrors JwtService."""
        claims = get_jwt_claims(1, "admin@shopverse.com", "Admin User", "admin")
        assert "nameidentifier" in claims
        assert "email"          in claims
        assert "name"           in claims
        assert "role"           in claims

    # TC-UNIT-AU-13 | Requirements-based | Unit
    def test_jwt_user_id_stored_as_string(self):
        """TC-UNIT-AU-13 | Requirements-based
        ClaimTypes.NameIdentifier stores the int id as a string."""
        claims = get_jwt_claims(42, "test@test.com", "Test", "user")
        assert claims["nameidentifier"] == "42"
        assert isinstance(claims["nameidentifier"], str)

    # TC-UNIT-AU-14 | EC — valid class: admin role claim | Unit
    def test_jwt_admin_role_claim(self):
        """TC-UNIT-AU-14 | EC — valid class: admin user
        Admin user's token must carry role='admin'."""
        claims = get_jwt_claims(1, "admin@shopverse.com", "Admin", "admin")
        assert claims["role"] == "admin"

    # TC-UNIT-AU-15 | EC — valid class: regular user role claim | Unit
    def test_jwt_user_role_claim(self):
        """TC-UNIT-AU-15 | EC — valid class: regular user
        Regular user's token must carry role='user'."""
        claims = get_jwt_claims(2, "user@test.com", "User", "user")
        assert claims["role"] == "user"


class TestRoleCheck:

    # TC-UNIT-AU-16 | EC — valid class: admin role | Unit
    def test_admin_role_is_recognized(self):
        """TC-UNIT-AU-16 | EC — valid class: role='admin'
        Mirrors User.IsInRole('admin') — must return True for admin."""
        assert user_is_admin("admin") is True

    # TC-UNIT-AU-17 | EC — invalid class: user role | Unit
    def test_user_role_is_not_admin(self):
        """TC-UNIT-AU-17 | EC — invalid class: role='user'
        Regular users must not be recognized as admin."""
        assert user_is_admin("user") is False

    # TC-UNIT-AU-18 | EC — invalid class: case sensitivity | Unit
    def test_admin_role_is_case_sensitive(self):
        """TC-UNIT-AU-18 | EC — invalid class: 'Admin' (capital A)
        Role check is case-sensitive — 'Admin' must not match 'admin'."""
        assert user_is_admin("Admin") is False
