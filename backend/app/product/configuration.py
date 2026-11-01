"""Instance-local provider configuration; no traveler database or provider calls."""

import hashlib
import json
import os
import secrets
import tempfile
import threading
from collections import deque
from contextlib import contextmanager
from functools import lru_cache
from io import StringIO
from pathlib import Path
from time import monotonic

import yaml
from dotenv.parser import parse_stream
from dotenv.variables import parse_variables
from pwdlib import PasswordHash

from backend.app.product.configuration_files import (
    FOUNDRY_FIELDS,
    replace_configuration_files,
    retire_foundry_bindings,
    update_foundry,
)
from backend.app.product.configuration_validation import supported_foundry_endpoint
from backend.app.runtime.deployment import DeploymentOptions, DeploymentYamlLoader

FIELDS = {
    "AZURE_OPENAI_ENDPOINT": False,
    "AZURE_OPENAI_DEPLOYMENT": False,
    "AZURE_OPENAI_API_KEY": True,
    "OPENAI_API_KEY": True,
    "GOOGLE_MAPS_API_KEY": True,
    "PRODUCT_UNSPLASH_ACCESS_KEY": True,
    "DAYLOOM_DB_HOST": False,
    "DAYLOOM_DB_PORT": False,
    "DAYLOOM_DB_NAME": False,
    "DAYLOOM_DB_USER": False,
    "DAYLOOM_DB_PASSWORD": True,
    "DAYLOOM_DB_URL": True,
    "PRODUCT_JWT_SECRET": True,
}
COOKIE = "dayloom_config_session"
SESSION_SECONDS = 1800
password_hasher = PasswordHash.recommended()
DEFAULT_TEST_PASSWORD = "dayloom-config-2026"


@lru_cache(maxsize=1)
def default_password_hash():
    return password_hasher.hash(DEFAULT_TEST_PASSWORD)


@contextmanager
def configuration_file_lock(path):
    """Serialize writers across local application processes on Windows and Unix."""
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


