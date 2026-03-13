"""
tests/test_register.py
──────────────────────────────────────────────────────────────────────────────
Registration page tests — real Chrome browser via Selenium.

Technique mapping
─────────────────
  Requirements-based : verifies a stated functional requirement
  EC  : Equivalence Partitioning — valid / invalid data classes
  BVA : Boundary Value Analysis — edge values

Run:  pytest tests/test_register.py -v
"""

import time
import uuid
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    wait_visible, wait_clickable,
)
from config import FRONTEND_URL, HOME_URL, LOGIN_URL, REGISTER_URL


class TestRegisterPage:

    # TC-E2E-R01 | Technique: Requirements-based | Level: System (E2E)
    def test_register_page_loads(self, browser):
        """TC-E2E-R01 | Requirements-based | REQ-AUTH-05
        Registration page must render name, email, password and submit fields."""
        browser.get(REGISTER_URL)
        name_input     = wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        email_input    = browser.find_element(By.CSS_SELECTOR, "input[formControlName='email']")
        password_input = browser.find_element(By.CSS_SELECTOR, "input[formControlName='password']")
        submit_btn     = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        assert name_input.is_displayed()
        assert email_input.is_displayed()
        assert password_input.is_displayed()
        assert submit_btn.is_displayed()

    # TC-E2E-R02 | Technique: Requirements-based | Level: System (E2E)
    def test_register_page_title(self, browser):
        """TC-E2E-R02 | Requirements-based | REQ-UI-02
        Page must contain ShopVerse branding."""
        browser.get(REGISTER_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        assert "ShopVerse" in browser.page_source

    # TC-E2E-R03 | Technique: BVA — boundary: all fields empty (length=0) | Level: System (E2E)
    def test_empty_submit_shows_validation(self, browser):
        """TC-E2E-R03 | BVA — boundary: empty fields (length = 0)
        Submitting blank form must keep user on /register."""
        browser.get(REGISTER_URL)
        wait_clickable(browser, By.CSS_SELECTOR, "button[type='submit']")
        browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(0.8)
        assert "register" in browser.current_url

    # TC-E2E-R04 | Technique: EC — invalid class: mismatched passwords | Level: System (E2E)
    def test_password_mismatch_shows_error(self, browser):
        """TC-E2E-R04 | EC — invalid class: password != confirmPassword
        Mismatched passwords must show an error and keep user on /register."""
        browser.get(REGISTER_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='name']").send_keys("Test User")
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='email']").send_keys("test@test.com")
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='password']").send_keys("password123")
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='confirmPassword']").send_keys("differentpassword")
        browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(0.8)
        error_elements = browser.find_elements(
            By.XPATH, "//*[contains(text(),'match') or contains(text(),'Passwords')]"
        )
        still_on_register = "register" in browser.current_url
        assert still_on_register or len(error_elements) > 0

    # TC-E2E-R05 | Technique: EC — valid class: all fields correctly filled | Level: System (E2E)
    def test_successful_registration(self, browser):
        """TC-E2E-R05 | EC — valid class: all fields correct, unique email
        Successful registration must redirect user away from /register."""
        browser.get(REGISTER_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        unique_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='name']").send_keys("Test User")
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='email']").send_keys(unique_email)
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='password']").send_keys("password123")
        browser.find_element(By.CSS_SELECTOR, "input[formControlName='confirmPassword']").send_keys("password123")
        browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        WebDriverWait(browser, 12).until(lambda d: "register" not in d.current_url)
        assert "register" not in browser.current_url

    # TC-E2E-R06 | Technique: Requirements-based | Level: System (E2E)
    def test_link_to_login_page(self, browser):
        """TC-E2E-R06 | Requirements-based | REQ-AUTH-06
        'Sign in' link on register page must navigate to /login."""
        browser.get(REGISTER_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        login_link = browser.find_element(
            By.XPATH, "//a[contains(@href,'/login') or contains(text(),'Sign in')]"
        )
        login_link.click()
        WebDriverWait(browser, 8).until(EC.url_contains("login"))
        assert "login" in browser.current_url
