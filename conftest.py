"""
conftest.py
─────────────────────────────────────────────────────────────────────────────
Root pytest configuration — Selenium browser fixture and shared E2E helpers.

pytest automatically makes everything defined here available to all test
files in this directory and every subdirectory, with no imports needed for
fixtures. Helper functions (wait_for, login, …) are imported explicitly by
the test files that need them.

All constants (URLs, credentials) live in config.py — import from there.
─────────────────────────────────────────────────────────────────────────────
"""

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import LOGIN_URL, ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD


# ── Browser fixture ───────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def browser():
    """
    Opens a real Chrome window for each test.
    scope="function" — fresh browser per test, no state leaks between tests.
    """
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)

    yield driver

    driver.quit()


# ── Logged-in browser fixtures ────────────────────────────────────────────────

def logged_in_user(browser):
    """Fixture that returns a logged-in browser session"""
    demo_login_user(browser)
    WebDriverWait(browser, 10).until(
        lambda d: "login" not in d.current_url
    )
    return browser


def logged_in_admin(browser):
    """
    Fixture: browser already logged in as the demo admin.
    """
    demo_login_admin(browser)
    WebDriverWait(browser, 10).until(
        lambda d: "login" not in d.current_url
    )
    return browser


# ── Wait helpers ──────────────────────────────────────────────────────────────

def wait_for(driver, by, selector, timeout=10):
    """Wait until element is present in the DOM."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, selector))
    )


def wait_visible(driver, by, selector, timeout=10):
    """Wait until element is visible."""
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, selector))
    )


def wait_clickable(driver, by, selector, timeout=10):
    """Wait until element is clickable."""
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, selector))
    )


# ── Login helpers ─────────────────────────────────────────────────────────────

def login(driver, email, password):
    """Log in via the email/password form."""
    driver.get(LOGIN_URL)
    wait_visible(driver, By.CSS_SELECTOR, "input[type='email']")
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").clear()
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(email)
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").clear()
    driver.find_element(By.CSS_SELECTOR, "input[type='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()


def demo_login_user(driver):
    """Log in via the 'Demo User' shortcut button on the login page."""
    driver.get(LOGIN_URL)
    wait_clickable(driver, By.XPATH, "//button[contains(text(),'Demo User')]")
    driver.find_element(By.XPATH, "//button[contains(text(),'Demo User')]").click()


def demo_login_admin(driver):
    """Log in via the 'Demo Admin' shortcut button on the login page."""
    driver.get(LOGIN_URL)
    wait_clickable(driver, By.XPATH, "//button[contains(text(),'Demo Admin')]")
    driver.find_element(By.XPATH, "//button[contains(text(),'Demo Admin')]").click()
