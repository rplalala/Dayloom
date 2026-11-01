"""Opt-in real Bash/Compose recovery against small, independently supplied images.

Supply DAYLOOM_COMPOSE_TESTS=1, DAYLOOM_TEST_APP_IMAGE,
DAYLOOM_TEST_BASELINE_IMAGE and DAYLOOM_TEST_BASELINE_ID. The baseline must contain
the current Product schema and a controlled account; this test never exports data.
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]


def command(arguments, *, cwd, environment, input=None, timeout=240):
    result = subprocess.run(arguments, cwd=cwd, env=environment, input=input,
                            text=True, capture_output=True, timeout=timeout)
    assert result.returncode == 0, "Controlled deployment command failed: " + result.stderr[-2000:]
    return result.stdout


def wait_health(origin):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            with urlopen(local_request(origin, "/health"), timeout=2) as response:
                assert json.load(response) == {"status": "ok"}
                return
        except (URLError, TimeoutError, ConnectionError):
            time.sleep(0.2)
    pytest.fail("Controlled application did not become live")


def local_request(origin, path):
    return Request(origin.replace("localhost", "127.0.0.1") + path,
                   headers={"Host": origin.removeprefix("http://")})


def configuration_fingerprint(paths):
    result = {}
    for path in paths:
        content = (json.dumps(dict(dotenv_values(path)), sort_keys=True).encode()
                   if path.name == ".env" else path.read_bytes())
        result[path.name] = hashlib.sha256(content).hexdigest()
    return result


@pytest.mark.skipif(os.environ.get("DAYLOOM_COMPOSE_TESTS") != "1",
                    reason="Requires explicitly selected local controlled deployment images")
def test_bash_relaunch_stop_start_recreate_and_late_database_preserve_instance(tmp_path):
    bash = os.environ.get("DAYLOOM_TEST_BASH") or shutil.which("bash")
    assert bash, "Bash is required for this opt-in acceptance"
    selected = {name: os.environ[name] for name in (
        "DAYLOOM_TEST_APP_IMAGE", "DAYLOOM_TEST_BASELINE_IMAGE", "DAYLOOM_TEST_BASELINE_ID",
    )}
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in ("start.sh", "compose.yaml", ".env.example", "README.md"):
        shutil.copyfile(ROOT / "deploy" / name, bundle / name)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = "http://localhost:" + str(port)
    project = "dayloom-t5-recovery-test-" + uuid4().hex[:10]
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA",
               "LOCALAPPDATA", "COMSPEC", "PATHEXT", "HOME", "PROGRAMFILES"}
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment.update({
        "DAYLOOM_APP_IMAGE": selected["DAYLOOM_TEST_APP_IMAGE"],
        "DAYLOOM_BASELINE_IMAGE": selected["DAYLOOM_TEST_BASELINE_IMAGE"],
        "DAYLOOM_BASELINE_ID": selected["DAYLOOM_TEST_BASELINE_ID"],
        "COMPOSE_PROJECT_NAME": project, "DAYLOOM_DB_NAME": "dayloom_t5_test",
        "DAYLOOM_DB_USER": "controlled", "DAYLOOM_HOST_PORT": str(port),
    })
    compose = ["docker", "compose", "--project-directory", str(bundle), "--env-file",
               str(bundle / "config" / ".env"), "-f", str(bundle / "compose.yaml")]

    def run(*arguments, input=None):
        return command([*compose, *arguments], cwd=bundle, environment=environment, input=input)

    def query(sql):
        return run("exec", "-T", "postgres", "psql", "-XAt", "-v", "ON_ERROR_STOP=1",
                   "-U", "controlled", "-d", "dayloom_t5_test", input=sql).strip()

    def durable_state():
        return query("""SELECT json_build_object(
            'receipt',(SELECT row_to_json(t) FROM app.deployment_baseline t),
            'users',(SELECT count(*) FROM app.users),
            'draft',(SELECT title FROM app.planning_drafts
                     WHERE id='00000000-0000-0000-0000-000000000252'),
            'media',(SELECT media_cache FROM app.itinerary_previews WHERE operation_key='t5-media'),
            'task',(SELECT json_build_array(state,fence,execution_id) FROM app.planning_tasks
                    WHERE operation_key='t5-historical'))""")

    try:
        # The caller's cwd differs from the bundle. Bash still owns the complete launch.
        command([bash, str(bundle / "start.sh"), "--non-interactive"], cwd=ROOT,
                environment=environment)
        wait_health(origin)
        with urlopen(local_request(origin, "/config")) as response:
            assert response.status == 200
        with pytest.raises(HTTPError) as unavailable:
            urlopen(local_request(origin, "/api/auth/me"))
        assert unavailable.value.code == 503  # Liveness does not imply provider readiness.
        query("""INSERT INTO app.users (id,email,password_hash)
            VALUES ('00000000-0000-0000-0000-000000000251','t5@example.test','controlled-hash');
            INSERT INTO app.planning_drafts(id,owner_id,title,editor)
            VALUES ('00000000-0000-0000-0000-000000000252','00000000-0000-0000-0000-000000000251',
                    'Retained after recreation','{"editor_version":1}');
            INSERT INTO app.itinerary_previews(id,owner_id,source_kind,operation_key,fingerprint,
                    snapshot,media_cache)
            VALUES ('00000000-0000-0000-0000-000000000253','00000000-0000-0000-0000-000000000251',
                    'imported','t5-media',repeat('a',64),'{"schema_version":"product_detail_1"}',
                    '{"photo":{"url":"https://example.invalid/retained.jpg","revision":"t5","attribution":"retained"}}');
            INSERT INTO app.planning_tasks(id,owner_id,operation_key,fingerprint,request,
                    reference_date,state,pending_deadline)
            VALUES ('00000000-0000-0000-0000-000000000254','00000000-0000-0000-0000-000000000251',
                    't5-historical',repeat('b',64),'{"input_version":"planning_request_2"}',
                    CURRENT_DATE,'pending',clock_timestamp()-interval '1 hour');""")
        dotenv = bundle / "config" / ".env"
        with dotenv.open("a", encoding="utf-8") as stream:
            stream.write("\nOPENAI_API_KEY='controlled-saved-not-a-provider-key'\n")
        protected_files = [dotenv, bundle / "config" / "product.yaml",
                           bundle / "config" / ".config-access.json"]
        fingerprints = configuration_fingerprint(protected_files)
        expected = durable_state()
        command([bash, str(bundle / "start.sh"), "--non-interactive"], cwd=ROOT,
                environment=environment)
        assert durable_state() == expected
        run("stop")
        run("start", "postgres", "app")
        wait_health(origin)
        assert durable_state() == expected
        run("up", "-d", "--no-deps", "--force-recreate", "app")
        wait_health(origin)
        assert durable_state() == expected
        # Direct app starts before its database: process stays non-ready, then recovers
        # through its own guard without another Compose dependency evaluation.
        run("stop", "app", "postgres")
        run("start", "app")
        time.sleep(2)
        with pytest.raises((URLError, ConnectionError, TimeoutError)):
            urlopen(local_request(origin, "/health"), timeout=1)
        run("start", "postgres")
        wait_health(origin)
        assert durable_state() == expected
        assert configuration_fingerprint(protected_files) == fingerprints
        # Every restart retains historical work unclaimed and the exact cached URL.
        state = json.loads(expected)
        assert state["task"] == ["pending", 0, None]
        assert state["media"]["photo"]["revision"] == "t5"
    finally:
        if (bundle / "config" / ".env").exists():
            run("down", "--volumes", "--remove-orphans")
