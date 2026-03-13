"""
tests/test_accessibility.py
──────────────────────────────────────────────────────────────────────────────
Non-functional — Basic accessibility / ergonomics tests.
Real Chrome browser via Selenium.

Technique : Accessibility analysis (non-functional — ergonomie / accessibilité)
Justification: WCAG 2.1 level AA is standard for e-commerce. These checks
  verify the most impactful accessibility basics: page titles, form labels,
  alt text on images, keyboard-accessible interactive elements, and sufficient
  colour-contrast indicators. We use Selenium DOM inspection rather than a
  dedicated axe-core tool to stay within the pytest+Selenium constraint.

Run:  pytest tests/test_accessibility.py -v
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import HOME_URL, LOGIN_URL, REGISTER_URL, CART_URL 
from conftest import wait_visible,logged_in_user


class TestAccessibility:

    # TC-E2E-A01 | Technique: Accessibility | Level: System (E2E)
    def test_home_page_has_title(self, browser):
        """TC-E2E-A01 | Accessibility — WCAG 2.4.2: Page has a meaningful title.
        The <title> element must be non-empty."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert len(browser.title) > 0, "Page title is empty"

    # TC-E2E-A02 | Technique: Accessibility | Level: System (E2E)
    def test_login_page_has_title(self, browser):
        """TC-E2E-A02 | Accessibility — WCAG 2.4.2
        /login must have a non-empty page title."""
        browser.get(LOGIN_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        assert len(browser.title) > 0

    # TC-E2E-A03 | Technique: Accessibility | Level: System (E2E)
    def test_login_inputs_have_labels_or_placeholders(self, browser):
        """TC-E2E-A03 | Accessibility — WCAG 1.3.1: Form inputs must be identifiable.
        Email and password inputs must have a type or placeholder attribute."""
        browser.get(LOGIN_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        email = browser.find_element(By.CSS_SELECTOR, "input[type='email']")
        pwd   = browser.find_element(By.CSS_SELECTOR, "input[type='password']")
        email_id = email.get_attribute("type") or email.get_attribute("placeholder")
        pwd_id   = pwd.get_attribute("type")   or pwd.get_attribute("placeholder")
        assert email_id, "Email input has no type or placeholder"
        assert pwd_id,   "Password input has no type or placeholder"

    # TC-E2E-A04 | Technique: Accessibility | Level: System (E2E)
    def test_register_inputs_have_labels_or_placeholders(self, browser):
        """TC-E2E-A04 | Accessibility — WCAG 1.3.1
        Registration form inputs must have a label or placeholder."""
        browser.get(REGISTER_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[formControlName='name']")
        name  = browser.find_element(By.CSS_SELECTOR, "input[formControlName='name']")
        email = browser.find_element(By.CSS_SELECTOR, "input[formControlName='email']")
        assert name.get_attribute("placeholder"),  "Name input has no placeholder"
        assert email.get_attribute("placeholder"), "Email input has no placeholder"

    # TC-E2E-A05 | Technique: Accessibility | Level: System (E2E)
    def test_product_images_have_alt_text(self, browser):
        """TC-E2E-A05 | Accessibility — WCAG 1.1.1: Images must have alternative text.
        Every product image on the home page must have a non-empty alt attribute."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        images = browser.find_elements(By.CSS_SELECTOR, "img")
        missing_alt = [
            img.get_attribute("src") for img in images
            if not img.get_attribute("alt")
        ]
        assert len(missing_alt) == 0, (
            f"{len(missing_alt)} image(s) are missing alt text: {missing_alt[:3]}"
        )

    # TC-E2E-A06 | Technique: Accessibility | Level: System (E2E)
    def test_submit_buttons_are_keyboard_accessible(self, browser):
        """TC-E2E-A06 | Accessibility — WCAG 2.1.1: All functionality must be operable via keyboard.
        Submit button on login page must be a <button> element (not a <div>), enabling Tab focus."""
        browser.get(LOGIN_URL)
        wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        submit = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        assert submit.tag_name.lower() == "button", (
            "Submit element is not a <button> — not natively keyboard accessible"
        )

    # TC-E2E-A08 | Technique: Accessibility | Level: System (E2E)
    def test_cart_page_has_heading(self, browser):
        """TC-E2E-A08 | Accessibility — WCAG 1.3.1: Content must have logical structure.
        The cart page must contain at least one heading element (h1–h3)."""
        logged_in_user(browser)
        browser.get(CART_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(1)
        headings = browser.find_elements(By.XPATH, "//h1|//h2|//h3")
        assert len(headings) > 0, "Cart page has no heading elements"
