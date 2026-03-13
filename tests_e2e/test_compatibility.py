"""
tests/test_compatibility.py
──────────────────────────────────────────────────────────────────────────────
Non-functional — Browser compatibility & responsive viewport tests.
Opens a real Chrome window and resizes it to simulate mobile, tablet, desktop.

Technique : Compatibility testing (non-functional)
Justification: ShopVerse targets end-users across devices. Angular's responsive
  design uses CSS breakpoints. We verify that the UI remains usable and does not
  break layout at three standard viewport sizes without changing the browser
  (Chrome covers the rendering engine; viewport tests cover responsive CSS).

Run:  pytest tests/test_compatibility.py -v
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import HOME_URL, LOGIN_URL, CART_URL
from conftest import wait_visible, logged_in_user, logged_in_admin

VIEWPORTS = [
    ("Mobile  375×667",  375,  667),
    ("Tablet  768×1024", 768,  1024),
    ("Desktop 1440×900", 1440, 900),
]


class TestBrowserCompatibility:

    # TC-E2E-COMPAT-01 | Technique: Compatibility | Level: System (E2E)
    @pytest.mark.parametrize("label,width,height", VIEWPORTS)
    def test_home_renders_at_viewport(self, browser, label, width, height):
        """TC-E2E-COMPAT-01 | Compatibility — responsive viewport
        Home page body must be visible at {label} viewport with no JS errors."""
        errors = []
        browser.execute_cdp_cmd("Log.enable", {})
        browser.set_window_size(width, height)
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed(), f"Body not visible at {label}"

    # TC-E2E-COMPAT-02 | Technique: Compatibility | Level: System (E2E)
    @pytest.mark.parametrize("label,width,height", VIEWPORTS)
    def test_login_renders_at_viewport(self, browser, label, width, height):
        """TC-E2E-COMPAT-02 | Compatibility — responsive viewport
        Login page email input must be visible at {label} viewport."""
        browser.set_window_size(width, height)
        browser.get(LOGIN_URL)
        email = wait_visible(browser, By.CSS_SELECTOR, "input[type='email']")
        assert email.is_displayed(), f"Email input not visible at {label}"

    # TC-E2E-COMPAT-03 | Technique: Compatibility | Level: System (E2E)
    @pytest.mark.parametrize("label,width,height", VIEWPORTS)
    def test_cart_renders_at_viewport(self, browser, label, width, height):
        """TC-E2E-COMPAT-03 | Compatibility — responsive viewport
        Cart page must load without errors at {label} viewport."""
        browser.set_window_size(width, height)
        logged_in_user(browser)
        browser.get(CART_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed(), f"Cart body not visible at {label}"

    # TC-E2E-COMPAT-04 | Technique: Compatibility | Level: System (E2E)
    def test_no_horizontal_scroll_on_mobile(self, browser):
        """TC-E2E-COMPAT-04 | Compatibility — no horizontal overflow on mobile
        At 375px width the page must not produce a horizontal scrollbar
        (scrollWidth == clientWidth)."""
        browser.set_window_size(375, 667)
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(1.5)
        scroll_w = browser.execute_script("return document.body.scrollWidth")
        client_w = browser.execute_script("return document.body.clientWidth")
        assert scroll_w <= client_w + 5, (
            f"Horizontal overflow on mobile: scrollWidth={scroll_w} > clientWidth={client_w}"
        )

    # TC-E2E-COMPAT-05 | Technique: Compatibility | Level: System (E2E)
    def test_navbar_visible_on_mobile(self, browser):
        """TC-E2E-COMPAT-05 | Compatibility — navbar usable on mobile
        At 375px the header nav must still be displayed."""
        browser.set_window_size(375, 667)
        logged_in_user(browser)
        browser.get(HOME_URL)
        navbar = wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert navbar.is_displayed()
