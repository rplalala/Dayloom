"""Planner contract fixtures retain their separate authenticated caller seam.

Real credentials, cookies and PostgreSQL are exercised by Product account acceptance.
These pre-existing tests replace provider execution and focus on planner projection.
"""

import pytest

from backend.app.main import app
from backend.app.product.auth import current_user


@pytest.fixture(autouse=True)
def authenticated_planner_caller():
    app.dependency_overrides[current_user] = lambda: {"id": "planner-contract-caller"}
    yield
    app.dependency_overrides.pop(current_user, None)
