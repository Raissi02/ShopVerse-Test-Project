"""
tests_api/test_api_orders.py
─────────────────────────────────────────────────────────────────────────────
Integration tests — OrdersController
  GET    /api/orders
  GET    /api/orders/:id
  POST   /api/orders
  PATCH  /api/orders/:id/status
  DELETE /api/orders/:id     (admin only)

Every test sends a REAL HTTP request to the running .NET backend.

Technique : EC + BVA + Security + State Transition
Level     : Integration
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from helpers import api


class TestCreateOrder:

    # TC-API-O01 | Requirements-based | Integration
    def test_create_order_returns_201_with_order_dto(self, user_token, first_product):
        """TC-API-O01 | Requirements-based | REQ-ORDER-01
        POST /api/orders with valid JWT and items must return 201 and an OrderDto."""
        res = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "pending"
        assert len(body["items"]) == 1
        assert body["total"] > 0

    # TC-API-O02 | Requirements-based | Integration
    def test_create_order_response_shape(self, user_token, first_product):
        """TC-API-O02 | Requirements-based
        OrderDto must contain all required fields."""
        res = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        assert res.status_code == 201
        body = res.json()
        for field in ("id", "userId", "status", "total", "createdAt", "items"):
            assert field in body, f"Missing field '{field}' in OrderDto"

    # TC-API-O03 | Security — no token | Integration
    def test_create_order_without_token_returns_401(self, first_product):
        """TC-API-O03 | Security — unauthenticated
        POST /api/orders without JWT must return 401."""
        res = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        })
        assert res.status_code == 401

    # TC-API-O04 | BVA — boundary: empty items list | Integration
    def test_create_order_with_empty_items_returns_400(self, user_token):
        """TC-API-O04 | BVA — boundary: items list is empty (length = 0)
        POST /api/orders with empty items array must return 400."""
        res = api("POST", "/api/orders", {"items": []}, token=user_token)
        assert res.status_code == 400

    # TC-API-O05 | EC — invalid class: inactive product | Integration
    def test_create_order_with_inactive_product_returns_400(
            self, user_token, admin_token, first_category):
        """TC-API-O05 | EC — invalid class: productId is inactive
        Creating an order with a soft-deleted product must return 400.
        Tests module interaction: OrdersController → ProductsController (IsActive check)."""
        # Admin creates then soft-deletes a product
        create = api("POST", "/api/products", {
            "name": "To Be Deleted", "description": "test",
            "urlImg": "", "price": 5.00, "reviews": 0,
            "categoryId": first_category["id"]
        }, token=admin_token)
        assert create.status_code == 201
        pid = create.json()["id"]

        api("DELETE", f"/api/products/{pid}", token=admin_token)

        # Try to order the deleted product
        res = api("POST", "/api/orders", {
            "items": [{"productId": pid, "quantity": 1, "price": 5.00}]
        }, token=user_token)
        assert res.status_code == 400

    # TC-API-O06 | EC — valid class: multiple items | Integration
    def test_create_order_with_two_items_totals_correctly(self, user_token, first_product):
        """TC-API-O06 | EC — valid class: 2 items in one order
        Total must equal sum of (price × quantity) for all items."""
        price = first_product["price"]
        res = api("POST", "/api/orders", {
            "items": [
                {"productId": first_product["id"], "quantity": 2, "price": price},
                {"productId": first_product["id"], "quantity": 1, "price": price},
            ]
        }, token=user_token)
        assert res.status_code == 201
        body = res.json()
        expected_total = round(price * 2 + price * 1, 2)
        assert abs(body["total"] - expected_total) < 0.01, (
            f"Total {body['total']} does not match expected {expected_total}"
        )


class TestGetOrders:

    # TC-API-O07 | Security — user sees only own orders | Integration
    def test_user_can_only_see_own_orders(self, user_token, first_product):
        """TC-API-O07 | Security — data isolation
        A regular user's GET /api/orders must return only their own orders."""
        # Place an order
        api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)

        res = api("GET", "/api/orders", token=user_token)
        assert res.status_code == 200
        orders = res.json()

        # Decode userId from token to verify ownership
        import base64, json as _json
        payload = user_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # pad
        decoded = _json.loads(base64.b64decode(payload))
        uid = int(decoded.get(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
            decoded.get("sub", 0)
        ))
        for order in orders:
            assert order["userId"] == uid, (
                f"Order {order['id']} belongs to userId={order['userId']}, not to current user {uid}"
            )

    # TC-API-O08 | Security — admin sees all orders | Integration
    def test_admin_can_see_all_orders(self, admin_token):
        """TC-API-O08 | Security — admin role
        GET /api/orders with admin JWT must return 200 (admin sees all orders)."""
        res = api("GET", "/api/orders", token=admin_token)
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    # TC-API-O09 | Security — no token | Integration
    def test_get_orders_without_token_returns_401(self):
        """TC-API-O09 | Security — unauthenticated
        GET /api/orders without JWT must return 401."""
        res = api("GET", "/api/orders")
        assert res.status_code == 401

    # TC-API-O10 | Requirements-based | Integration
    def test_get_order_by_id_returns_correct_order(self, user_token, first_product):
        """TC-API-O10 | Requirements-based
        GET /api/orders/:id must return the correct order for its owner."""
        create = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        assert create.status_code == 201
        order_id = create.json()["id"]

        res = api("GET", f"/api/orders/{order_id}", token=user_token)
        assert res.status_code == 200
        assert res.json()["id"] == order_id

    # TC-API-O11 | Security — cross-user access | Integration
    def test_user_cannot_access_another_users_order(
            self, user_token, admin_token, first_product, registered_user):
        """TC-API-O11 | Security — cross-user access
        A user must get 403 when trying to GET an order that belongs to another user.
        Tests the ownership check in OrdersController.GetById."""
        # Create order as admin
        admin_order = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=admin_token)
        assert admin_order.status_code == 201
        admin_order_id = admin_order.json()["id"]

        # Try to access it as a different user
        res = api("GET", f"/api/orders/{admin_order_id}", token=registered_user["token"])
        assert res.status_code in (403, 404)


