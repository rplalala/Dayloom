"""Installed CLI acceptance at the process boundary, using offline synthetic material."""

import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytest_plugins = ("backend.tests.evaluation.test_intake",)
CLI_ENVIRONMENT_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "SYSTEMDRIVE",
    "LOCALAPPDATA",
    "APPDATA",
    "USERPROFILE",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PROGRAMDATA",
    "TEMP",
    "TMP",
    "TMPDIR",
)

GUARD = """import atexit
import importlib.abc
import json
import os
import socket
import sys
from pathlib import Path

events = Path(os.environ["RTPEVAL_TEST_EVENTS"])
block_intake = os.environ.get("RTPEVAL_TEST_BLOCK_INTAKE") == "1"
evaluation_offline = os.environ.get("RTPEVAL_TEST_EVALUATION_OFFLINE") == "1"
tools_offline = os.environ.get("RTPEVAL_TEST_TOOLS_OFFLINE") == "1"
events.write_text("", encoding="utf-8")

def deny(kind, detail):
    with events.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"kind": kind, "detail": str(detail)}) + "\\n")
    raise RuntimeError("OFFLINE_RTPEVAL_BLOCK: " + kind + ": " + str(detail))

def network(*args, **kwargs):
    deny("network", "DNS or socket operation")

for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "create_connection"):
    setattr(socket, name, network)
original_connect = socket.socket.connect
for name in ("connect", "connect_ex", "sendto"):
    setattr(socket.socket, name, network)

if tools_offline:
    def local_connect(self, address):
        if isinstance(address, tuple) and address[0] in ("127.0.0.1", "::1"):
            return original_connect(self, address)
        return network()
    socket.socket.connect = local_connect

forbidden = ("backend.app", "dotenv", "httpx", "openai", "pydantic_settings",
             "backend.evaluation.evaluation_run")
if evaluation_offline:
    forbidden = ("backend.app.versions", "backend.app.llm",
                 "backend.app.services", "openai", "backend.evaluation.opening_run")
if tools_offline:
    forbidden = ()
if block_intake:
    forbidden += ("backend.evaluation",)

class OfflineImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            deny("runtime_import", fullname)

sys.meta_path.insert(0, OfflineImports())

original_getitem = os._Environ.__getitem__
def environment_getitem(self, key):
    if str(key).upper().endswith(("API_KEY", "API_TOKEN", "PASSWORD")):
        deny("credential_read", key)
    return original_getitem(self, key)
os._Environ.__getitem__ = environment_getitem

def audit(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        if Path(os.fsdecode(args[0])).name.startswith(".env"):
            deny("credential_file", args[0])
sys.addaudithook(audit)

if evaluation_offline or tools_offline:
    import dotenv
    import httpx
    from backend.app.runtime import RuntimeSettings, token_counting

    def online_runtime(*args, **kwargs):
        deny("runtime_init", "HTTP client or runtime settings")
    if tools_offline:
        httpx.Client.__init__ = httpx.AsyncClient.__init__ = online_runtime
    else:
        httpx.Client = httpx.AsyncClient = online_runtime
    RuntimeSettings.__init__ = online_runtime
    dotenv.load_dotenv = dotenv.dotenv_values = online_runtime
    if tools_offline:
        import openai
        openai.OpenAI.__init__ = openai.AsyncOpenAI.__init__ = online_runtime

    class FixtureEncoding:
        def encode_ordinary(self, text):
            return range((len(text.encode("utf-8")) + 3) // 4)
    def fixture_tokenizer():
        if os.environ.get("RTPEVAL_TEST_MISSING_TOKENIZER") == "1":
            raise RuntimeError("Synthetic missing tokenizer vocabulary")
        return FixtureEncoding()
    token_counting.tokenizer = fixture_tokenizer

def finished():
    for name in sys.modules:
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden):
            with events.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"kind": "loaded_runtime", "detail": name}) + "\\n")
atexit.register(finished)
bootstrap = os.environ.get("RTPEVAL_TEST_BOOTSTRAP")
if bootstrap:
    exec(compile(bootstrap, "<offline planner fixture>", "exec"))
print("OFFLINE_RTPEVAL_GUARD_ACTIVE", file=sys.stderr)
"""


