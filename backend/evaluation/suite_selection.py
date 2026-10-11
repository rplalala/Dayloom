"""Named accepted source material shared by the suite track adapters."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CaseSelection:
    """One declaration and accepted intake, with optional preparation inputs."""

    declaration: dict
    intake: dict
    files: dict[str, Path] | None = None
    values: dict | None = None
