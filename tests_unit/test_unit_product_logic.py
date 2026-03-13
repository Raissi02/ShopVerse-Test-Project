"""
tests_unit/test_unit_product_logic.py
─────────────────────────────────────────────────────────────────────────────
Unit tests — Product business logic  (mirrors ProductsController.cs rules)

Tests the pure rules extracted from the backend:
  - Search filter logic  (name or description contains keyword)
  - Category filter logic
  - Price range filter   (minPrice / maxPrice)
  - Sorting logic        (price-asc, price-desc, alpha-asc, alpha-desc)
  - Soft-delete flag     (IsActive = false → hidden from listing)
  - Pagination           (skip/take)

NO HTTP calls — runs instantly without the backend being started.

Technique : EC + BVA + Requirements-based + White-box
Level     : Unit
─────────────────────────────────────────────────────────────────────────────
"""

import pytest


# ── Business logic extracted from ProductsController.cs ──────────────────────

def apply_search(products: list[dict], keyword: str) -> list[dict]:
    """
    Mirrors:
      query = query.Where(p => p.Name.Contains(search)
                            || p.Description.Contains(search))
    Case-insensitive, matching the SQLite LIKE default.
    """
    if not keyword or not keyword.strip():
        return products
    kw = keyword.lower()
    return [p for p in products
            if kw in p["name"].lower() or kw in p["description"].lower()]


def apply_category_filter(products: list[dict], category_id: int) -> list[dict]:
    """Mirrors: query = query.Where(p => p.CategoryId == categoryId)"""
    return [p for p in products if p["categoryId"] == category_id]


def apply_price_range(products: list[dict],
                      min_price: float = None,
                      max_price: float = None) -> list[dict]:
    """
    Mirrors:
      if (minPrice.HasValue) query = query.Where(p => p.Price >= minPrice)
      if (maxPrice.HasValue) query = query.Where(p => p.Price <= maxPrice)
    """
    result = products
    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]
    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]
    return result


def apply_sort(products: list[dict], sort_by: str) -> list[dict]:
    """
    Mirrors the sortBy switch in ProductsController.GetAll:
      "price-asc"  → OrderBy(p => p.Price)
      "price-desc" → OrderByDescending(p => p.Price)
      "alpha-asc"  → OrderBy(p => p.Name)
      "alpha-desc" → OrderByDescending(p => p.Name)
      default      → OrderBy(p => p.Id)
    """
    if sort_by == "price-asc":
        return sorted(products, key=lambda p: p["price"])
    if sort_by == "price-desc":
        return sorted(products, key=lambda p: p["price"], reverse=True)
    if sort_by == "alpha-asc":
        return sorted(products, key=lambda p: p["name"])
    if sort_by == "alpha-desc":
        return sorted(products, key=lambda p: p["name"], reverse=True)
    return sorted(products, key=lambda p: p["id"])


def apply_pagination(products: list[dict], page: int, page_size: int) -> list[dict]:
    """Mirrors: .Skip((page - 1) * pageSize).Take(pageSize)"""
    start = (page - 1) * page_size
    return products[start: start + page_size]


def filter_active(products: list[dict]) -> list[dict]:
    """Mirrors: .Where(p => p.IsActive)"""
    return [p for p in products if p["isActive"]]


# ── Fixtures ──────────────────────────────────────────────────────────────────

PRODUCTS = [
    {"id": 101, "name": "Pro Laptop X1 Ultra",            "description": "High-performance ultrabook",  "price": 1299.99, "categoryId": 1, "isActive": True},
    {"id": 102, "name": "Wireless Headphones",            "description": "Premium noise cancelling",     "price":  249.99, "categoryId": 1, "isActive": True},
    {"id": 103, "name": "Slim-Fit Premium Blazer",        "description": "Italian wool blend blazer",    "price":  189.99, "categoryId": 2, "isActive": True},
    {"id": 104, "name": "18K Gold Pendant Necklace",      "description": "Delicate gold plated chain",   "price":   89.99, "categoryId": 3, "isActive": True},
    {"id": 119, "name": "Smart LED Strip Lights 5m",      "description": "WiFi controlled 16M colors",   "price":   24.99, "categoryId": 4, "isActive": True},
    {"id": 999, "name": "Deleted Product",                "description": "This product was removed",     "price":    9.99, "categoryId": 1, "isActive": False},
]


