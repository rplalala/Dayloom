"""Instance-local provider configuration; no traveler database or provider calls."""

import hashlib
import os
import secrets
import tempfile
import threading
from collections import deque
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

import yaml
from dotenv.parser import parse_stream
from dotenv.variables import parse_variables

from backend.app.runtime.deployment import DeploymentOptions, DeploymentYamlLoader

FIELDS = {
    "AZURE_OPENAI_ENDPOINT": False,
    "AZURE_OPENAI_DEPLOYMENT": False,
    "AZURE_OPENAI_API_KEY": True,
    "OPENAI_API_KEY": True,
    "GOOGLE_MAPS_API_KEY": True,
    "PRODUCT_UNSPLASH_ACCESS_KEY": True,
}
COOKIE = "dayloom_config_session"
SESSION_SECONDS = 1800


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


class LocalConfiguration:
    def __init__(self, root: Path, *, origin: str, environment: dict):
        self.root, self.origin = root, origin.rstrip("/")
        self.environment = dict(environment)
        self.token = secrets.token_urlsafe(32)
        self.sessions = {}
        self.attempts = deque(maxlen=10)
        self.lock = threading.Lock()
        self.initial = self.snapshot()[1]
        self.running_ready = True
        self.resource_probe = None

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

    def snapshot(self):
        text, local = self.read()
        path = self.root / "product.yaml"
        data = (
            yaml.load(path.read_text(encoding="utf-8"), Loader=DeploymentYamlLoader)
            if path.exists()
            else {}
        )
        options = DeploymentOptions.model_validate({} if data is None else data)
        defaults = {}
        if options.foundry:
            defaults = {
                "AZURE_OPENAI_ENDPOINT": str(options.foundry.endpoint),
                "AZURE_OPENAI_DEPLOYMENT": options.foundry.deployment,
            }
        values = {
            key: next(
                (
                    source[key]
                    for source in (self.environment, local, defaults)
                    if source.get(key) is not None
                ),
                "",
            )
            for key in FIELDS
        }
        for source in (self.environment, local):
            for key in ("PRODUCT_UNSPLASH_ACCESS_KEY", "UNSPLASH_API_KEY"):
                if source.get(key) is not None:
                    values["PRODUCT_UNSPLASH_ACCESS_KEY"] = source[key] or ""
                    return text, values
        return text, values

    def view(self):
        text, values = self.snapshot()
        return {
            "revision": hashlib.sha256(text.encode()).hexdigest(),
            "restart_required": values != self.initial,
            "running_ready": self.running_ready,
            "fields": {
                key: {
                    "secret": secret,
                    "configured": bool(values[key]),
                    "value": None if secret else values[key],
                    "locked": self.environment.get(key) is not None
                    or (
                        key == "PRODUCT_UNSPLASH_ACCESS_KEY"
                        and self.environment.get("UNSPLASH_API_KEY") is not None
                    ),
                }
                for key, secret in FIELDS.items()
            },
        }

    def validate(self, changes):
        fields = self.view()["fields"]
        for key, value in changes.items():
            if key not in FIELDS:
                raise ConfigurationError("unsupported_setting")
            if fields[key]["locked"]:
                raise ConfigurationError("setting_managed_by_environment", 409)
            if (
                len(value) > 4096
                or "${" in value
                or any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                raise ConfigurationError("invalid_setting_value")
            if key == "AZURE_OPENAI_ENDPOINT" and value:
                try:
                    url = urlsplit(value)
                    valid = (
                        url.scheme == "https"
                        and url.hostname
                        and url.hostname.endswith(
                            (
                                ".openai.azure.com",
                                ".services.ai.azure.com",
                                ".cognitiveservices.azure.com",
                            )
                        )
                        and url.port in (None, 443)
                        and not url.username
                        and not url.password
                        and not url.query
                        and not url.fragment
                        and url.path.rstrip("/") == "/openai/v1"
                    )
                except ValueError:
                    valid = False
                if not valid:
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
            self.validate(changes)
            if revision != self.view()["revision"]:
                raise ConfigurationError("configuration_changed", 409)
            text, _ = self.read()
            replacements = dict(changes)
            if "PRODUCT_UNSPLASH_ACCESS_KEY" in changes:
                replacements["UNSPLASH_API_KEY"] = changes["PRODUCT_UNSPLASH_ACCESS_KEY"]
            pieces = [
                item.original.string
                for item in parse_stream(StringIO(text))
                if item.key not in replacements
            ]
            retained = "".join(pieces)
            if retained and not retained.endswith("\n"):
                retained += "\n"
            for key, value in replacements.items():
                quoted = value.replace("\\", "\\\\").replace("'", "\\'")
                retained += f"{key}='{quoted}'\n"
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    newline="\n",
                    dir=self.root,
                    prefix=".env.",
                    delete=False,
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(retained)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.root / ".env")
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            return self.view()

    def readiness(self):
        from backend.app.product.local_readiness import check_local_resources

        view = self.view()
        required = [key for key in FIELDS if key != "PRODUCT_UNSPLASH_ACCESS_KEY"]
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

    def unlock(self, token):
        now = monotonic()
        with self.lock:
            if len(self.attempts) == 10 and now - self.attempts[0] < 60:
                raise ConfigurationError("too_many_attempts", 429)
            if not secrets.compare_digest(token.encode(), self.token.encode()):
                self.attempts.append(now)
                raise ConfigurationError("invalid_management_token", 401)
            self.sessions = {key: value for key, value in self.sessions.items() if value[0] > now}
            if len(self.sessions) >= 8:
                raise ConfigurationError("too_many_sessions", 429)
            session, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self.sessions[session] = (now + SESSION_SECONDS, csrf)
            return session, csrf

    def authorize(self, session, csrf=None, *, write=False):
        with self.lock:
            value = self.sessions.get(session or "")
            if value is None or value[0] <= monotonic():
                raise ConfigurationError("configuration_locked", 401)
            if write and not secrets.compare_digest((csrf or "").encode(), value[1].encode()):
                raise ConfigurationError("csrf_rejected", 403)
            return value[1]