class TestUpdateOrderStatus:

    # TC-API-O12 | State Transition — user cancels own pending order | Integration
    def test_user_can_cancel_own_pending_order(self, user_token, first_product):
        """TC-API-O12 | State Transition: pending → cancelled (by owner)
        A user must be able to PATCH their own pending order to 'cancelled'."""
        create = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        assert create.status_code == 201
        order_id = create.json()["id"]

        res = api("PATCH", f"/api/orders/{order_id}/status",
                  {"status": "cancelled"}, token=user_token)
        assert res.status_code == 200
        assert res.json()["status"] == "cancelled"

    # TC-API-O13 | Security — user cannot set status to 'delivered' | Integration
    def test_user_cannot_set_status_to_delivered(self, user_token, first_product):
        """TC-API-O13 | Security — role enforcement
        A regular user must get 403 when trying to set status to 'delivered' (admin only)."""
        create = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        assert create.status_code == 201
        order_id = create.json()["id"]

        res = api("PATCH", f"/api/orders/{order_id}/status",
                  {"status": "delivered"}, token=user_token)
        assert res.status_code == 403

    # TC-API-O14 | State Transition — cannot cancel already-cancelled order | Integration
    def test_user_cannot_cancel_already_cancelled_order(self, user_token, first_product):
        """TC-API-O14 | State Transition: cancelled → cancelled must return 400
        Only pending orders can be cancelled — business rule enforced by backend."""
        create = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        order_id = create.json()["id"]

        # First cancel — must succeed
        api("PATCH", f"/api/orders/{order_id}/status",
            {"status": "cancelled"}, token=user_token)

        # Second cancel — must fail
        res = api("PATCH", f"/api/orders/{order_id}/status",
                  {"status": "cancelled"}, token=user_token)
        assert res.status_code == 400

    # TC-API-O15 | EC — invalid status value | Integration
    def test_invalid_status_value_returns_400(self, admin_token, user_token, first_product):
        """TC-API-O15 | EC — invalid class: status not in allowed set
        PATCH with status='shipped' (not valid) must return 400."""
        create = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        order_id = create.json()["id"]

        res = api("PATCH", f"/api/orders/{order_id}/status",
                  {"status": "shipped"}, token=admin_token)
        assert res.status_code == 400

    # TC-API-O16 | State Transition — admin advances order status | Integration
    def test_admin_can_advance_order_to_proceeding(self, admin_token, user_token, first_product):
        """TC-API-O16 | State Transition: pending → proceeding (by admin)
        Admin must be able to change any order status including 'proceeding'."""
        create = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=user_token)
        order_id = create.json()["id"]

        res = api("PATCH", f"/api/orders/{order_id}/status",
                  {"status": "proceeding"}, token=admin_token)
        assert res.status_code == 200
        assert res.json()["status"] == "proceeding"

    # TC-API-O17 | Security — cross-user status update | Integration
    def test_user_cannot_cancel_another_users_order(
            self, admin_token, user_token, first_product, registered_user):
        """TC-API-O17 | Security — cross-user access
        A user must get 403 when attempting to cancel an order they don't own."""
        # Admin places an order
        admin_order = api("POST", "/api/orders", {
            "items": [{"productId": first_product["id"], "quantity": 1,
                       "price": first_product["price"]}]
        }, token=admin_token)
        order_id = admin_order.json()["id"]

        # Another user tries to cancel it
        res = api("PATCH", f"/api/orders/{order_id}/status",
                  {"status": "cancelled"}, token=registered_user["token"])
        assert res.status_code == 403
