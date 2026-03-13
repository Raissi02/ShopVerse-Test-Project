"""
tests/test_home.py
──────────────────────────────────────────────────────────────────────────────
Home page and product listing tests — real Chrome browser via Selenium.

Technique mapping
─────────────────
  Requirements-based : verifies a stated functional requirement
  EC  : Equivalence Partitioning — valid / invalid search/filter inputs
  State Transition   : anonymous → authenticated navbar state

Run:  pytest tests/test_home.py -v
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    browser,
    demo_login_user,
    wait_visible, wait_clickable,logged_in_user, logged_in_admin
)
from config import HOME_URL, LOGIN_URL, CART_URL


class TestHomePage:

    # TC-E2E-H01 | Technique: Requirements-based | Level: System (E2E)
    def test_home_page_loads(self, browser):
        """TC-E2E-H01 | Requirements-based | REQ-HOME-01
        Home page must load and show the navbar."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        navbar = wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert navbar.is_displayed()

    # TC-E2E-H02 | Technique: Requirements-based | Level: System (E2E)
    def test_shopverse_logo_in_navbar(self, browser):
        """TC-E2E-H02 | Requirements-based | REQ-UI-03
        ShopVerse logo must be visible in the navbar."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        assert "ShopVerse" in browser.page_source

    # TC-E2E-H03 | Technique: Requirements-based | Level: System (E2E)
    def test_product_cards_are_displayed(self, browser):
        """TC-E2E-H03 | Requirements-based | REQ-PROD-01
        At least one product card must appear on the home page."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        WebDriverWait(browser, 12).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[ng-reflect-router-link], a[href*='/products/']")
            )
        )
        product_cards = browser.find_elements(
            By.CSS_SELECTOR, "a[ng-reflect-router-link], a[href*='/products/']"
        )
        assert len(product_cards) > 0

    # TC-E2E-H04 | Technique: Requirements-based | Level: System (E2E)
    def test_search_box_is_visible(self, browser):
        """TC-E2E-H04 | Requirements-based | REQ-PROD-02
        Search input must be present on the home page."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(1)
        search = browser.find_element(
            By.XPATH, "//input[@placeholder[contains(.,'Search')]]"
        )
        assert search.is_displayed()

    # TC-E2E-H05 | Technique: EC — valid class: known product name | Level: System (E2E)
    def test_search_filters_products(self, browser):
        """TC-E2E-H05 | EC — valid class: typing a product keyword filters the list.
        REQ-PROD-03: Search must filter displayed products."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        search = browser.find_element(
            By.XPATH, "//input[@placeholder[contains(.,'Search')]]"
        )
        search.clear()
        search.send_keys("laptop")
        time.sleep(1.5)
        page_source = browser.page_source
        assert "laptop" in page_source.lower() or "No products found" in page_source

    # TC-E2E-H06 | Technique: Requirements-based | Level: System (E2E)
    def test_category_dropdown_exists(self, browser):
        """TC-E2E-H06 | Requirements-based | REQ-PROD-04
        Category filter dropdown must be visible."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(1)
        category_select = browser.find_element(
            By.XPATH, "//select[.//option[contains(text(),'All Categories')]]"
        )
        assert category_select.is_displayed()

    # TC-E2E-H07 | Technique: Requirements-based | Level: System (E2E)
    def test_cart_icon_in_navbar(self, browser):
        """TC-E2E-H07 | Requirements-based | REQ-CART-01
        Cart icon link must be visible in the navbar."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        cart_link = browser.find_element(
            By.CSS_SELECTOR, "a[href='/cart'], a[routerlink='/cart']"
        )
        assert cart_link.is_displayed()

    # TC-E2E-H08 | Technique: Requirements-based | Level: System (E2E)
    def test_cart_icon_navigates_to_cart(self, browser):
        """TC-E2E-H08 | Requirements-based | REQ-CART-02
        Clicking the cart icon must navigate to /cart."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        cart_link = browser.find_element(
            By.XPATH, "//a[contains(@href,'/cart') or @routerlink='/cart']"
        )
        cart_link.click()
        WebDriverWait(browser, 8).until(EC.url_contains("cart"))
        assert "cart" in browser.current_url

    # TC-E2E-H09 | Technique: Requirements-based | Level: System (E2E)
    def test_add_to_cart_button_exists_on_product(self, browser):
        """TC-E2E-H09 | Requirements-based | REQ-CART-03
        At least one 'Add to Cart' button must be visible on the home page."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        assert len(add_buttons) > 0

    # TC-E2E-H10 | Technique: EC — valid action triggers state change | Level: System (E2E)
    def test_add_to_cart_updates_navbar_count(self, browser):
        """TC-E2E-H10 | EC — valid class: adding a product increments cart badge.
        REQ-CART-04: Cart counter must update after Add to Cart."""
        logged_in_user(browser)
        browser.get(HOME_URL)
        wait_visible(browser, By.CSS_SELECTOR, "header nav")
        time.sleep(2)
        add_buttons = browser.find_elements(
            By.XPATH, "//button[contains(text(),'Add to Cart')]"
        )
        assert len(add_buttons) > 0, "No 'Add to Cart' buttons found"
        add_buttons[0].click()
        time.sleep(1.5)
        badge = WebDriverWait(browser, 8).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href='/cart'] span, a[routerlink='/cart'] span")
            )
        )
        assert badge.text.strip() in ["1", "2", "3", "4", "5"]
        

    # TC-E2E-H12 | Technique: State Transition (anonymous → authenticated) | Level: System (E2E)
    def test_user_menu_visible_after_login(self, browser):
        """TC-E2E-H12 | State Transition: anonymous → authenticated
        After demo login the 'Sign in' button must disappear from navbar."""
        demo_login_user(browser)
        WebDriverWait(browser, 10).until(lambda d: "login" not in d.current_url)
        sign_in_buttons = browser.find_elements(
            By.XPATH, "//a[contains(text(),'Sign in')]"
        )
        assert len(sign_in_buttons) == 0
