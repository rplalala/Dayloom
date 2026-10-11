"""Output-location-aware Markdown provenance shared by offline research tracks."""

import os
import re
from pathlib import Path
from urllib.parse import quote

from backend.cli.collection import _require


def label(value):
    return re.sub(r"([\\`*_{}\[\]()#+.!|<>])", r"\\\1", value)


def render_markdown(report, render, *, source_root, output_path):
    """Render immutable JSON semantics and links relative to the actual Markdown file."""
    root, output = Path(source_root).resolve(), Path(output_path).resolve()
    lines = [
        render(report).rstrip(),
        "",
        "## Sources",
        "",
        "Links resolve from this report; exact byte SHA-256 binds each source.",
        "",
    ]
    for source in report["source_bindings"]:
        target = (root / source["path"]).resolve()
        _require(target.is_relative_to(root), "Research provenance source escapes declared root")
        try:
            destination = quote(Path(os.path.relpath(target, output.parent)).as_posix(), safe="/.:")
        except ValueError:
            # Windows volumes cannot express a relative filesystem path between drives.
            destination = quote(target.as_posix(), safe="/.:")
        lines.append(f"- [{label(source['path'])}]({destination}): `{source['sha256']}`")
    lines.append("")
    return "\n".join(lines)
