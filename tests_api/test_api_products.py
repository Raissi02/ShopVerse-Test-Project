"""
tests_api/test_api_products.py
─────────────────────────────────────────────────────────────────────────────
Integration tests — ProductsController
  GET    /api/products
  GET    /api/products/:id
  POST   /api/products       (admin only)
  PUT    /api/products/:id   (admin only)
  DELETE /api/products/:id   (admin only — soft delete)

Every test sends a REAL HTTP request to the running .NET backend.

Technique : EC + BVA + Requirements-based + Security
Level     : Integration
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from helpers import api, unique_email


class TestGetProducts:

    # TC-API-P01 | Requirements-based | Integration
    def test_get_all_products_returns_200_no_auth(self):
        """TC-API-P01 | Requirements-based | REQ-PROD-01
        GET /api/products must return 200 without any authentication.
        Verifies [AllowAnonymous] on the controller action."""
        res = api("GET", "/api/products")
        assert res.status_code == 200

    # TC-API-P02 | Requirements-based | Integration
    def test_get_products_response_shape(self):
        """TC-API-P02 | Requirements-based
        Response must be a PaginatedResponse with data[], total, page, pageSize."""
        res = api("GET", "/api/products")
        assert res.status_code == 200
        body = res.json()
        for field in ("data", "total", "page", "pageSize"):
            assert field in body, f"Missing field '{field}' in paginated response"
        assert isinstance(body["data"], list)
        assert body["total"] >= 0

    # TC-API-P03 | Requirements-based | Integration
    def test_product_dto_contains_required_fields(self):
        """TC-API-P03 | Requirements-based
        Each product in data[] must have all ProductDto fields."""
        res = api("GET", "/api/products?pageSize=1")
        assert res.status_code == 200
        products = res.json()["data"]
        assert len(products) > 0, "No products in DB — seed the database"
        p = products[0]
        for field in ("id", "name", "description", "price", "isActive",
                      "categoryId", "categoryName"):
            assert field in p, f"Missing field '{field}' in ProductDto"

    # TC-API-P04 | EC — valid filter: search keyword | Integration
    def test_search_filter_returns_matching_products(self):
        """TC-API-P04 | EC — valid class: search query matches product name/description
        GET /api/products?search=a must only return products whose name or
        description contains the letter 'a'."""
        res = api("GET", "/api/products?search=a")
        assert res.status_code == 200
        body = res.json()
        for p in body["data"]:
            name_match = "a" in p["name"].lower()
            desc_match = "a" in p["description"].lower()
            assert name_match or desc_match, (
                f"Product '{p['name']}' returned but does not match search='a'"
            )

    # TC-API-P05 | EC — valid filter: category | Integration
    def test_category_filter_returns_only_that_category(self, first_category):
        """TC-API-P05 | EC — valid class: filtering by categoryId
        All returned products must belong to the requested category."""
        cat_id = first_category["id"]
        res = api("GET", f"/api/products?categoryId={cat_id}")
        assert res.status_code == 200
        for p in res.json()["data"]:
            assert p["categoryId"] == cat_id, (
                f"Product '{p['name']}' has categoryId={p['categoryId']}, expected {cat_id}"
            )

    # TC-API-P06 | EC — valid filter: pagination | Integration
    def test_pagination_pagesize_is_respected(self):
        """TC-API-P06 | EC — valid class: pageSize parameter
        GET /api/products?pageSize=2 must return at most 2 items."""
        res = api("GET", "/api/products?pageSize=2")
        assert res.status_code == 200
        body = res.json()
        assert len(body["data"]) <= 2
        assert body["pageSize"] == 2

    # TC-API-P07 | Requirements-based | Integration
    def test_get_product_by_id_returns_200(self, first_product):
        """TC-API-P07 | Requirements-based
        GET /api/products/:id must return 200 and the correct product."""
        pid = first_product["id"]
        res = api("GET", f"/api/products/{pid}")
        assert res.status_code == 200
        assert res.json()["id"] == pid

    # TC-API-P08 | EC — invalid class: non-existent id | Integration
    def test_get_product_by_nonexistent_id_returns_404(self):
        """TC-API-P08 | EC — invalid class: id not in DB
        GET /api/products/999999 must return 404."""
        res = api("GET", "/api/products/999999")
        assert res.status_code == 404

    # TC-API-P09 | EC — valid filter: price range | Integration
    def test_min_price_filter_excludes_cheaper_products(self):
        """TC-API-P09 | EC — valid class: minPrice filter
        All returned products must have price >= minPrice."""
        min_price = 100
        res = api("GET", f"/api/products?minPrice={min_price}")
        assert res.status_code == 200
        for p in res.json()["data"]:
            assert p["price"] >= min_price, (
                f"Product '{p['name']}' price={p['price']} is below minPrice={min_price}"
            )

    # TC-API-P10 | EC — valid filter: sort order | Integration
    def test_sort_price_asc_is_ordered(self):
        """TC-API-P10 | EC — valid class: sortBy=price-asc
        Returned products must be in ascending price order."""
        res = api("GET", "/api/products?sortBy=price-asc&pageSize=20")
        assert res.status_code == 200
        prices = [p["price"] for p in res.json()["data"]]
        assert prices == sorted(prices), "Products are not sorted by price ascending"


class TestProductsAuth:

    # TC-API-P11 | Security — role enforcement | Integration
    def test_create_product_without_auth_returns_401(self):
        """TC-API-P11 | Security — no token
        POST /api/products without Authorization must return 401."""
        res = api("POST", "/api/products", {
            "name": "Hack Product", "description": "test",
            "urlImg": "", "price": 9.99, "reviews": 0, "categoryId": 1
        })
        assert res.status_code == 401

    # TC-API-P12 | Security — role enforcement | Integration
    def test_create_product_as_user_returns_403(self, user_token):
        """TC-API-P12 | Security — non-admin role
        POST /api/products with a regular user JWT must return 403 Forbidden."""
        res = api("POST", "/api/products", {
            "name": "User Product", "description": "test",
            "urlImg": "", "price": 9.99, "reviews": 0, "categoryId": 1
        }, token=user_token)
        assert res.status_code == 403

    # TC-API-P13 | Requirements-based + Security | Integration
    def test_create_product_as_admin_returns_201(self, admin_token, first_category):
        """TC-API-P13 | Requirements-based + Security — admin role
        POST /api/products with admin JWT must return 201 and the new ProductDto."""
        res = api("POST", "/api/products", {
            "name":        "Test Product API",
            "description": "Created by pytest integration test",
            "urlImg":      "https://example.com/img.jpg",
            "price":       49.99,
            "reviews":     0,
            "categoryId":  first_category["id"],
        }, token=admin_token)
        assert res.status_code == 201
        body = res.json()
        assert body["name"]   == "Test Product API"
        assert body["isActive"] is True

    # TC-API-P14 | EC — invalid class: bad categoryId | Integration
    def test_create_product_with_invalid_category_returns_400(self, admin_token):
        """TC-API-P14 | EC — invalid class: categoryId not in DB
        POST /api/products with a non-existent categoryId must return 400."""
        res = api("POST", "/api/products", {
            "name": "Bad Cat Product", "description": "test",
            "urlImg": "", "price": 9.99, "reviews": 0,
            "categoryId": 999999
        }, token=admin_token)
        assert res.status_code == 400

    # TC-API-P15 | Requirements-based — soft delete | Integration
    def test_delete_product_soft_deletes_it(self, admin_token, first_category):
        """TC-API-P15 | Requirements-based — soft delete
        DELETE /api/products/:id must set IsActive=false, not physically remove it.
        After deletion, the product must NOT appear in GET /api/products."""
        # Create a product to delete
        create = api("POST", "/api/products", {
            "name":        "Product To Delete",
            "description": "Will be soft-deleted",
            "urlImg":      "",
            "price":       1.00,
            "reviews":     0,
            "categoryId":  first_category["id"],
        }, token=admin_token)
        assert create.status_code == 201
        pid = create.json()["id"]

        # Delete it
        delete = api("DELETE", f"/api/products/{pid}", token=admin_token)
        assert delete.status_code == 200

        # Must not appear in active listing
        listing = api("GET", "/api/products")
        ids = [p["id"] for p in listing.json()["data"]]
        assert pid not in ids, "Soft-deleted product still appears in product listing"

    # TC-API-P16 | Security — delete without auth | Integration
    def test_delete_product_without_auth_returns_401(self, first_product):
        """TC-API-P16 | Security — no token
        DELETE /api/products/:id without Authorization must return 401."""
        res = api("DELETE", f"/api/products/{first_product['id']}")
        assert res.status_code == 401
