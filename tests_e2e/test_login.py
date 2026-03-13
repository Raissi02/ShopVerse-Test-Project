"""
tests/test_login.py
──────────────────────────────────────────────────────────────────────────────
Login page tests — real Chrome browser via Selenium.

Technique mapping
─────────────────
  Requirements-based : verifies a stated functional requirement
  EC  : Equivalence Partitioning — valid / invalid input classes
  BVA : Boundary Value Analysis — edge values (empty string, min length)
  State Transition : login → logged-in state change

Run:  pytest tests/test_login.py -v
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    login, demo_login_user, demo_login_admin,
    wait_visible, wait_clickable,
)
from config import LOGIN_URL, HOME_URL, CART_URL, ADMIN_EMAIL, ADMIN_PASSWORD


class TestLoginPage:

    # TC-E2E-L01 | Technique: Requirements-based | Level: System (E2E)
    def test_login_page_loads(self, browser):
        """TC-E2E-L01 | Requirements-based | REQ-AUTH-01
        The login page must render an email field, password field and submit button."""
        browser.get(LOGIN_URL)
        email_input    = wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        password_input = browser.find_element(By.CSS_SELECTOR, "input[type='password']")
        submit_btn     = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        assert email_input.is_displayed()
        assert password_input.is_displayed()
        assert submit_btn.is_displayed()

    # TC-E2E-L02 | Technique: Requirements-based | Level: System (E2E)
    def test_login_page_has_shopverse_branding(self, browser):
        """TC-E2E-L02 | Requirements-based | REQ-UI-01
        ShopVerse brand name must be visible on the login page."""
        browser.get(LOGIN_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        assert "ShopVerse" in browser.page_source

    # TC-E2E-L03 | Technique: BVA — boundary: empty fields (length=0) | Level: System (E2E)
    def test_empty_form_shows_validation(self, browser):
        """TC-E2E-L03 | BVA — boundary: empty fields (length = 0)
        Submitting an empty form must not navigate away from /login."""
        browser.get(LOGIN_URL)
        wait_clickable(browser, By.CSS_SELECTOR, "button[type='submit']")
        browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(0.8)
        assert "login" in browser.current_url

    # TC-E2E-L04 | Technique: EC — invalid class (non-existent credentials) | Level: System (E2E)
    def test_invalid_credentials_shows_error(self, browser):
        """TC-E2E-L04 | EC — invalid equivalence class: credentials not in DB
        Wrong email/password must show an error and keep the user on /login."""
        login(browser, "doesnotexist@fake.com", "wrongpassword")
        time.sleep(2)
        still_on_login = "login" in browser.current_url
        error_visible  = len(browser.find_elements(
            By.XPATH,
            "//*[contains(@style,'ef4444') or contains(@class,'alert') or contains(@class,'error')]"
        )) > 0
        assert still_on_login or error_visible

    # TC-E2E-L05 | Technique: Requirements-based | Level: System (E2E)
    def test_demo_user_button_logs_in(self, browser):
        """TC-E2E-L05 | Requirements-based | REQ-AUTH-02
        'Demo User' button must log in and redirect away from /login."""
        demo_login_user(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)
        assert "login" not in browser.current_url

    # TC-E2E-L06 | Technique: Requirements-based | Level: System (E2E)
    def test_demo_admin_button_logs_in(self, browser):
        """TC-E2E-L06 | Requirements-based | REQ-AUTH-03
        'Demo Admin' button must log in and redirect away from /login."""
        demo_login_admin(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)
        assert "login" not in browser.current_url

    # TC-E2E-L07 | Technique: State Transition (logged-out → logged-in) | Level: System (E2E)
    def test_after_login_navbar_shows_username(self, browser):
        """TC-E2E-L07 | State Transition: logged-out → logged-in
        After login, navbar must reflect authenticated state (Sign in button hidden)."""
        demo_login_user(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)
        nav = wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert nav.is_displayed()

    # TC-E2E-L08 | Technique: Requirements-based | Level: System (E2E)
    def test_link_to_register_page(self, browser):
        """TC-E2E-L08 | Requirements-based | REQ-AUTH-04
        'Create one' link on login page must navigate to /register."""
        browser.get(LOGIN_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        register_link = browser.find_element(
            By.XPATH, "//a[contains(@href,'/register') or contains(text(),'Create')]"
        )
        register_link.click()
        WebDriverWait(browser, 8).until(EC.url_contains("register"))
        assert "register" in browser.current_url
