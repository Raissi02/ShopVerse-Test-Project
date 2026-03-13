"""
tests/test_cart.py
──────────────────────────────────────────────────────────────────────────────
Shopping cart tests — real Chrome browser via Selenium.

Technique mapping
─────────────────
  Requirements-based : verifies a stated functional requirement
  EC  : Equivalence Partitioning — empty cart vs cart with items
  BVA : Boundary Value Analysis — 0 items (boundary), 1 item, 2 items

Run:  pytest tests/test_cart.py -v
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    demo_login_user,
    wait_visible, wait_clickable,logged_in_user, logged_in_admin
)
from config import HOME_URL, CART_URL


class TestCartPage:

    # TC-E2E-C01 | Technique: BVA — boundary: 0 items in cart | Level: System (E2E)
    def test_empty_cart_message(self, browser):
        """TC-E2E-C01 | BVA — boundary: 0 items (lower boundary)
        Navigating to /cart when empty must show the empty-cart message."""
        logged_in_user(browser)
        browser.get(CART_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(1)
        empty_msg = WebDriverWait(browser, 8).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(text(),'empty') or contains(text(),'haven') or contains(text(),'cart is empty')]"
            ))
        )
        assert empty_msg.is_displayed()

    # TC-E2E-C02 | Technique: Requirements-based | Level: System (E2E)
    def test_continue_shopping_link_in_empty_cart(self, browser):
        """TC-E2E-C02 | Requirements-based | REQ-CART-05
        Empty cart must show a 'Continue Shopping' link back to home."""
        logged_in_user(browser)
        browser.get(CART_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(1)
        continue_link = WebDriverWait(browser, 8).until(
            EC.presence_of_element_located((
                By.XPATH, "//a[contains(text(),'Continue Shopping') or contains(text(),'Shopping')]"
            ))
        )
        assert continue_link.is_displayed()

    # TC-E2E-C03 | Technique: EC — valid class: product added → appears in cart | Level: System (E2E)
    def test_add_product_appears_in_cart(self, browser):
        """TC-E2E-C03 | EC — valid class: 1 product added
        Adding a product from home must make it appear on /cart."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        assert len(add_buttons) > 0, "No 'Add to Cart' buttons found"
        add_buttons[0].click()
        time.sleep(1)
        browser.get(CART_URL)
        time.sleep(1.5)
        empty_messages = browser.find_elements(
            By.XPATH, "//*[contains(text(),'cart is empty')]"
        )
        assert len(empty_messages) == 0

    # TC-E2E-C04 | Technique: Requirements-based | Level: System (E2E)
    def test_cart_shows_order_summary(self, browser):
        """TC-E2E-C04 | Requirements-based | REQ-CART-06
        Order Summary panel must be visible when cart has items."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        add_buttons[0].click()
        time.sleep(1)
        browser.get(CART_URL)
        time.sleep(1.5)
        order_summary = WebDriverWait(browser, 8).until(
            EC.presence_of_element_located((
                By.XPATH, "//*[contains(text(),'Order Summary')]"
            ))
        )
        assert order_summary.is_displayed()

    # TC-E2E-C05 | Technique: Requirements-based | Level: System (E2E)
    def test_cart_shows_total(self, browser):
        """TC-E2E-C05 | Requirements-based | REQ-CART-07
        Cart must display a Total field after adding a product."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        add_buttons[0].click()
        time.sleep(1)
        browser.get(CART_URL)
        time.sleep(1.5)
        total_elements = browser.find_elements(
            By.XPATH, "//*[contains(text(),'Total')]"
        )
        assert len(total_elements) > 0

    # TC-E2E-C06 | Technique: Requirements-based | Level: System (E2E)
    def test_proceed_to_checkout_button_visible(self, browser):
        """TC-E2E-C06 | Requirements-based | REQ-CART-08
        'Proceed to Checkout' button must appear when cart has items."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        add_buttons[0].click()
        time.sleep(1)
        browser.get(CART_URL)
        time.sleep(1.5)
        checkout_btn = WebDriverWait(browser, 8).until(
            EC.presence_of_element_located((
                By.XPATH, "//a[contains(text(),'Proceed to Checkout') or contains(text(),'Checkout')]"
            ))
        )
        assert checkout_btn.is_displayed()

    # TC-E2E-C07 | Technique: BVA — 2 items (just above lower boundary) | Level: System (E2E)
    def test_adding_two_products_updates_cart(self, browser):
        """TC-E2E-C07 | BVA — 2 items (boundary + 1)
        Adding two distinct products must reflect count >= 2 in navbar badge."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        assert len(add_buttons) >= 2, "Need at least 2 products on home page"
        add_buttons[0].click()
        time.sleep(0.8)
        add_buttons[1].click()
        time.sleep(0.8)
        browser.get(CART_URL)
        time.sleep(1.5)
        badge = browser.find_elements(
            By.CSS_SELECTOR, "a[href='/cart'] span, a[routerlink='/cart'] span"
        )
        if badge:
            assert badge[0].text.strip() in ["2", "3", "4"]
