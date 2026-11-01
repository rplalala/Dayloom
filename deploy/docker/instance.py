"""Create instance-owned configuration without contacting external services."""

import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from backend.app.product.configuration import (
    DEFAULT_TEST_PASSWORD,
    LocalConfiguration,
    configuration_file_lock,
    password_hasher,
)
from backend.app.product.configuration_files import replace_configuration_files


def local_origin(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("Container configuration requires a loopback HTTP origin")
    return value.rstrip("/")


def create_private_file(path, content):
    if path.is_symlink():
        raise ValueError("Instance configuration must not contain symbolic-link files")
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            os.chmod(path, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        return False
    return True


def bootstrap_instance(directory, origin, *, database_host="postgres", database_port=5432,
                       database_name="dayloom", database_user="dayloom"):
    origin = local_origin(origin)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    for name in (".env", "product.yaml", ".config-access.json", ".bootstrap.lock"):
        if (directory / name).is_symlink():
            raise ValueError("Instance configuration must not contain symbolic-link files")
    with configuration_file_lock(directory / ".bootstrap.lock"):
        values = {
            "DAYLOOM_DB_HOST": database_host, "DAYLOOM_DB_PORT": str(database_port),
            "DAYLOOM_DB_NAME": database_name, "DAYLOOM_DB_USER": database_user,
            "DAYLOOM_DB_PASSWORD": secrets.token_urlsafe(48),
            "PRODUCT_JWT_SECRET": secrets.token_urlsafe(48),
            "AZURE_OPENAI_API_KEY": "", "OPENAI_API_KEY": "",
            "GOOGLE_MAPS_API_KEY": "", "UNSPLASH_API_KEY": "",
        }
        created = create_private_file(directory / ".env", "".join(
            f"{key}={json.dumps(value)}\n" for key, value in values.items()
        ))
        create_private_file(directory / "product.yaml", yaml.safe_dump({
            "origin": origin, "runtime_profile": "acceptance", "allow_insecure_loopback": True,
            "database": {"host": database_host, "port": database_port,
                         "name": database_name, "user": database_user},
            "foundry": {"endpoint": None, "deployment": "gpt-6-luna"},
        }, sort_keys=False))
        manager = LocalConfiguration(directory, origin=origin, environment={})
        manager.ensure_signing_key()
        result = {"created": created, "configuration_url": origin + "/config"}
        if not (directory / ".config-access.json").exists():
            password = secrets.token_urlsafe(32)
            manager.set_access(manager.access_view()["revision"], enabled=True,
                               current_password=DEFAULT_TEST_PASSWORD,
                               new_password=password, confirmation=password)
            result["management_password"] = password
        for name in (".env", "product.yaml", ".config-access.json", ".bootstrap.lock",
                     ".env.config.lock"):
            path = directory / name
            if path.exists():
                os.chmod(path, 0o600)
        return result


def reset_management_password(directory):
    directory = Path(directory)
    if not (directory / ".env").is_file():
        raise ValueError("Bootstrap the instance before resetting management access")
    path = directory / ".config-access.json"
    if path.is_symlink():
        raise ValueError("Management access must not be a symbolic-link file")
    with configuration_file_lock(directory / ".bootstrap.lock"):
        password = secrets.token_urlsafe(32)
        state = {"schema_version": 1, "revision": secrets.token_hex(32),
                 "password_hash": password_hasher.hash(password)}
        replace_configuration_files({path: json.dumps(state) + "\n"})
        os.chmod(path, 0o600)
        return {"management_password": password}
