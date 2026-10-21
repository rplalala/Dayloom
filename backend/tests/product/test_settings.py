"""Configuration diagnostics never include unrecognized dotenv credential input."""

import pytest
from pydantic import ValidationError

from backend.app.product.settings import ProductSettings


def test_missing_product_settings_hide_unrecognized_dotenv_secrets(monkeypatch, tmp_path):
    monkeypatch.delenv("PRODUCT_DATABASE_URL", raising=False)
    monkeypatch.delenv("PRODUCT_JWT_SECRET", raising=False)
    dotenv = tmp_path / "controlled.env"
    sentinel = "private42"
    dotenv.write_text(f"UNRECOGNIZED_PROVIDER_SECRET={sentinel}\n", encoding="utf-8")
    with pytest.raises(ValidationError) as failure:
        ProductSettings(_env_file=dotenv)
    assert "database_url" in str(failure.value) and "jwt_secret" in str(failure.value)
    assert sentinel not in str(failure.value)
    assert sentinel not in repr(failure.value)
    assert "input_value" not in str(failure.value)
    assert "input_value" not in repr(failure.value)
