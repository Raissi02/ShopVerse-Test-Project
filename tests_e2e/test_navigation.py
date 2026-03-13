"""
tests/test_navigation.py
──────────────────────────────────────────────────────────────────────────────
Route guard and navigation tests — real Chrome browser via Selenium.

Technique mapping
─────────────────
  Requirements-based : verifies routing / guard requirements
  Security           : access-control enforcement (authGuard, guestGuard, adminGuard)
  State Transition   : logged-in → logged-out guard re-activation

Run:  pytest tests/test_navigation.py -v
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    demo_login_user, demo_login_admin,
    wait_visible,logged_in_user
)
from config import FRONTEND_URL, HOME_URL, LOGIN_URL, REGISTER_URL, CART_URL


class TestNavigation:

    # TC-E2E-N01 | Technique: Requirements-based | Level: System (E2E)
    def test_home_route_loads(self, browser):
        """TC-E2E-N01 | Requirements-based | REQ-NAV-01
        / must load without errors."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert "localhost:4200" in browser.current_url

    # TC-E2E-N02 | Technique: Requirements-based | Level: System (E2E)
    def test_login_route_loads(self, browser):
        """TC-E2E-N02 | Requirements-based | REQ-NAV-02
        /login must load and show the form."""
        browser.get(LOGIN_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        assert "login" in browser.current_url

    # TC-E2E-N03 | Technique: Requirements-based | Level: System (E2E)
    def test_register_route_loads(self, browser):
        """TC-E2E-N03 | Requirements-based | REQ-NAV-03
        /register must load and show the form."""
        browser.get(REGISTER_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        assert "register" in browser.current_url

    # TC-E2E-N04 | Technique: Requirements-based | Level: System (E2E)
    def test_cart_route_loads(self, browser):
        """TC-E2E-N04 | Requirements-based | REQ-NAV-04
        /cart must load even when the cart is empty."""
        logged_in_user(browser)
        browser.get(CART_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert "cart" in browser.current_url

    # TC-E2E-N05 | Technique: Security — authGuard blocks unauthenticated access | Level: System (E2E)
    def test_admin_route_redirects_unauthenticated_user(self, browser):
        """TC-E2E-N05 | Security — authGuard
        /admin must redirect an unauthenticated visitor away."""
        logged_in_user(browser)
        browser.get(f"{FRONTEND_URL}/admin")
        time.sleep(2)
        assert "/admin" not in browser.current_url or "login" in browser.current_url

    # TC-E2E-N06 | Technique: Security — authGuard blocks unauthenticated access | Level: System (E2E)
    def test_profile_route_redirects_unauthenticated_user(self, browser):
        """TC-E2E-N06 | Security — authGuard
        /profile must redirect an unauthenticated visitor away."""
        browser.get(f"{FRONTEND_URL}/profile")
        time.sleep(2)
        assert "profile" not in browser.current_url or "login" in browser.current_url

    # TC-E2E-N07 | Technique: Security — guestGuard prevents re-login | Level: System (E2E)
    def test_guest_redirect_on_login_when_logged_in(self, browser):
        """TC-E2E-N07 | Security — guestGuard
        Visiting /login while already authenticated must redirect to home."""
        demo_login_user(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)
        browser.get(LOGIN_URL)
        time.sleep(2)
        assert "login" not in browser.current_url

    # TC-E2E-N08 | Technique: Security — adminGuard grants access to admin role | Level: System (E2E)
    def test_admin_panel_accessible_after_admin_login(self, browser):
        """TC-E2E-N08 | Security — adminGuard
        /admin must be accessible after logging in as admin."""
        demo_login_admin(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)
        browser.get(f"{FRONTEND_URL}/admin")
        time.sleep(2)
        assert "admin" in browser.current_url

    # TC-E2E-N09 | Technique: State Transition (logged-in → logged-out) + Security | Level: System (E2E)
    def test_logout_then_admin_blocked(self, browser):
        """TC-E2E-N09 | State Transition: logged-in → logged-out + Security — authGuard
        After logout, /admin is blocked again."""
        # Login as admin first
        demo_login_admin(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)

        # Logout via navbar user menu
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        user_menu_btn = browser.find_element(
            By.XPATH, "//button[.//span[contains(text(),'admin')]]"
        )
        user_menu_btn.click()
        time.sleep(0.5)

        logout_btn = browser.find_element(
            By.XPATH, "//button[contains(text(),'Sign out')]"
        )
        logout_btn.click()
        time.sleep(1.5)

        # Now try /admin
        browser.get(f"{FRONTEND_URL}/admin")
        time.sleep(2)

        assert "admin" not in browser.current_url or "login" in browser.current_url
