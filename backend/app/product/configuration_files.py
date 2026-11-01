"""Preserve deployment text and replace locally owned configuration files."""

import json
import os
import tempfile
from io import StringIO
from pathlib import Path

import yaml
from dotenv.parser import parse_stream
from dotenv.variables import Variable, parse_variables

FOUNDRY_FIELDS = {
    "AZURE_OPENAI_ENDPOINT": "endpoint",
    "AZURE_OPENAI_DEPLOYMENT": "deployment",
}


def retire_foundry_bindings(text, environment):
    """Remove legacy keys, preserving dependents' existing interpolated values."""
    resolved, pieces = {}, []
    for item in parse_stream(StringIO(text)):
        atoms = list(parse_variables(item.value)) if item.value is not None else []
        variables = {**resolved, **environment}
        value = "".join(atom.resolve(variables) for atom in atoms)
        if item.key is not None:
            resolved[item.key] = value if item.value is not None else None
        if item.key and item.key.upper() in FOUNDRY_FIELDS:
            continue
        if any(isinstance(atom, Variable) and atom.name.upper() in FOUNDRY_FIELDS
               for atom in atoms):
            quoted = value.replace("\\", "\\\\").replace("'", "\\'")
            pieces.append(f"{item.key}='{quoted}'\n")
        else:
            pieces.append(item.original.string)
    return "".join(pieces)


def update_foundry(text, changes):
    """Edit scalar spans so unrelated YAML settings and comments remain intact."""
    updates = {FOUNDRY_FIELDS[key]: value or None for key, value in changes.items()
               if key in FOUNDRY_FIELDS}
    if not updates:
        return text
    root = yaml.compose(text)
    if root is None:
        return text + ("\n" if text and not text.endswith("\n") else "") + yaml.safe_dump(
            {"foundry": updates}, sort_keys=False,
        )
    foundry = next((value for key, value in root.value if key.value == "foundry"), None)
    if foundry is None and not root.flow_style:
        return text + ("\n" if not text.endswith("\n") else "") + yaml.safe_dump(
            {"foundry": updates}, sort_keys=False,
        )
    if root.flow_style or any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken))
                              for token in yaml.scan(text)):
        data = yaml.safe_load(text)
        data["foundry"] = {**(data.get("foundry") or {}), **updates}
        return yaml.safe_dump(data, sort_keys=False)
    if not isinstance(foundry, yaml.MappingNode) or foundry.flow_style:
        values = {} if not isinstance(foundry, yaml.MappingNode) else yaml.safe_load(
            text[foundry.start_mark.index:foundry.end_mark.index]
        )
        rendered = yaml.safe_dump({**values, **updates}, default_flow_style=True,
                                  sort_keys=False, width=10000).strip()
        if foundry.start_mark.index and text[foundry.start_mark.index - 1] == ":":
            rendered = " " + rendered
        return text[:foundry.start_mark.index] + rendered + text[foundry.end_mark.index:]
    spans = []
    for key, value in foundry.value:
        if key.value in updates:
            replacement = updates.pop(key.value)
            rendered = "null" if replacement is None else json.dumps(replacement)
            if value.style in {"|", ">"}:
                rendered += "\n"
            elif value.start_mark.index and text[value.start_mark.index - 1] == ":":
                rendered = " " + rendered
            spans.append((value.start_mark.index, value.end_mark.index, rendered))
    if updates:
        last = max(value.end_mark.index for _, value in foundry.value)
        end = text.find("\n", last)
        end = len(text) if end < 0 else end + 1
        addition = ("\n" if end and text[end - 1] != "\n" else "") + "".join(
            " " * foundry.start_mark.column + f"{key}: "
            + ("null" if value is None else json.dumps(value)) + "\n"
            for key, value in updates.items()
        )
        spans.append((end, end, addition))
    for start, end, value in sorted(spans, reverse=True):
        text = text[:start] + value + text[end:]
    return text


def replace_configuration_files(replacements):
    """Stage every file first; roll back completed replacements on an I/O failure.

    Each replacement is atomic; a process/host crash is not a two-file transaction.
    """
    staged, backups, replaced = {}, {}, []

    def stage(path, content):
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent,
            prefix=f".{path.name.lstrip('.')}.config-", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            staged_paths.append(temporary)
            stream.write(content.encode("utf-8") if isinstance(content, str) else content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            temporary.chmod(path.stat().st_mode)
        return temporary

    staged_paths = []
    try:
        for path, text in replacements.items():
            backups[path] = stage(path, path.read_bytes()) if path.exists() else None
            staged[path] = stage(path, text)
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except OSError:
        try:
            for path in reversed(replaced):
                if backups[path] is None:
                    path.unlink(missing_ok=True)
                else:
                    os.replace(backups[path], path)
        except OSError:
            # Retain ignored backups for host recovery when rollback is also blocked.
            staged_paths = [path for path in staged_paths if path not in backups.values()]
            raise
        raise
    finally:
        for temporary in staged_paths:
            temporary.unlink(missing_ok=True)
