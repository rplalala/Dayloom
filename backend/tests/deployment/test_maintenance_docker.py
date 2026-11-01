"""Opt-in Bash → Compose → Product recovery on small, disposable fixture storage."""

import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    os.environ.get("DAYLOOM_T6_DOCKER_TESTS") != "1",
    reason="Requires explicit isolated Docker fixture acceptance",
)


def command(arguments, *, cwd=ROOT, environment=None, input=None, timeout=240, expected=0):
    allowed = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "COMSPEC",
        "PATHEXT",
        "HOME",
        "PROGRAMFILES",
    }
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    result = subprocess.run(
        list(map(str, arguments)),
        cwd=cwd,
        env={**env, **(environment or {})},
        input=input,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == expected, "Controlled command failed: " + result.stderr[-4000:]
    return result.stdout


def test_bash_upgrade_once_and_private_restore_preserve_product_identity(tmp_path):
    fixture = Path(os.environ["DAYLOOM_T6_FIXTURE_BASELINE"]).resolve()
    # An explicit small fixture is required. Never discover a source/runtime connection.
    assert fixture.name == "baseline" and (fixture / "database.pgcustom").stat().st_size < 200000
    bash = os.environ.get("DAYLOOM_TEST_BASH", "bash")
    tag = "t6-" + uuid4().hex[:10]
    baseline_image = "dayloom-baseline:" + tag
    old_image = "dayloom-app:" + tag
    new_image = old_image + "-upgrade"
    bad_image = old_image + "-incompatible"
    project, recovered_project = "dayloom-" + tag, "dayloom-" + tag + "-restore"
    port, recovered_port = 55761, 55762
    manifest = json.loads((fixture / "baseline.json").read_text())
    baseline_id = manifest["baseline_id"]
    overlay = tmp_path / "overlay"
    shutil.copytree(ROOT / "deploy", overlay / "deploy")
    shutil.copytree(fixture / "runtime", overlay / "resources")
    shutil.copyfile(ROOT / "backend/app/product/database.py", overlay / "database.py")
    (overlay / "Dockerfile").write_text(
        "FROM dayloom-app:t4-local\nUSER 0:0\nCOPY deploy/ deploy/\n"
        "COPY database.py backend/app/product/database.py\n"
        "COPY resources/ data/tripworld/\nUSER 1000:1000\n",
        encoding="utf-8",
    )
    command(
        [
            "docker",
            "build",
            "--build-context",
            "baseline-data=" + str(fixture),
            "-f",
            "deploy/docker/baseline.Dockerfile",
            "-t",
            baseline_image,
            ".",
        ]
    )
    command(["docker", "build", "-t", old_image, str(overlay)])
    migration = (
        "UPDATE app.user_profiles SET display_name=display_name||' [upgraded]' "
        "WHERE display_name='Maintenance User';\n"
    )
    # A second execution would change the observable name twice, so repetition is detectable.
    migration = migration.replace(
        "WHERE display_name='Maintenance User'", "WHERE display_name LIKE 'Maintenance User%'"
    )
    (overlay / "011_controlled.sql").write_text(migration, encoding="utf-8")
    (overlay / "Dockerfile").write_text(
        f"FROM {old_image}\nUSER 0:0\nCOPY 011_controlled.sql "
        "backend/app/product/migrations/011_controlled.sql\nUSER 1000:1000\n",
        encoding="utf-8",
    )
    command(["docker", "build", "-t", new_image, str(overlay)])
    (overlay / "bad-manifest.json").write_text(
        '{"output_sha256":"incompatible-controlled","entity_count":1}', encoding="utf-8"
    )
    (overlay / "Dockerfile").write_text(
        f"FROM {new_image}\nUSER 0:0\nCOPY bad-manifest.json "
        "data/tripworld/artifacts/retrieval_entities.parquet.manifest.json\nUSER 1000:1000\n",
        encoding="utf-8",
    )
    command(["docker", "build", "-t", bad_image, str(overlay)])

    def bundle(name):
        target = tmp_path / name
        target.mkdir()
        for filename in ("start.sh", "compose.yaml", ".env.example", "README.md"):
            shutil.copyfile(ROOT / "deploy" / filename, target / filename)
        text = (target / ".env.example").read_text()
        for old, new in (
            ("dayloom-app:local", old_image),
            ("dayloom-baseline:local", baseline_image),
            ("UNRELEASED", baseline_id),
        ):
            text = text.replace(old, new)
        (target / ".env.example").write_text(text, encoding="utf-8")
        return target

    source, destination = bundle("source"), bundle("recovered")
    env = {"DAYLOOM_HOST_PORT": str(port), "COMPOSE_PROJECT_NAME": project}

    def launch(bundle, *arguments, environment=None, expected=0):
        return command(
            [
                bash,
                (bundle / "start.sh").as_posix(),
                *[
                    a.replace("\\", "/") if isinstance(a, str) and len(a) > 1 and a[1] == ":" else a
                    for a in arguments
                ],
            ],
            cwd=tmp_path,
            environment=environment,
            timeout=300,
            expected=expected,
        )

    def compose(bundle, *arguments, input=None, expected=0):
        return command(
            [
                "docker",
                "compose",
                "--project-directory",
                bundle,
                "--env-file",
                bundle / "config/.env",
                "-f",
                bundle / "compose.yaml",
                *arguments,
            ],
            input=input,
            expected=expected,
        )

    def seed(sql):
        compose(
            source,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "dayloom",
            "-d",
            "dayloom",
            input=sql,
        )

    try:
        launch(source, "--non-interactive", environment=env)
        from backend.app.tripworld.database.vectors import SPACE, SPACE_ID

        seed(
            "CREATE TABLE tripworld.embedding_spaces("
            "space_id text PRIMARY KEY, configuration jsonb);"
            + "INSERT INTO tripworld.embedding_spaces VALUES ('"
            + SPACE_ID
            + "','"
            + json.dumps(SPACE)
            + "'); ALTER TABLE tripworld.entities ADD COLUMN IF NOT EXISTS artifact_hash text;"
            + "ALTER TABLE tripworld.entities ADD COLUMN IF NOT EXISTS policy_version text;"
            + "UPDATE tripworld.entities SET artifact_hash='"
            + json.loads(
                (fixture / "runtime/artifacts/retrieval_entities.parquet.manifest.json").read_text()
            )["output_sha256"]
            + "',policy_version='tripworld-production-policy-v1';"
        )
        launch(
            source,
            "upgrade",
            old_image,
            "--backup",
            str(tmp_path / "provider-empty.dayloom-backup"),
        )
        # Controlled provider settings enable business routes; this test sends no provider request.
        config = source / "config"
        with (config / ".env").open("a", encoding="utf-8") as stream:
            stream.write(
                "\nOPENAI_API_KEY=controlled-t6\nGOOGLE_MAPS_API_KEY=controlled-t6\n"
                "AZURE_OPENAI_API_KEY=controlled-t6\n"
            )
        import yaml

        deployment = yaml.safe_load((config / "product.yaml").read_text())
        deployment["foundry"]["endpoint"] = "https://example.services.ai.azure.com/openai/v1"
        (config / "product.yaml").write_text(yaml.safe_dump(deployment), encoding="utf-8")
        compose(source, "restart", "app")
        compose(source, "up", "-d", "--no-deps", "--wait", "--wait-timeout", "180", "app")
        origin = f"http://localhost:{port}"
        with httpx.Client(
            base_url=f"http://127.0.0.1:{port}", headers={"Host": f"localhost:{port}"}, timeout=30
        ) as client:
            account = client.post(
                "/api/auth/register",
                headers={"Origin": origin},
                json={
                    "email": "maintenance@example.test",
                    "password": "controlled test password",
                    "display_name": "Maintenance User",
                },
            )
            assert account.status_code == 201, account.text
            from backend.tests.product.test_drafts import editor

            created = client.post(
                "/api/drafts",
                json={"title": "Retained later draft", "editor": editor()},
                headers={"Origin": origin, "X-CSRF-Token": account.json()["csrf_token"]},
            )
            assert created.status_code == 201, created.text
            draft_id = created.json()["id"]
            from backend.tests.product.test_imports import source as imported_itinerary

            headers = {"Origin": origin, "X-CSRF-Token": account.json()["csrf_token"]}
            imported = client.post(
                "/api/imports",
                headers={**headers, "X-Import-Key": "saved"},
                content=json.dumps({**imported_itinerary(), "title": "Retained later trip"}),
            )
            assert imported.status_code == 200, imported.text
            saved = client.post(
                f"/api/previews/{imported.json()['id']}/save", headers=headers, json={}
            )
            assert saved.status_code == 200, saved.text
            trip_id = saved.json()["saved_trip_id"]
            pending = client.post(
                "/api/imports",
                headers={**headers, "X-Import-Key": "pending"},
                content=json.dumps({**imported_itinerary(), "title": "Retained later preview"}),
            )
            assert pending.status_code == 200, pending.text
            preview_id = pending.json()["id"]
            task_id, media_revision = str(uuid4()), str(uuid4())
            owner = account.json()["id"]
            # Seed a terminal task and an adopted cached image as controlled durable fixtures.
            # All retention assertions below go through Product HTTP, including cache reuse.
            cache_key = hashlib.sha256(
                json.dumps(["cover", "Sydney", 960, 640]).encode()
            ).hexdigest()
            cache = {
                cache_key: {
                    "revision": media_revision,
                    "acquired_at": "2026-11-01T00:00:00+00:00",
                    "sharing_key": None,
                    "media": {
                        "status": "available",
                        "provider": "Unsplash",
                        "kind": "atmosphere",
                        "image_url": "https://images.unsplash.com/controlled-retained-photo",
                        "source_url": "https://unsplash.com/photos/controlled",
                        "authors": [
                            {
                                "name": "Controlled Photographer",
                                "url": "https://unsplash.com/@controlled",
                            }
                        ],
                        "theme": "general",
                    },
                }
            }
            seed(
                "INSERT INTO app.planning_tasks(id,owner_id,operation_key,fingerprint,request,"
                "reference_date,state,pending_deadline) VALUES ('"
                + task_id
                + "','"
                + owner
                + "','controlled-terminal','"
                + "a" * 64
                + '\',\'{"input_version":"planning_request_2","destination":"Sydney"}\','
                "'2026-11-01','cancelled',now()); UPDATE app.trips SET media_cache='"
                + json.dumps(cache)
                + "' WHERE id='"
                + trip_id
                + "';"
            )
            retained_task = client.get(f"/api/planning/tasks/{task_id}").json()
            retained_media = client.get(f"/api/trips/{trip_id}/cover-media").json()
            assert retained_media["cache_revision"] == media_revision

            def retained_content(client, display_name):
                assert client.get("/api/auth/current").json()["display_name"] == display_name
                assert (
                    client.get(f"/api/drafts/{draft_id}").json()["title"] == "Retained later draft"
                )
                assert client.get(f"/api/trips/{trip_id}").json()["title"] == "Retained later trip"
                assert (
                    client.get(f"/api/previews/{preview_id}").json()["snapshot"]["title"]
                    == "Retained later preview"
                )
                assert client.get(f"/api/planning/tasks/{task_id}").json() == retained_task
                assert client.get(f"/api/trips/{trip_id}/cover-media").json() == retained_media

            cookies = dict(client.cookies)
            original = dotenv_values(config / ".env")
            management = (config / ".config-access.json").read_bytes()
            backup = tmp_path / "before.dayloom-backup"
            launch(source, "backup", str(backup))
            launch(source, "verify-backup", str(backup))
            # New bundle defaults deliberately disagree; existing installation must win.
            template = source / ".env.example"
            template.write_text(template.read_text().replace(baseline_id, "f" * 64))
            upgrade_backup = tmp_path / "upgrade.dayloom-backup"
            launch(source, "upgrade", new_image, "--backup", str(upgrade_backup))
            retained_content(client, "Maintenance User [upgraded]")
            for candidate, label in (
                (bad_image, "resource-rejected"),
                (old_image, "downgrade-rejected"),
            ):
                launch(
                    source,
                    "upgrade",
                    candidate,
                    "--backup",
                    str(tmp_path / f"{label}.dayloom-backup"),
                    expected=1,
                )
                assert dotenv_values(config / ".env")["DAYLOOM_APP_IMAGE"] == new_image
                compose(source, "up", "-d", "--no-deps", "--wait", "--wait-timeout", "180", "app")
                retained_content(client, "Maintenance User [upgraded]")
            launch(
                source, "upgrade", new_image, "--backup", str(tmp_path / "repeat.dayloom-backup")
            )
            retained_content(client, "Maintenance User [upgraded]")
            after = dotenv_values(config / ".env")
            for key in (
                "PRODUCT_JWT_SECRET",
                "DAYLOOM_DB_PASSWORD",
                "OPENAI_API_KEY",
                "DAYLOOM_BASELINE_ID",
            ):
                assert after[key] == original[key]
            assert (config / ".config-access.json").read_bytes() == management
        launch(
            destination,
            "restore-backup",
            str(backup),
            "--project",
            recovered_project,
            "--port",
            str(recovered_port),
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{recovered_port}",
            headers={"Host": f"localhost:{recovered_port}"},
            cookies=cookies,
            timeout=30,
        ) as client:
            retained_content(client, "Maintenance User")
        restored = dotenv_values(destination / "config/.env")
        assert restored["PRODUCT_JWT_SECRET"] == original["PRODUCT_JWT_SECRET"]
        assert restored["COMPOSE_PROJECT_NAME"] == recovered_project
        assert (destination / "config/.config-access.json").read_bytes() == management
        compose(
            destination,
            "run",
            "--rm",
            "--no-deps",
            "--entrypoint",
            "python3",
            "-v",
            f"{tmp_path}:/backups:ro",
            "init",
            "-m",
            "deploy.release.maintenance",
            "restore",
            "/backups/before.dayloom-backup",
            expected=2,
        )
        with httpx.Client(
            base_url=f"http://127.0.0.1:{recovered_port}",
            headers={"Host": f"localhost:{recovered_port}"},
            cookies=cookies,
            timeout=30,
        ) as client:
            retained_content(client, "Maintenance User")
        if os.environ.get("DAYLOOM_T6_RESULT_PATH"):
            result = {
                "captured_at": datetime.now(UTC).isoformat(),
                "status": "passed",
                "fixture_baseline_id": baseline_id,
                "fixture_dump_bytes": (fixture / "database.pgcustom").stat().st_size,
                "backup_dump_bytes": (backup / "database.pgcustom").stat().st_size,
                "source_project": project,
                "restore_project": recovered_project,
                "app_images": [old_image, new_image, bad_image],
                "baseline_image": baseline_image,
                "checks": [
                    "provider-empty upgrade",
                    "private backup integrity",
                    "controlled pending migration",
                    "repeat without migration replay",
                    "incompatible resource rejection",
                    "unknown migration downgrade rejection",
                    "independent empty-storage recovery",
                    "nonempty restore rejection",
                    "retained account/session/draft/trip/preview/terminal-task/cached-media",
                    "retained provider/JWT/database/management identity",
                ],
                "limits": (
                    "Small synthetic corpus; no planner/provider action or full baseline restore"
                ),
            }
            Path(os.environ["DAYLOOM_T6_RESULT_PATH"]).write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
    finally:
        for selected in (source, destination):
            if (selected / "config/.env").exists():
                compose(selected, "down", "--volumes", "--remove-orphans")
