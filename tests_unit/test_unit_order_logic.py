"""
tests_unit/test_unit_order_logic.py
─────────────────────────────────────────────────────────────────────────────
Unit tests — Order business logic  (mirrors OrdersController.cs rules)

These tests exercise the PURE BUSINESS RULES extracted from the backend:
  - Valid/invalid order statuses          (OrdersController.UpdateStatus)
  - User permission to change status      (IsAdmin / ownership check)
  - Order total calculation               (order.Items.Sum(...))
  - Pending-only cancellation rule        (order.Status != "pending" → 400)

NO HTTP calls — runs instantly without the backend being started.

Technique : EC (Equivalence Partitioning) + BVA (Boundary Value Analysis)
            + State Transition + White-box (branch coverage)
Level     : Unit
─────────────────────────────────────────────────────────────────────────────
"""

import pytest


# ── Business logic extracted from OrdersController.cs ────────────────────────
# We re-implement the exact same rules in Python so we can unit-test them
# without spinning up .NET.  Each function mirrors one backend method/check.

VALID_STATUSES = {"pending", "proceeding", "delivered", "cancelled"}


def is_valid_status(status: str) -> bool:
    """Mirrors: validStatuses.Contains(req.Status)"""
    return status in VALID_STATUSES


def can_user_update_status(
    is_admin: bool,
    order_user_id: int,
    current_user_id: int,
    new_status: str,
    current_order_status: str,
) -> tuple[bool, str]:
    """
    Mirrors the permission logic in OrdersController.UpdateStatus:
      - Admin  → can do anything
      - User   → can only cancel their OWN pending order
    Returns (allowed: bool, reason: str)
    """
    if is_admin:
        return True, "ok"
    if order_user_id != current_user_id:
        return False, "forbidden: not owner"
    if new_status != "cancelled":
        return False, "forbidden: users can only cancel"
    if current_order_status != "pending":
        return False, "bad_request: only pending orders can be cancelled"
    return True, "ok"


def calculate_order_total(items: list[dict]) -> float:
    """
    Mirrors: order.Total = order.Items.Sum(i => i.Price * i.Quantity)
    Each item: {"price": float, "quantity": int}
    """
    return sum(item["price"] * item["quantity"] for item in items)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestOrderStatusValidation:

    # TC-UNIT-OS-01 | EC — valid class | Unit
    def test_pending_is_valid_status(self):
        """TC-UNIT-OS-01 | EC — valid class
        'pending' is in the allowed set."""
        assert is_valid_status("pending") is True

    # TC-UNIT-OS-02 | EC — valid class | Unit
    def test_proceeding_is_valid_status(self):
        """TC-UNIT-OS-02 | EC — valid class
        'proceeding' is in the allowed set."""
        assert is_valid_status("proceeding") is True

    # TC-UNIT-OS-03 | EC — valid class | Unit
    def test_delivered_is_valid_status(self):
        """TC-UNIT-OS-03 | EC — valid class
        'delivered' is in the allowed set."""
        assert is_valid_status("delivered") is True

    # TC-UNIT-OS-04 | EC — valid class | Unit
    def test_cancelled_is_valid_status(self):
        """TC-UNIT-OS-04 | EC — valid class
        'cancelled' is in the allowed set."""
        assert is_valid_status("cancelled") is True

    # TC-UNIT-OS-05 | EC — invalid class | Unit
    def test_shipped_is_not_valid_status(self):
        """TC-UNIT-OS-05 | EC — invalid class: 'shipped' not in backend enum
        Must be rejected — backend returns 400 for this value."""
        assert is_valid_status("shipped") is False

    # TC-UNIT-OS-06 | EC — invalid class | Unit
    def test_unknown_string_is_not_valid_status(self):
        """TC-UNIT-OS-06 | EC — invalid class: arbitrary unknown string."""
        assert is_valid_status("processing") is False

    # TC-UNIT-OS-07 | BVA — boundary: empty string | Unit
    def test_empty_string_is_not_valid_status(self):
        """TC-UNIT-OS-07 | BVA — boundary: length = 0
        Empty string must be rejected."""
        assert is_valid_status("") is False

    # TC-UNIT-OS-08 | EC — invalid class: case sensitivity | Unit
    def test_status_is_case_sensitive(self):
        """TC-UNIT-OS-08 | EC — invalid class: wrong case
        'Pending' (capital P) must be rejected — backend uses lowercase."""
        assert is_valid_status("Pending") is False