@pytest.fixture
def installed_cli(tmp_path):
    executable = Path(sysconfig.get_path("scripts")) / (
        "rtpeval.exe" if os.name == "nt" else "rtpeval"
    )
    assert executable.is_file(), "Install the repository editable project with uv sync"
    guard = tmp_path / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(GUARD, encoding="utf-8")
    events = guard / "events.jsonl"

    def run(
        *args,
        legacy=False,
        block_intake=False,
        probe=False,
        evaluation_offline=False,
        missing_tokenizer=False,
        tools_offline=False,
        legacy_module="backend.evaluation",
        bootstrap="",
    ):
        env = {
            **{key: os.environ[key] for key in CLI_ENVIRONMENT_KEYS if key in os.environ},
            # The guard imports backend before -m adds cwd to sys.path. Select the
            # tested checkout explicitly when reusing another checkout's venv.
            "PYTHONPATH": os.pathsep.join((str(guard), str(ROOT))),
            "PYTHONUTF8": "1",
            "RTPEVAL_TEST_EVENTS": str(events),
            "RTPEVAL_TEST_BLOCK_INTAKE": "1" if block_intake else "0",
            "RTPEVAL_TEST_EVALUATION_OFFLINE": "1" if evaluation_offline else "0",
            "RTPEVAL_TEST_TOOLS_OFFLINE": "1" if tools_offline else "0",
            "RTPEVAL_TEST_MISSING_TOKENIZER": "1" if missing_tokenizer else "0",
            "RTPEVAL_TEST_BOOTSTRAP": bootstrap,
        }
        command = [sys.executable, "-m", legacy_module] if legacy else [str(executable)]
        if probe:
            command = [sys.executable, "-c"]
        result = subprocess.run(
            [*command, *map(str, args)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            encoding="utf-8",
            timeout=60,
        )
        assert "OFFLINE_RTPEVAL_GUARD_ACTIVE" in result.stderr
        attempts = events.read_text(encoding="utf-8")
        assert attempts == "", attempts + result.stdout + result.stderr
        return result

    return run


@pytest.mark.parametrize("legacy", [False, True])
def test_subprocess_uses_selected_checkout_with_shared_environment(
    installed_cli, tmp_path, monkeypatch, legacy
):
    checkout = tmp_path / "checkout"
    package = checkout / "backend"
    package.mkdir(parents=True)
    # Share dependencies/modules, but give this checkout its own package identity.
    (package / "__init__.py").write_text(
        f"__path__.append({str(ROOT / 'backend')!r})\n", encoding="utf-8"
    )
    monkeypatch.setattr(sys.modules[__name__], "ROOT", checkout)
    result = installed_cli(
        "--help",
        legacy=legacy,
        evaluation_offline=True,
        bootstrap=(
            "import backend\n"
            "print('CHECKOUT=' + str(Path(backend.__file__).resolve()), file=sys.stderr)"
        ),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"CHECKOUT={(package / '__init__.py').resolve()}" in result.stderr


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_installed_command_exposes_offline_help(installed_cli, flag):
    result = installed_cli(flag, block_intake=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "validate" in result.stdout
    assert "offline" in result.stdout.lower()


def test_installed_validation_preserves_native_accepted_inventory(installed_cli, batch):
    _, _, write, _, root = batch
    manifest = write()
    originals = {path: path.read_bytes() for path in root.glob("*.json")}
    current = installed_cli("validate", manifest)
    legacy = installed_cli(manifest, legacy=True)
    assert current.returncode == legacy.returncode == 0
    assert current.stdout == legacy.stdout
    report = json.loads(current.stdout)
    assert report["status"] == "accepted"
    assert set(report["inventory"][0]["runs"]) == {"v0", "v1", "v2", "v3"}
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize("fault", ["missing_version", "hash_drift", "unreviewed", "malformed"])
def test_installed_validation_preserves_native_correction_diagnostics(installed_cli, batch, fault):
    manifest, _, write, save, root = batch
    if fault == "missing_version":
        del manifest["groups"][0]["selected_runs"]["v2"]
    elif fault == "unreviewed":
        spec = json.loads((root / "requirements.json").read_bytes())
        spec["review"]["status"] = "pending"
        manifest["groups"][0]["requirement_spec_ref"] = save(
            "requirements.json", spec, spec["schema_version"]
        )
    path = write()
    if fault == "hash_drift":
        (root / "v0.json").write_text("{}", encoding="utf-8")
    elif fault == "malformed":
        path.write_text("{", encoding="utf-8")
    originals = {path: path.read_bytes() for path in root.glob("*.json")}
    current = installed_cli("validate", path)
    legacy = installed_cli(path, legacy=True)
    assert current.returncode == legacy.returncode == 2
    assert current.stdout == legacy.stdout
    report = json.loads(current.stdout)
    assert report["status"] == "needs_material_correction"
    assert report["material_diagnostics"]
    assert {path: path.read_bytes() for path in originals} == originals


def test_validation_help_describes_the_native_offline_interface(installed_cli):
    current = installed_cli("validate", "--help")
    legacy = installed_cli("--help", legacy=True)
    assert current.returncode == legacy.returncode == 0
    assert "usage: rtpeval validate [-h] manifest" in current.stdout
    for phrase in ("manifest", "offline", "emits preparation records", "never scores"):
        assert phrase in current.stdout.lower()
        assert phrase in legacy.stdout.lower()


@pytest.mark.parametrize(
    "args,diagnostic",
    [
        ((), "required"),
        (("--unknown", "validate"), "unrecognized arguments"),
        (("unknown",), "invalid choice"),
        (("validate",), "required"),
        (("validate", "manifest.json", "--unknown"), "unrecognized arguments"),
        (("validate", "manifest.json", "extra.json"), "unrecognized arguments"),
    ],
)
def test_argument_errors_do_not_start_online_work(installed_cli, args, diagnostic):
    result = installed_cli(*args, block_intake=not args or args[0] != "validate")
    assert result.returncode == 2
    assert diagnostic in result.stderr
    assert result.stdout == ""
    if args and args[0] == "validate":
        assert "usage: rtpeval validate [-h] manifest" in result.stderr


def test_missing_manifest_preserves_native_file_diagnostics(installed_cli, tmp_path):
    path = tmp_path / "missing.json"
    current = installed_cli("validate", path)
    legacy = installed_cli(path, legacy=True)
    assert current.returncode == legacy.returncode == 2
    assert current.stdout == legacy.stdout
    assert json.loads(current.stdout)["material_diagnostics"]


@pytest.mark.parametrize(
    "operation,kind",
    [
        ("socket.getaddrinfo('example.test', 443)", "network"),
        ("socket.socket().connect(('203.0.113.1', 443))", "network"),
        ("os.environ.get('AZURE_OPENAI_API_KEY')", "credential_read"),
        ("open('.env', encoding='utf-8')", "credential_file"),
        ("__import__('backend.app.runtime.config')", "runtime_import"),
    ],
)
def test_offline_guard_detects_attempts_even_when_caught(installed_cli, operation, kind):
    probe = "import os, socket\ntry:\n    " + operation + "\nexcept RuntimeError:\n    pass\n"
    with pytest.raises(AssertionError, match='"kind": "' + kind + '"'):
        installed_cli(probe, probe=True)
