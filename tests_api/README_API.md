# ShopVerse — Real API Tests (pytest + requests)

## What these tests do

Send **real HTTP requests** to the running .NET backend. No mocking, no simulation.
Every assertion exercises the actual database, business logic and JWT middleware.

## Tools used

| Tool | Role | Guideline §5.1 |
|---|---|---|
| **pytest** | Test runner + fixtures | ✅ Listed |
| **requests** | HTTP client (real HTTP calls) | ✅ Equivalent to Postman |

## Levels covered

| File | Level | What it tests |
|---|---|---|
| `test_api_auth.py` | Integration | AuthController — login, register, token |
| `test_api_products.py` | Integration | ProductsController — CRUD, filters, auth |
| `test_api_orders.py` | Integration | OrdersController — create, status, access |
| `test_api_users.py` | Integration | UsersController — admin CRUD, suspend, role |
| `test_api_categories.py` | Integration | CategoriesController — CRUD, auth |
| `test_system_flows.py` | System | Full cross-controller user journeys |

## Prerequisites

1. **Start the backend:**
   ```bash
   cd ShopVerseAPI
   dotnet run
   # API listens on http://localhost:5000
   ```

2. **Install Python dependency** (requests is the only addition):
   ```bash
   pip install pytest requests
   # or:
   pip install -r requirements_api.txt
   ```

## Run the tests

```bash
# All API + system tests
pytest tests_api/ -v

# One file at a time
pytest tests_api/test_api_auth.py -v
pytest tests_api/test_api_orders.py -v
pytest tests_api/test_system_flows.py -v

# With the dedicated ini file
pytest -c pytest_api.ini
```

## Test count summary

| Suite | Tests |
|---|---|
| test_api_auth.py | 13 |
| test_api_products.py | 16 |
| test_api_orders.py | 17 |
| test_api_users.py | 12 |
| test_api_categories.py | 9 |
| test_system_flows.py | 11 |
| **Total** | **78** |
