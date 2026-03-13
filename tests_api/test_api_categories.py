"""
tests_api/test_api_categories.py
─────────────────────────────────────────────────────────────────────────────
Integration tests — CategoriesController
  GET    /api/categories
  GET    /api/categories/:id
  POST   /api/categories     (admin only)
  PUT    /api/categories/:id (admin only)
  DELETE /api/categories/:id (admin only)

Every test sends a REAL HTTP request to the running .NET backend.

Technique : EC + BVA + Security + Requirements-based
Level     : Integration
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
import requests
from helpers import api


class TestGetCategories:

    # TC-API-C01 | Requirements-based | Integration
    def test_get_all_categories_returns_200_no_auth(self):
        """TC-API-C01 | Requirements-based | [AllowAnonymous]
        GET /api/categories must return 200 without any authentication."""
        res = api("GET", "/api/categories")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    # TC-API-C02 | Requirements-based | Integration
    def test_category_dto_contains_required_fields(self):
        """TC-API-C02 | Requirements-based
        Each CategoryDto must have id, name, description, icon."""
        res = api("GET", "/api/categories")
        assert res.status_code == 200
        cats = res.json()
        assert len(cats) > 0, "No categories in DB"
        c = cats[0]
        for field in ("id", "name", "description", "icon"):
            assert field in c, f"Missing field '{field}' in CategoryDto"

    # TC-API-C03 | Requirements-based | Integration
    def test_get_category_by_id_returns_200(self, first_category):
        """TC-API-C03 | Requirements-based
        GET /api/categories/:id must return the correct category."""
        cid = first_category["id"]
        res = api("GET", f"/api/categories/{cid}")
        assert res.status_code == 200
        assert res.json()["id"] == cid

    # TC-API-C04 | EC — invalid class: non-existent id | Integration
    def test_get_category_by_nonexistent_id_returns_404(self):
        """TC-API-C04 | EC — invalid class: id not in DB
        GET /api/categories/999999 must return 404."""
        res = api("GET", "/api/categories/999999")
        assert res.status_code == 404


class TestCategoryAuth:

    # TC-API-C05 | Security — admin creates category | Integration
    def test_create_category_as_admin_returns_201(self):
        """TC-API-C05 | Security — admin role
        POST /api/categories with admin JWT must return 201 and new CategoryDto."""
        import uuid
        
        # Step 1: Login as admin (similar to TC-API-L08)
        login_response = api("POST", "/api/auth/login", {
            "email":    "admin@shopverse.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        
        # Get token from login response
        admin_token = login_response.json()["token"]  # Adjust key name if needed
        
        name = f"Test Category {uuid.uuid4().hex[:6]}"
        res = api("POST", "/api/categories", {
            "name":        name,
            "description": "Created by pytest integration test",
            "icon":        "🧪"
        }, token=admin_token)
        assert res.status_code == 201
        body = res.json()
        assert body["name"] == name
        assert body["icon"] == "🧪"

    # TC-API-C08 | EC — invalid class: duplicate name | Integration
    def test_create_duplicate_category_returns_400(self, admin_token, first_category):
        """TC-API-C08 | EC — invalid class: category name already exists
        POST /api/categories with an existing name must return 400."""

        res = api("POST", "/api/categories", {
        "name":        first_category["name"],  # already exists
        "description": "Duplicate",
        "icon":        "📦"
        }, token=admin_token)  # Using the fixture token
    
        assert res.status_code == 400


    # TC-API-C06 | Security — no token blocked | Integration
    def test_create_category_without_auth_returns_401(self):
        """TC-API-C06 | Security — no token
        POST /api/categories without JWT must return 401."""
        res = api("POST", "/api/categories", {
            "name": "Hack Cat", "description": "test", "icon": "🔓"
        })
        assert res.status_code == 401

    # TC-API-C07 | Security — regular user blocked | Integration
    def test_create_category_as_user_returns_403(self, user_token):
        """TC-API-C07 | Security — non-admin role
        POST /api/categories with a regular user JWT must return 403."""
        res = api("POST", "/api/categories", {
            "name": "User Cat", "description": "test", "icon": "👤"
        }, token=user_token)
        assert res.status_code == 403

    # TC-API-C09 | Requirements-based — default icon | Integration
    def test_create_category_without_icon_gets_default(self, admin_token):
        """TC-API-C09 | Requirements-based
        Creating a category without icon must use the default icon '📦'."""
        import uuid
        res = api("POST", "/api/categories", {
            "name":        f"No Icon Cat {uuid.uuid4().hex[:6]}",
            "description": "No icon provided",
        }, token=admin_token)
        assert res.status_code == 201
        assert res.json()["icon"] == "📦"
