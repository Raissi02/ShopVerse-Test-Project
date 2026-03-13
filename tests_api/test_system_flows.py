"""
tests_api/test_system_flows.py
─────────────────────────────────────────────────────────────────────────────
System tests — Full user journey scenarios through the REAL .NET backend.

Each test exercises a complete multi-step flow that crosses multiple
controllers and the database — no mocking, no simulation.

Technique : Scenario-based + State Transition + Security + Regression
Level     : System
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from helpers import api, unique_email


class TestUserJourneyScenarios:

    # TC-SYS-01 | Scenario-based | System
    def test_full_user_journey_register_login_browse_order_cancel(self):
        """TC-SYS-01 | Scenario-based | SYS-FLOW-01
        Complete user journey:
          Register → Login → Browse products → Place order → Cancel order

        Crosses: AuthController → ProductsController → OrdersController → DB
        """
        # Step 1: Register
        email    = unique_email("journey")
        password = "Journey123"
        reg = api("POST", "/api/auth/register", {
            "name": "Journey User", "email": email, "password": password
        })
        assert reg.status_code == 201, f"Step 1 FAIL: {reg.text}"
        token = reg.json()["token"]

        # Step 2: Browse products (no auth needed)
        products_res = api("GET", "/api/products?pageSize=1")
        assert products_res.status_code == 200
        products = products_res.json()["data"]
        assert len(products) > 0, "Step 2 FAIL: No products to order"
        product = products[0]

        # Step 3: Place order
        order_res = api("POST", "/api/orders", {
            "items": [{"productId": product["id"], "quantity": 1,
                       "price": product["price"]}]
        }, token=token)
        assert order_res.status_code == 201, f"Step 3 FAIL: {order_res.text}"
        assert order_res.json()["status"] == "pending"
        order_id = order_res.json()["id"]

        # Step 4: Cancel order
        cancel_res = api("PATCH", f"/api/orders/{order_id}/status",
                         {"status": "cancelled"}, token=token)
        assert cancel_res.status_code == 200, f"Step 4 FAIL: {cancel_res.text}"
        assert cancel_res.json()["status"] == "cancelled"

    # TC-SYS-02 | Scenario-based | System
    def test_admin_creates_product_user_orders_admin_delivers(self, admin_token):
        """TC-SYS-02 | Scenario-based | SYS-FLOW-02
        Admin lifecycle:
          Admin creates product → User sees it → User orders it → Admin delivers it

        Crosses: AuthController → ProductsController → OrdersController
        """
        # Step 1: Admin creates a product
        cats = api("GET", "/api/categories").json()
        cat_id = cats[0]["id"]
        create_prod = api("POST", "/api/products", {
            "name":        "SYS-02 Product",
            "description": "System test product",
            "urlImg":      "",
            "price":       25.00,
            "reviews":     0,
            "categoryId":  cat_id
        }, token=admin_token)
        assert create_prod.status_code == 201
        pid = create_prod.json()["id"]

        # Step 2: Anonymous user sees the product in listing
        listing = api("GET", f"/api/products/{pid}")
        assert listing.status_code == 200
        assert listing.json()["isActive"] is True

        # Step 3: New user registers and orders the product
        email    = unique_email("sys02")
        reg = api("POST", "/api/auth/register", {
            "name": "SYS02 User", "email": email, "password": "Sys02Pass"
        })
        assert reg.status_code == 201
        user_token = reg.json()["token"]

        order_res = api("POST", "/api/orders", {
            "items": [{"productId": pid, "quantity": 1, "price": 25.00}]
        }, token=user_token)
        assert order_res.status_code == 201
        order_id = order_res.json()["id"]

        # Step 4: Admin advances order to 'delivered'
        deliver_res = api("PATCH", f"/api/orders/{order_id}/status",
                          {"status": "delivered"}, token=admin_token)
        assert deliver_res.status_code == 200
        assert deliver_res.json()["status"] == "delivered"

    # TC-SYS-03 | Scenario-based | System
    def test_admin_suspends_user_user_cannot_login(self, admin_token):
        """TC-SYS-03 | Scenario-based | SYS-FLOW-03
        Admin moderation:
          Register user → Admin suspends → User login is blocked

        Crosses: AuthController → UsersController → AuthController (login check)
        """
        # Step 1: Register user
        email    = unique_email("suspend")
        password = "Suspend123"
        reg = api("POST", "/api/auth/register", {
            "name": "To Suspend", "email": email, "password": password
        })
        assert reg.status_code == 201
        uid = reg.json()["id"]

        # Step 2: Admin suspends the user
        suspend = api("PATCH", f"/api/users/{uid}/status",
                      {"status": "suspended"}, token=admin_token)
        assert suspend.status_code == 200
        assert suspend.json()["status"] == "suspended"

        # Step 3: Suspended user cannot log in
        login_res = api("POST", "/api/auth/login", {
            "email": email, "password": password
        })
        assert login_res.status_code == 401

    # TC-SYS-04 | Scenario-based | System
    def test_admin_soft_deletes_product_it_disappears_from_listing(self, admin_token):
        """TC-SYS-04 | Scenario-based | SYS-FLOW-04
        Product lifecycle:
          Admin creates product → Appears in listing → Admin deletes → Disappears

        Verifies soft-delete logic: IsActive=false hides from GET /api/products
        """
        cats     = api("GET", "/api/categories").json()
        cat_id   = cats[0]["id"]

        create = api("POST", "/api/products", {
            "name": "SYS-04 Delete Me", "description": "test",
            "urlImg": "", "price": 1.00, "reviews": 0, "categoryId": cat_id
        }, token=admin_token)
        assert create.status_code == 201
        pid = create.json()["id"]

        # Confirm it appears in listing
        before = api("GET", "/api/products")
        ids_before = [p["id"] for p in before.json()["data"]]
        assert pid in ids_before, "Product not visible in listing after creation"

        # Soft-delete
        delete = api("DELETE", f"/api/products/{pid}", token=admin_token)
        assert delete.status_code == 200

        # Must not appear in active listing anymore
        after = api("GET", "/api/products?pageSize=200")
        ids_after = [p["id"] for p in after.json()["data"]]
        assert pid not in ids_after, "Soft-deleted product still appears in listing"


class TestRegressionScenarios:

    # TC-SYS-REG-01 | Regression | System
    def test_duplicate_email_registration_is_blocked(self):
        """TC-SYS-REG-01 | Regression
        Registering twice with the same email must return 409 on the second attempt.
        Prevents a regression where the uniqueness check could be bypassed."""
        email = unique_email("dupe")
        api("POST", "/api/auth/register", {
            "name": "First",  "email": email, "password": "Pass123"
        })
        res = api("POST", "/api/auth/register", {
            "name": "Second", "email": email, "password": "Pass456"
        })
        assert res.status_code == 409

    # TC-SYS-REG-02 | Regression | System
    def test_order_with_inactive_product_is_rejected(self, admin_token):
        """TC-SYS-REG-02 | Regression
        Ordering an inactive (soft-deleted) product must always return 400.
        Prevents a regression where price-injection via deleted products was possible."""
        cats   = api("GET", "/api/categories").json()
        cat_id = cats[0]["id"]

        # Create and immediately delete a product
        create = api("POST", "/api/products", {
            "name": "REG-02 Inactive", "description": "test",
            "urlImg": "", "price": 1.00, "reviews": 0, "categoryId": cat_id
        }, token=admin_token)
        pid = create.json()["id"]
        api("DELETE", f"/api/products/{pid}", token=admin_token)

        # New user tries to order the deleted product
        email = unique_email("reg02")
        reg   = api("POST", "/api/auth/register", {
            "name": "REG02 User", "email": email, "password": "Pass123"
        })
        token = reg.json()["token"]

        order_res = api("POST", "/api/orders", {
            "items": [{"productId": pid, "quantity": 1, "price": 1.00}]
        }, token=token)
        assert order_res.status_code == 400

    # TC-SYS-REG-03 | Regression | System
    def test_cannot_cancel_already_cancelled_order(self):
        """TC-SYS-REG-03 | Regression
        Cancelling an already-cancelled order must return 400.
        Prevents double-cancel regression."""
        prods  = api("GET", "/api/products?pageSize=1").json()["data"]
        prod   = prods[0]
        email  = unique_email("reg03")
        token  = api("POST", "/api/auth/register", {
            "name": "REG03 User", "email": email, "password": "Pass123"
        }).json()["token"]

        order_id = api("POST", "/api/orders", {
            "items": [{"productId": prod["id"], "quantity": 1, "price": prod["price"]}]
        }, token=token).json()["id"]

        # First cancel — must succeed
        first = api("PATCH", f"/api/orders/{order_id}/status",
                    {"status": "cancelled"}, token=token)
        assert first.status_code == 200

        # Second cancel — must fail
        second = api("PATCH", f"/api/orders/{order_id}/status",
                     {"status": "cancelled"}, token=token)
        assert second.status_code == 400


class TestSecurityScenarios:

    # TC-SYS-SEC-01 | Security | System
    def test_fabricated_token_is_rejected(self):
        """TC-SYS-SEC-01 | Security
        A fabricated (invalid) JWT must return 401 on any protected endpoint.
        Tests JwtService token validation in the real middleware pipeline."""
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OTkifQ.FAKESIG"
        res = api("GET", "/api/orders", token=fake_token)
        assert res.status_code == 401

    # TC-SYS-SEC-02 | Security | System
    def test_user_cannot_access_admin_users_endpoint(self, user_token):
        """TC-SYS-SEC-02 | Security
        A regular user's JWT must be rejected by the admin-only UsersController."""
        res = api("GET", "/api/users", token=user_token)
        assert res.status_code == 403

    # TC-SYS-SEC-03 | Security | System
    def test_user_cannot_create_product(self, user_token, first_category):
        """TC-SYS-SEC-03 | Security
        A regular user must not be able to create products (admin-only action)."""
        res = api("POST", "/api/products", {
            "name": "Injected Product", "description": "test",
            "urlImg": "", "price": 0.01, "reviews": 0,
            "categoryId": first_category["id"]
        }, token=user_token)
        assert res.status_code == 403

    # TC-SYS-SEC-04 | Security | System
    def test_expired_or_malformed_token_rejected(self):
        """TC-SYS-SEC-04 | Security
        Sending a completely malformed Authorization header must return 401."""
        res = api("GET", "/api/orders", token="not.a.jwt")
        assert res.status_code == 401