class TestSoftDelete:

    # TC-UNIT-PL-01 | Requirements-based | Unit
    def test_inactive_products_excluded_from_listing(self):
        """TC-UNIT-PL-01 | Requirements-based | REQ-PROD-01
        .Where(p => p.IsActive) must exclude soft-deleted products."""
        active = filter_active(PRODUCTS)
        ids = [p["id"] for p in active]
        assert 999 not in ids

    # TC-UNIT-PL-02 | Requirements-based | Unit
    def test_active_products_are_included(self):
        """TC-UNIT-PL-02 | Requirements-based
        All IsActive=true products must appear in the filtered listing."""
        active = filter_active(PRODUCTS)
        assert len(active) == 5

    # TC-UNIT-PL-03 | BVA — boundary: all inactive | Unit
    def test_all_inactive_returns_empty_list(self):
        """TC-UNIT-PL-03 | BVA — boundary: all products inactive
        Filtering all-inactive products returns empty list."""
        all_inactive = [{"id": i, "name": "x", "description": "x",
                         "price": 1.0, "categoryId": 1, "isActive": False}
                        for i in range(3)]
        assert filter_active(all_inactive) == []


class TestSearchFilter:

    # TC-UNIT-PL-04 | EC — valid class: keyword matches name | Unit
    def test_search_matches_product_name(self):
        """TC-UNIT-PL-04 | EC — valid class: keyword in product name
        Search 'laptop' must return products whose name contains 'laptop'."""
        result = apply_search(PRODUCTS, "laptop")
        assert len(result) == 1
        assert result[0]["name"] == "Pro Laptop X1 Ultra"

    # TC-UNIT-PL-05 | EC — valid class: keyword matches description | Unit
    def test_search_matches_product_description(self):
        """TC-UNIT-PL-05 | EC — valid class: keyword in description
        Search 'wool' must return the blazer (keyword in description)."""
        result = apply_search(PRODUCTS, "wool")
        assert len(result) == 1
        assert result[0]["id"] == 103

    # TC-UNIT-PL-06 | EC — invalid class: no match | Unit
    def test_search_no_match_returns_empty(self):
        """TC-UNIT-PL-06 | EC — invalid class: keyword not in any product
        Search for a non-existent keyword must return empty list."""
        result = apply_search(PRODUCTS, "zzznomatch")
        assert result == []

    # TC-UNIT-PL-07 | BVA — boundary: empty keyword | Unit
    def test_search_empty_keyword_returns_all(self):
        """TC-UNIT-PL-07 | BVA — boundary: empty search string
        Empty keyword must return all products (no filter applied)."""
        result = apply_search(PRODUCTS, "")
        assert len(result) == len(PRODUCTS)

    # TC-UNIT-PL-08 | EC — valid class: case-insensitive | Unit
    def test_search_is_case_insensitive(self):
        """TC-UNIT-PL-08 | EC — valid class: uppercase keyword
        Search is case-insensitive — 'LAPTOP' must match 'Pro Laptop X1 Ultra'."""
        result = apply_search(PRODUCTS, "LAPTOP")
        assert len(result) == 1


class TestCategoryFilter:

    # TC-UNIT-PL-09 | EC — valid class: matching category | Unit
    def test_category_filter_returns_only_matching(self):
        """TC-UNIT-PL-09 | EC — valid class: categoryId=1 (Electronics)
        Only products in category 1 must be returned."""
        result = apply_category_filter(PRODUCTS, 1)
        for p in result:
            assert p["categoryId"] == 1

    # TC-UNIT-PL-10 | EC — invalid class: non-existent category | Unit
    def test_category_filter_no_match_returns_empty(self):
        """TC-UNIT-PL-10 | EC — invalid class: categoryId not in DB
        A categoryId with no products must return empty list."""
        result = apply_category_filter(PRODUCTS, 999)
        assert result == []


