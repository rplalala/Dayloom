"""Synthetic service settings shared by offline configuration probe tests."""

import pytest


@pytest.fixture
def provider_values():
    return {
        "AZURE_OPENAI_ENDPOINT": "https://example.services.ai.azure.com/openai/v1",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-6-luna",
        "AZURE_OPENAI_API_KEY": "synthetic-foundry",
        "OPENAI_API_KEY": "synthetic-openai",
        "GOOGLE_MAPS_API_KEY": "synthetic-google",
        "PRODUCT_UNSPLASH_ACCESS_KEY": "synthetic-unsplash",
    }
