"""
config.py
─────────────────────────────────────────────────────────────────────────────
Central configuration for the entire ShopVerse test suite.

All URLs, ports, and credentials live here — one place to change when the
app is deployed to a different host or when passwords are rotated.

Import from anywhere in the suite:
    from config import FRONTEND_URL, API_URL, ADMIN_EMAIL, ADMIN_PASSWORD
─────────────────────────────────────────────────────────────────────────────
"""

# ── Backend (API) ─────────────────────────────────────────────────────────────
API_URL = "http://localhost:5000"

# ── Frontend (Angular) ────────────────────────────────────────────────────────
FRONTEND_URL  = "http://localhost:4200"
LOGIN_URL     = f"{FRONTEND_URL}/login"
REGISTER_URL  = f"{FRONTEND_URL}/register"
CART_URL      = f"{FRONTEND_URL}/cart"
HOME_URL      = FRONTEND_URL

# ── Seeded admin credentials (BCrypt hash in AppDbContext.cs seed data) ───────
ADMIN_EMAIL    = "admin@shopverse.com"
ADMIN_PASSWORD = "admin123"          # lowercase — confirmed from AppDbContext seed

# ── Seeded regular-user credentials ──────────────────────────────────────────
USER_EMAIL    = "rabie@shopverse.com"
USER_PASSWORD = "user123"

# ── Test-user defaults (used when registering throwaway accounts) ─────────────
TEST_USER_PASSWORD = "TestPass123"
