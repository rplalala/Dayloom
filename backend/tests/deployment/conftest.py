"""Deployment tools run in the minimal PostgreSQL utility environment."""

import pytest


@pytest.fixture(autouse=True)
def offline_semantic_tokenizer():
    """These provider-free tools do not import the planner or its tokenizer."""
