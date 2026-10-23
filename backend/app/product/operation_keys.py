"""Storeable operation identities, transported as query values for recovery."""

import unicodedata
from typing import Annotated

from pydantic import AfterValidator, Field


def storeable_key(value: str) -> str:
    if not value.strip() or any(
        unicodedata.category(character).startswith("C") for character in value
    ):
        raise ValueError("Operation keys must be nonblank text without control characters")
    return value


OperationKey = Annotated[str, Field(min_length=1, max_length=120), AfterValidator(storeable_key)]
# Task submission retains its existing public character domain.
TaskOperationKey = Annotated[OperationKey, Field(pattern=r"^[A-Za-z0-9_.:-]+$")]