class TestPriceFilter:

    # TC-UNIT-PL-11 | EC — valid class: minPrice | Unit
    def test_min_price_excludes_cheaper_products(self):
        """TC-UNIT-PL-11 | EC — valid class: minPrice = 200
        Products cheaper than 200 must be excluded."""
        result = apply_price_range(PRODUCTS, min_price=200)
        for p in result:
            assert p["price"] >= 200

    # TC-UNIT-PL-12 | EC — valid class: maxPrice | Unit
    def test_max_price_excludes_more_expensive_products(self):
        """TC-UNIT-PL-12 | EC — valid class: maxPrice = 100
        Products more expensive than 100 must be excluded."""
        result = apply_price_range(PRODUCTS, max_price=100)
        for p in result:
            assert p["price"] <= 100

    # TC-UNIT-PL-13 | EC — valid class: price range | Unit
    def test_price_range_filters_both_ends(self):
        """TC-UNIT-PL-13 | EC — valid class: minPrice=50, maxPrice=300
        Only products in range [50, 300] must appear."""
        result = apply_price_range(PRODUCTS, min_price=50, max_price=300)
        for p in result:
            assert 50 <= p["price"] <= 300

    # TC-UNIT-PL-14 | BVA — boundary: exact price match | Unit
    def test_min_price_inclusive_boundary(self):
        """TC-UNIT-PL-14 | BVA — boundary: price exactly equals minPrice
        A product with price == minPrice must be INCLUDED (>=, not >)."""
        result = apply_price_range(PRODUCTS, min_price=249.99)
        ids = [p["id"] for p in result]
        assert 102 in ids  # price is exactly 249.99


class TestSorting:

    # TC-UNIT-PL-15 | EC — valid class: price-asc | Unit
    def test_sort_price_asc(self):
        """TC-UNIT-PL-15 | EC — valid class: sortBy='price-asc'
        Products must be in ascending price order."""
        result = apply_sort(PRODUCTS, "price-asc")
        prices = [p["price"] for p in result]
        assert prices == sorted(prices)

    # TC-UNIT-PL-16 | EC — valid class: price-desc | Unit
    def test_sort_price_desc(self):
        """TC-UNIT-PL-16 | EC — valid class: sortBy='price-desc'
        Products must be in descending price order."""
        result = apply_sort(PRODUCTS, "price-desc")
        prices = [p["price"] for p in result]
        assert prices == sorted(prices, reverse=True)

    # TC-UNIT-PL-17 | EC — valid class: alpha-asc | Unit
    def test_sort_alpha_asc(self):
        """TC-UNIT-PL-17 | EC — valid class: sortBy='alpha-asc'
        Products must be sorted alphabetically by name A→Z."""
        result = apply_sort(PRODUCTS, "alpha-asc")
        names = [p["name"] for p in result]
        assert names == sorted(names)

    # TC-UNIT-PL-18 | EC — invalid/default class: unknown sort | Unit
    def test_sort_unknown_defaults_to_id(self):
        """TC-UNIT-PL-18 | EC — default branch: unrecognised sortBy
        Unknown sort value must fall back to ordering by id."""
        result = apply_sort(PRODUCTS, "unknown")
        ids = [p["id"] for p in result]
        assert ids == sorted(ids)


class TestPagination:

    # TC-UNIT-PL-19 | EC — valid class: first page | Unit
    def test_pagination_page_1(self):
        """TC-UNIT-PL-19 | EC — valid class: page=1, pageSize=2
        First page must return the first 2 items."""
        result = apply_pagination(PRODUCTS, page=1, page_size=2)
        assert len(result) == 2
        assert result[0]["id"] == PRODUCTS[0]["id"]

    # TC-UNIT-PL-20 | EC — valid class: second page | Unit
    def test_pagination_page_2(self):
        """TC-UNIT-PL-20 | EC — valid class: page=2, pageSize=2
        Second page must return items 3 and 4."""
        result = apply_pagination(PRODUCTS, page=2, page_size=2)
        assert len(result) == 2
        assert result[0]["id"] == PRODUCTS[2]["id"]

    # TC-UNIT-PL-21 | BVA — boundary: page beyond data | Unit
    def test_pagination_beyond_data_returns_empty(self):
        """TC-UNIT-PL-21 | BVA — boundary: page that exceeds total records
        Page beyond available data must return empty list."""
        result = apply_pagination(PRODUCTS, page=999, page_size=10)
        assert result == []