class TestOrderPermissions:

    # TC-UNIT-OP-01 | EC — valid class: admin | Unit
    def test_admin_can_update_any_order_to_any_status(self):
        """TC-UNIT-OP-01 | EC — valid class: is_admin=True
        Admin can update any order regardless of ownership or status."""
        allowed, reason = can_user_update_status(
            is_admin=True,
            order_user_id=99,      # different user's order
            current_user_id=1,
            new_status="delivered",
            current_order_status="pending",
        )
        assert allowed is True

    # TC-UNIT-OP-02 | EC — valid class: owner cancels pending | Unit
    def test_owner_can_cancel_own_pending_order(self):
        """TC-UNIT-OP-02 | EC — valid class: owner + pending + cancel
        User can cancel their own pending order."""
        allowed, reason = can_user_update_status(
            is_admin=False,
            order_user_id=5,
            current_user_id=5,
            new_status="cancelled",
            current_order_status="pending",
        )
        assert allowed is True

    # TC-UNIT-OP-03 | EC — invalid class: not owner | Unit
    def test_non_owner_cannot_update_order(self):
        """TC-UNIT-OP-03 | EC — invalid class: different user
        User cannot touch an order that belongs to someone else → Forbid."""
        allowed, reason = can_user_update_status(
            is_admin=False,
            order_user_id=5,
            current_user_id=7,     # different user
            new_status="cancelled",
            current_order_status="pending",
        )
        assert allowed is False
        assert "forbidden" in reason

    # TC-UNIT-OP-04 | EC — invalid class: user sets delivered | Unit
    def test_user_cannot_set_status_to_delivered(self):
        """TC-UNIT-OP-04 | EC — invalid class: non-cancel status by user
        Regular user trying to set 'delivered' must be forbidden."""
        allowed, reason = can_user_update_status(
            is_admin=False,
            order_user_id=5,
            current_user_id=5,
            new_status="delivered",
            current_order_status="pending",
        )
        assert allowed is False
        assert "forbidden" in reason

    # TC-UNIT-OP-05 | State Transition: delivered → cancelled blocked | Unit
    def test_user_cannot_cancel_delivered_order(self):
        """TC-UNIT-OP-05 | State Transition: delivered → cancelled must be blocked
        Only pending orders can be cancelled by a user."""
        allowed, reason = can_user_update_status(
            is_admin=False,
            order_user_id=5,
            current_user_id=5,
            new_status="cancelled",
            current_order_status="delivered",
        )
        assert allowed is False
        assert "pending" in reason

    # TC-UNIT-OP-06 | State Transition: cancelled → cancelled blocked | Unit
    def test_user_cannot_cancel_already_cancelled_order(self):
        """TC-UNIT-OP-06 | State Transition: cancelled → cancelled must be blocked
        Regression guard: double-cancel must be rejected."""
        allowed, reason = can_user_update_status(
            is_admin=False,
            order_user_id=5,
            current_user_id=5,
            new_status="cancelled",
            current_order_status="cancelled",
        )
        assert allowed is False

    # TC-UNIT-OP-07 | White-box: admin branch | Unit
    def test_admin_can_cancel_non_pending_order(self):
        """TC-UNIT-OP-07 | White-box — admin branch skips all user checks
        Admin can cancel a delivered order (rule only applies to non-admins)."""
        allowed, _ = can_user_update_status(
            is_admin=True,
            order_user_id=5,
            current_user_id=1,
            new_status="cancelled",
            current_order_status="delivered",
        )
        assert allowed is True


class TestOrderTotalCalculation:

    # TC-UNIT-OT-01 | BVA — boundary: 0 items | Unit
    def test_empty_items_total_is_zero(self):
        """TC-UNIT-OT-01 | BVA — boundary: empty items list (lower boundary)
        Total of an order with no items must be 0."""
        assert calculate_order_total([]) == 0.0

    # TC-UNIT-OT-02 | EC — valid class: single item | Unit
    def test_single_item_total(self):
        """TC-UNIT-OT-02 | EC — valid class: 1 item
        Total = price × quantity."""
        assert calculate_order_total([{"price": 49.99, "quantity": 2}]) == pytest.approx(99.98)

    # TC-UNIT-OT-03 | EC — valid class: multiple items | Unit
    def test_multiple_items_total_is_summed(self):
        """TC-UNIT-OT-03 | EC — valid class: multiple items
        Total = sum of (price × quantity) for all items."""
        items = [
            {"price": 10.00, "quantity": 3},   # 30.00
            {"price": 5.50,  "quantity": 2},   # 11.00
            {"price": 100.00,"quantity": 1},   # 100.00
        ]
        assert calculate_order_total(items) == pytest.approx(141.00)

    # TC-UNIT-OT-04 | BVA — boundary: price = 0 | Unit
    def test_free_item_does_not_break_total(self):
        """TC-UNIT-OT-04 | BVA — boundary: price = 0 (lower price boundary)
        A free item (price=0) must not crash the calculation."""
        items = [
            {"price": 0.00,  "quantity": 5},
            {"price": 20.00, "quantity": 1},
        ]
        assert calculate_order_total(items) == pytest.approx(20.00)

    # TC-UNIT-OT-05 | BVA — boundary: quantity = 1 | Unit
    def test_minimum_quantity_one(self):
        """TC-UNIT-OT-05 | BVA — boundary: quantity = 1 (minimum allowed)
        Total with quantity=1 must equal the price."""
        assert calculate_order_total([{"price": 299.99, "quantity": 1}]) == pytest.approx(299.99)

    # TC-UNIT-OT-06 | EC — valid class: large order | Unit
    def test_large_order_total(self):
        """TC-UNIT-OT-06 | EC — valid class: large quantity
        Total correctly multiplies large quantities."""
        assert calculate_order_total([{"price": 1.00, "quantity": 1000}]) == pytest.approx(1000.00)

    