class ConfigurationError(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def _revision(text, values):
    """Cover both saved files and effective values in one opaque version."""
    return hashlib.sha256(json.dumps([text, values], sort_keys=True).encode()).hexdigest()


class LocalConfiguration:
    def __init__(self, root: Path, *, origin: str, environment: dict):
        from backend.app.product.api_checks import ApiChecker

        self.root, self.origin = root, origin.rstrip("/")
        self.environment = dict(environment)
        self._environment_settings = {key.upper(): value for key, value in environment.items()}
        self.sessions = {}
        self.attempts = deque(maxlen=10)
        self.lock = threading.Lock()
        self.migrate_foundry_overrides()
        self.initial = self.snapshot()[1]
        self.running_ready = True
        self.resource_probe = None
        self.api_checker = ApiChecker()

    def read(self):
        path = self.root / ".env"
        if path.is_symlink():
            raise ConfigurationError("configuration_symlink_rejected")
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        bindings = list(parse_stream(StringIO(text)))
        if len(text) > 1_048_576 or any(item.error for item in bindings):
            raise ConfigurationError("invalid_dotenv")
        resolved = {}
        for item in bindings:
            if item.key is None:
                continue
            # Match load_dotenv(override=False), without mutating global process
            # state while a configuration request is being served.
            environment = {**resolved, **self.environment}
            resolved[item.key] = (
                "".join(atom.resolve(environment) for atom in parse_variables(item.value))
                if item.value is not None
                else None
            )
        return text, resolved

    def read_deployment(self):
        path = self.root / "product.yaml"
        if not path.exists() and not path.is_symlink():
            path = self.root / "product.example.yaml"
        if path.is_symlink():
            raise ConfigurationError("configuration_symlink_rejected")
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        data = yaml.load(text, Loader=DeploymentYamlLoader)
        options = DeploymentOptions.model_validate({} if data is None else data)
        return text, options

    def migrate_foundry_overrides(self):
        """Preserve the last saved deployment before retiring dotenv overrides."""
        text, _ = self.read()
        if not any(item.key and item.key.upper() in FOUNDRY_FIELDS
                   for item in parse_stream(StringIO(text))):
            return
        with self.lock, configuration_file_lock(self.root / ".env.config.lock"):
            text, values = self.read()
            changes = {key.upper(): value for key, value in values.items()
                       if key.upper() in FOUNDRY_FIELDS and value is not None}
            deployment_text, _ = self.read_deployment()
            updated = update_foundry(deployment_text, changes)
            DeploymentOptions.model_validate(yaml.load(updated, Loader=DeploymentYamlLoader) or {})
            files = {}
            if updated != deployment_text:
                files[self.root / "product.yaml"] = updated
            retained = retire_foundry_bindings(text, self.environment)
            if retained != text:
                files[self.root / ".env"] = retained
            replace_configuration_files(files)

    def snapshot(self):
        text, local = self.read()
        # Settings names are case-insensitive; dotenv variable expansion above is not.
        local = {key.upper(): value for key, value in local.items()}
        deployment_text, options = self.read_deployment()
        defaults = {
            "DAYLOOM_DB_HOST": "127.0.0.1", "DAYLOOM_DB_PORT": "55432",
            "DAYLOOM_DB_NAME": "dayloom", "DAYLOOM_DB_USER": "dayloom",
        }
        if options.database:
            defaults.update({"DAYLOOM_DB_" + key.upper(): str(value)
                             for key, value in options.database.model_dump().items()})
        if options.foundry:
            defaults.update({
                "AZURE_OPENAI_ENDPOINT": str(options.foundry.endpoint or ""),
                "AZURE_OPENAI_DEPLOYMENT": options.foundry.deployment or "",
            })
        values = {
            key: next(
                (
                    source[key]
                    for source in (self._environment_settings,
                                   {} if key in FOUNDRY_FIELDS else local, defaults)
                    if source.get(key) is not None
                ),
                "",
            )
            for key in FIELDS
        }
        for source in (self._environment_settings, local):
            for key in ("PRODUCT_UNSPLASH_ACCESS_KEY", "UNSPLASH_API_KEY"):
                if source.get(key) is not None:
                    values["PRODUCT_UNSPLASH_ACCESS_KEY"] = source[key] or ""
                    return [text, deployment_text], values
        return [text, deployment_text], values

    def view(self):
        text, values = self.snapshot()
        return {
            "revision": _revision(text, values),
            "restart_required": values != self.initial,
            "running_ready": self.running_ready,
            "fields": {
                key: {
                    "secret": secret,
                    "configured": bool(values[key]),
                    "value": None if secret else values[key],
                    "locked": self._environment_settings.get(key) is not None
                    or (
                        key == "PRODUCT_UNSPLASH_ACCESS_KEY"
                        and self._environment_settings.get("UNSPLASH_API_KEY") is not None
                    ),
                }
                for key, secret in FIELDS.items()
            },
        }

    def values_for_check(self, revision):
        text, values = self.snapshot()
        if revision != _revision(text, values):
            raise ConfigurationError("configuration_changed", 409)
        return values

    def validate(self, changes):
        for key, value in changes.items():
            if key not in FIELDS:
                raise ConfigurationError("unsupported_setting")
            if self._environment_settings.get(key) is not None or (
                key == "PRODUCT_UNSPLASH_ACCESS_KEY"
                and self._environment_settings.get("UNSPLASH_API_KEY") is not None
            ):
                raise ConfigurationError("setting_managed_by_environment", 409)
            if (
                len(value) > 4096
                or "${" in value
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                raise ConfigurationError("invalid_setting_value")
            if key == "PRODUCT_JWT_SECRET" and len(value) < 32:
                raise ConfigurationError("invalid_signing_key")
            if (
                key in {"DAYLOOM_DB_HOST", "DAYLOOM_DB_NAME", "DAYLOOM_DB_USER"}
                and not value.strip()
            ):
                raise ConfigurationError("invalid_database_setting")
            if key == "DAYLOOM_DB_PORT" and (
                not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 65535
            ):
                raise ConfigurationError("invalid_database_setting")
            if key == "DAYLOOM_DB_URL" and value:
                from psycopg.conninfo import conninfo_to_dict
                try:
                    parameters = conninfo_to_dict(value)
                    if not parameters.get("dbname"):
                        raise ValueError
                except Exception:
                    raise ConfigurationError("invalid_database_setting") from None
            if key == "AZURE_OPENAI_ENDPOINT" and value:
                if not supported_foundry_endpoint(value):
                    raise ConfigurationError("invalid_foundry_endpoint")
            if (
                key == "AZURE_OPENAI_DEPLOYMENT"
                and value
                and (
                    len(value) > 128
                    or any(not (c.isascii() and (c.isalnum() or c in "-_.")) for c in value)
                )
            ):
                raise ConfigurationError("invalid_foundry_deployment")

    def save(self, revision, changes):
        with self.lock, configuration_file_lock(self.root / ".env.config.lock"):
            return self._save_locked(revision, changes)

    def _save_locked(self, revision, changes):
        self.validate(changes)
        texts, values = self.snapshot()
        if revision != _revision(texts, values):
            raise ConfigurationError("configuration_changed", 409)
        text, deployment_text = texts
        replacements = {
            key: value for key, value in changes.items() if key not in FOUNDRY_FIELDS
        }
        if "PRODUCT_UNSPLASH_ACCESS_KEY" in changes:
            replacements["UNSPLASH_API_KEY"] = changes["PRODUCT_UNSPLASH_ACCESS_KEY"]
        pieces, seen = [], set()
        for item in parse_stream(StringIO(retire_foundry_bindings(text, self.environment))):
            key = item.key.upper() if item.key is not None else None
            if key in FOUNDRY_FIELDS:
                continue
            if key not in replacements:
                pieces.append(item.original.string)
                continue
            value = replacements[key].replace("\\", "\\\\").replace("'", "\\'")
            # Keep spelling and order so dependent ${...} bindings still resolve.
            pieces.append(f"{item.key}='{value}'\n")
            seen.add(key)
        retained = "".join(pieces)
        for key, value in replacements.items():
            if key in seen:
                continue
            if retained and not retained.endswith("\n"):
                retained += "\n"
            quoted = value.replace("\\", "\\\\").replace("'", "\\'")
            retained += f"{key}='{quoted}'\n"
        updated_yaml = update_foundry(deployment_text, changes)
        DeploymentOptions.model_validate(
            yaml.load(updated_yaml, Loader=DeploymentYamlLoader) or {}
        )
        files = {}
        if updated_yaml != deployment_text:
            files[self.root / "product.yaml"] = updated_yaml
        if retained != text:
            files[self.root / ".env"] = retained
        replace_configuration_files(files)
        return self.view()

    def generate_signing_key(self, revision):
        return self.save(revision, {"PRODUCT_JWT_SECRET": secrets.token_urlsafe(48)})

    def ensure_signing_key(self):
        """Initialize once at local startup; retain all existing effective keys."""
        with self.lock, configuration_file_lock(self.root / ".env.config.lock"):
            texts, values = self.snapshot()
            if not values["PRODUCT_JWT_SECRET"]:
                self._save_locked(_revision(texts, values), {
                    "PRODUCT_JWT_SECRET": secrets.token_urlsafe(48),
                })
            self.initial = self.snapshot()[1]

    def readiness(self):
        from backend.app.product.local_readiness import check_local_resources

        view = self.view()
        required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT",
                    "AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY",
                    "PRODUCT_JWT_SECRET"]
        if not view["fields"]["DAYLOOM_DB_URL"]["configured"]:
            required.append("DAYLOOM_DB_PASSWORD")
        resources = (self.resource_probe or check_local_resources)()
        missing = [key for key in required if not view["fields"][key]["configured"]]
        return {
            "ready": not missing and all(item["ready"] for item in resources),
            "missing": missing,
            "resources": resources,
            "credentials_verified": False,
            "restart_required": view["restart_required"],
            "running_ready": self.running_ready,
        }

    def _password_state(self):
        path = self.root / ".config-access.json"
        try:
            if path.is_symlink():
                raise ValueError("Configuration access file must not be a symlink")
            try:
                with path.open("rb") as stream:
                    content = stream.read(8193)
            except FileNotFoundError:
                return {"schema_version": 1, "revision": "0" * 64,
                        "password_hash": default_password_hash()}
            state = json.loads(content)
            if (
                len(content) > 8192
                or not isinstance(state, dict)
                or set(state) != {"schema_version", "revision", "password_hash"}
                or state["schema_version"] != 1
                or not isinstance(state["revision"], str)
                or len(state["revision"]) != 64
                or any(c not in "0123456789abcdef" for c in state["revision"])
                or (state["password_hash"] is not None and (
                    not isinstance(state["password_hash"], str)
                    or not state["password_hash"].startswith("$argon2id$")
                    or len(state["password_hash"]) > 512
                ))
            ):
                raise ValueError("Invalid configuration access file")
            return state
        except Exception:
            raise ConfigurationError("configuration_access_unreadable", 503) from None

    def access_view(self):
        state = self._password_state()
        return {"password_required": state["password_hash"] is not None,
                "revision": state["revision"], "default_test_password": DEFAULT_TEST_PASSWORD}

    def verify_access_password(self, password):
        with self.lock:
            self._check_password(self._password_state(), password)

    def _check_password(self, state, password):
        if state["password_hash"] is None:
            return
        now = monotonic()
        if len(self.attempts) == 10 and now - self.attempts[0] < 60:
            raise ConfigurationError("too_many_attempts", 429)
        try:
            valid = password_hasher.verify(password, state["password_hash"])
        except Exception:
            raise ConfigurationError("configuration_access_unreadable", 503) from None
        if not valid:
            self.attempts.append(now)
            raise ConfigurationError("invalid_configuration_password", 401)
        self.attempts.clear()

    def set_access(self, revision, *, enabled, current_password, new_password, confirmation):
        with self.lock, configuration_file_lock(self.root / ".env.config.lock"):
            state = self._password_state()
            if state["revision"] != revision:
                raise ConfigurationError("configuration_changed", 409)
            self._check_password(state, current_password)
            if enabled:
                if not 10 <= len(new_password) <= 128:
                    raise ConfigurationError("configuration_password_required")
                if not secrets.compare_digest(new_password.encode(), confirmation.encode()):
                    raise ConfigurationError("password_confirmation_mismatch")
            saved = {"schema_version": 1, "revision": secrets.token_hex(32),
                     "password_hash": password_hasher.hash(new_password) if enabled else None}
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="\n", dir=self.root,
                    prefix=".config-access.", delete=False,
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(json.dumps(saved) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.root / ".config-access.json")
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            self.sessions.clear()
            self.attempts.clear()
            return self.access_view()

    def unlock(self, password="", *, previous_session=None):
        now = monotonic()
        with self.lock:
            state = self._password_state()
            self._check_password(state, password)
            self.sessions.pop(previous_session or "", None)
            self.sessions = {key: value for key, value in self.sessions.items() if value[0] > now}
            if len(self.sessions) >= 8:
                raise ConfigurationError("too_many_sessions", 429)
            session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self.sessions[session] = (now + SESSION_SECONDS, csrf, state["revision"])
            return session, csrf

    def authorize(self, session, csrf=None, *, write=False):
        with self.lock:
            value = self.sessions.get(session or "")
            state = self._password_state()
            if (value is None or value[0] <= monotonic()
                    or value[2] != state["revision"]):
                raise ConfigurationError("configuration_locked", 401)
            if (write or state["password_hash"] is not None) and not secrets.compare_digest(
                (csrf or "").encode(), value[1].encode(),
            ):
                raise ConfigurationError(
                    "csrf_rejected" if write else "configuration_locked", 403 if write else 401,
                )
            return value[1]
