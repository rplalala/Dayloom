"""Explicit full-baseline acceptance through an extracted release, never a source DB.

Run with ``python -m backend.tests.deployment.archive_acceptance --help``.
Inputs are explicit local artifacts; provider transports remain controlled. The
three stages permit diagnosis without repeatedly restoring a multi-GB baseline.
Generated configuration and operational backups are private and must be cleaned.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import threading
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]
OS_KEYS = {
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


def command(arguments, *, cwd=ROOT, environment=None, input=None, timeout=2400):
    env = {k: v for k, v in os.environ.items() if k.upper() in OS_KEYS}
    env.update(MSYS_NO_PATHCONV="1", PYTHONUTF8="1")
    env.update(environment or {})
    result = subprocess.run(
        list(map(str, arguments)),
        cwd=cwd,
        env=env,
        input=input,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode:
        # Do not print captured bootstrap output, private rows or provider values.
        frames = re.findall(r'File "([^\"]+)", line (\d+), in ([^\n]+)', result.stderr)
        location = f"; child frame {frames[-1]}" if frames else ""
        raise RuntimeError(
            "Acceptance command failed: " + " ".join(map(str, arguments[:3])) + location
        )
    return result.stdout


class Acceptance:
    def __init__(self, args):
        self.args = args
        self.work = args.work.resolve()
        self.bundle = self.work / "bundle"
        self.origin = f"http://localhost:{args.port}"
        self.record = self.work / "result.json"
        if (self.bundle / "config/.env").exists():
            installed = dotenv_values(self.bundle / "config/.env", interpolate=False)
            assert installed["COMPOSE_PROJECT_NAME"] == args.project
            assert installed["DAYLOOM_DB_NAME"] == args.database

    def save(self, **values):
        previous = json.loads(self.record.read_text()) if self.record.exists() else {}
        self.record.write_text(json.dumps(previous | values, indent=2) + "\n")

    def launch(self, *arguments, bundle=None, environment=None):
        return command(
            [
                self.args.bash,
                ((bundle or self.bundle) / "start.sh").as_posix(),
                *map(str, arguments),
            ],
            cwd=self.work,
            environment=environment,
        )

    def compose(self, *arguments, bundle=None, input=None, guarded=False):
        folder = bundle or self.bundle
        selection = [
            "docker",
            "compose",
            "--project-directory",
            folder,
            "--env-file",
            folder / "config/.env",
            "-f",
            folder / "compose.yaml",
        ]
        if guarded:
            selection += ["-f", self.work / "egress.yaml"]
        return command([*selection, *arguments], input=input)

    def sql(self, query, *, bundle=None):
        return self.compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-XAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "dayloom",
            "-d",
            self.args.database,
            input=query,
            bundle=bundle,
        ).strip()

    def client(self, port=None):
        port = port or self.args.port
        return httpx.Client(
            base_url=f"http://127.0.0.1:{port}",
            trust_env=False,
            headers={"Host": f"localhost:{port}", "Origin": f"http://localhost:{port}"},
            timeout=45,
        )

    def wait(self, port=None):
        with self.client(port) as client:
            for _ in range(240):
                try:
                    if client.get("/health").status_code == 200:
                        return
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
        raise RuntimeError("Application did not become live")

    def extract(self, folder):
        metadata = json.loads(
            command([sys.executable, "-m", "deploy.release.package", "verify", self.args.archive])
        )
        folder.mkdir()
        with tarfile.open(self.args.archive) as archive:
            archive.extractall(folder, filter="data")
        assert {p.name for p in folder.iterdir()} == {
            "compose.yaml",
            ".env.example",
            "start.sh",
            "README.md",
        }
        return metadata

    def cold(self):
        assert not self.bundle.exists(), "Select a fresh work directory"
        assert not command(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                "label=com.docker.compose.project=" + self.args.project,
            ]
        ).strip()
        assert not command(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                "label=com.docker.compose.project=" + self.args.project,
            ]
        ).strip()
        self.work.mkdir(parents=True, exist_ok=True)
        metadata = self.extract(self.bundle)
        started = time.monotonic()
        stop, peaks = threading.Event(), {"docker_stats": {}, "cgroup": {}}
        sampler = threading.Thread(target=self.sample_memory, args=(stop, peaks), daemon=True)
        sampler.start()
        try:
            output = self.launch(
                "--non-interactive",
                environment={
                    "COMPOSE_PROJECT_NAME": self.args.project,
                    "DAYLOOM_DB_NAME": self.args.database,
                    "DAYLOOM_HOST_PORT": str(self.args.port),
                },
            )
        finally:
            stop.set()
            sampler.join(timeout=20)
        assert len(re.findall(r'"management_password"\s*:\s*"([^\"]+)"', output)) == 1
        del output
        self.wait()
        install_seconds = round(time.monotonic() - started, 2)
        with self.client() as client:
            assert client.get("/config").status_code == 200
            assert client.get("/api/auth/current").status_code == 503
            access = client.get("/api/config/access").json()
            assert access["password_required"] and not access.get("default_test_password")
            assert client.get("/api/config").status_code == 401
        inventory = json.loads(self.compose("run", "--rm", "--no-deps", "init", "inspect"))
        manifest = json.loads(self.args.manifest.read_text())
        assert inventory == manifest["database"], "Complete restored inventory differs"
        parity = self.sql(
            "SET search_path=tripworld,public;\n"
            + self.args.topk_sql.read_text(encoding="utf-8-sig")
        )
        rows = [line.split("|") for line in parity.splitlines() if "|" in line]
        expected = json.loads(self.args.source_evidence.read_text())["saved_vector_parity"]
        assert [row[0] for row in rows] == [row[0] for row in expected]
        assert all(
            abs(float(row[1]) - wanted[1]) < 1e-12
            for row, wanted in zip(rows, expected, strict=True)
        )
        self.save(
            metadata=metadata,
            cold_seconds=install_seconds,
            verification_seconds=round(time.monotonic() - started - install_seconds, 2),
            inventory_match=True,
            vector_parity_rows=len(rows),
            archive_bytes=self.args.archive.stat().st_size,
            archive_sha256=hashlib.sha256(self.args.archive.read_bytes()).hexdigest(),
            dump_bytes=manifest["files"]["database.pgcustom"]["bytes"],
            inventory=inventory,
            sampled_memory_bytes=peaks,
            public_distribution="pending publication authorization",
        )

    def sample_memory(self, stop, peaks):
        """Sample this project's Docker memory metric; not a minimum-RAM guarantee."""
        scale = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}
        while not stop.is_set():
            try:
                containers = command(
                    [
                        "docker",
                        "ps",
                        "-q",
                        "--filter",
                        "label=com.docker.compose.project=" + self.args.project,
                    ],
                    timeout=10,
                ).split()
                if containers:
                    usage = command(
                        [
                            "docker",
                            "stats",
                            "--no-stream",
                            "--format",
                            "{{.Name}}|{{.MemUsage}}",
                            *containers,
                        ],
                        timeout=15,
                    )
                    for line in usage.splitlines():
                        name, memory = line.split("|", 1)
                        amount, unit = re.fullmatch(
                            r"([0-9.]+)([A-Za-z]+)", memory.split(" / ")[0]
                        ).groups()
                        peaks["docker_stats"][name] = max(
                            peaks["docker_stats"].get(name, 0), int(float(amount) * scale[unit])
                        )
                        # Unlike Docker's displayed working set, memory.current includes
                        # charged page cache. Both are observations on this engine only.
                        current = int(
                            command(
                                ["docker", "exec", name, "cat", "/sys/fs/cgroup/memory.current"],
                                timeout=5,
                            ).strip()
                        )
                        peaks["cgroup"][name] = max(peaks["cgroup"].get(name, 0), current)
            except Exception:
                # Sampling never changes the acceptance outcome or runtime configuration.
                pass
            stop.wait(3)

    def guard(self, bundle=None):
        # Test-only Compose overlay. Docker DNS still resolves the internal postgres
        # service; external names have no resolver and known provider names are loopback.
        (self.work / "egress.yaml").write_text(
            "services:\n  app:\n    dns: [127.0.0.1]\n    extra_hosts:\n"
            "      - 'api.openai.com:127.0.0.1'\n"
            "      - 'places.googleapis.com:127.0.0.1'\n"
            "      - 'api.unsplash.com:127.0.0.1'\n"
            "      - 'controlled.services.ai.azure.com:127.0.0.1'\n"
            "    environment:\n      HTTP_PROXY: ''\n      HTTPS_PROXY: ''\n"
            "      ALL_PROXY: ''\n      NO_PROXY: '*'\n"
        )
        self.compose(
            "up", "-d", "--no-deps", "--force-recreate", "app", bundle=bundle, guarded=True
        )
        self.wait(self.args.port + 1 if bundle else None)

    def configuration(self):
        self.guard()
        password = json.loads(
            self.compose(
                "exec",
                "-T",
                "app",
                "python",
                "-m",
                "deploy.docker.app_entrypoint",
                "reset-management-password",
                "--directory",
                "/instance",
            )
        )["management_password"]
        from playwright.sync_api import expect, sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context()
            context.route(
                "**/*",
                lambda route: (
                    route.continue_()
                    if route.request.url.startswith(self.origin + "/")
                    else route.abort()
                ),
            )
            page = context.new_page()
            page.goto(self.origin + "/config")
            page.get_by_label("Configuration password", exact=True).fill(password)
            page.get_by_role("button", name="Unlock configuration", exact=True).click()
            fields = {
                "Foundry endpoint": "https://controlled.services.ai.azure.com/openai/v1",
                "Foundry API key": "controlled-t8-foundry",
                "OpenAI API key": "controlled-t8-openai-" + str(time.time_ns()),
                "Google Maps API key": "controlled-t8-google",
                "Unsplash access key": "controlled-t8-unsplash",
            }
            for label, value in fields.items():
                page.get_by_label(label, exact=True).fill(value)
            page.get_by_role("button", name="Save configuration", exact=True).click()
            expect(page.get_by_text("Saved. Restart Dayloom", exact=False)).to_be_visible()
            context.close()
            browser.close()
        with self.client() as client:
            unlocked = client.post("/api/config/session", json={"password": password})
            assert unlocked.status_code == 200
            client.headers["X-CSRF-Token"] = unlocked.json()["csrf_token"]
            assert client.get("/api/config").json()["restart_required"] is True
            assert (
                client.get("/api/config/access", headers={"Host": "other.local"}).status_code == 403
            )
            assert (
                client.post(
                    "/api/config/session",
                    headers={"Origin": "http://other.local"},
                    json={"password": password},
                ).status_code
                == 403
            )
            assert (
                client.put(
                    "/api/config",
                    headers={"X-CSRF-Token": ""},
                    json={"revision": client.get("/api/config").json()["revision"], "changes": {}},
                ).status_code
                == 403
            )
        self.compose("restart", "app", guarded=True)
        self.wait()
        with self.client() as client:
            unlocked = client.post("/api/config/session", json={"password": password})
            assert unlocked.status_code == 200
            client.headers["X-CSRF-Token"] = unlocked.json()["csrf_token"]
            view = client.get("/api/config").json()
            assert not view["restart_required"] and view["running_ready"]
            assert not view["fields"]["OPENAI_API_KEY"]["locked"]
        self.save(browser_configuration=True, restart_to_apply=True)

    def state(self, bundle=None):
        return self.sql(
            """SELECT json_build_object(
            'receipt',(SELECT row_to_json(t) FROM app.deployment_baseline t),
            'users',(SELECT json_agg(t ORDER BY id) FROM app.users t),
            'profiles',(SELECT json_agg(t ORDER BY user_id) FROM app.user_profiles t),
            'migrations',(SELECT json_agg(t ORDER BY name) FROM app.schema_migrations t),
            'drafts',(SELECT json_agg(t ORDER BY id) FROM app.planning_drafts t),
            'trips',(SELECT json_agg(t ORDER BY id) FROM app.trips t),
            'previews',(SELECT json_agg(t ORDER BY id) FROM app.itinerary_previews t),
            'tasks',(SELECT json_agg(t ORDER BY id) FROM app.planning_tasks t));""",
            bundle=bundle,
        )

    def journey(self):
        recorded = json.loads(self.record.read_text())
        if not recorded.get("browser_configuration"):
            self.configuration()
        else:
            self.guard()
        with self.client() as client:
            login = client.post(
                "/api/auth/login", json={"email": "admin@admin.com", "password": "admin123456"}
            )
            assert login.status_code == 200
            library = client.get("/api/library").json()
            assert len([item for item in library["items"] if item["kind"] == "saved"]) == 4
            from backend.tests.product.test_drafts import editor

            recorded = json.loads(self.record.read_text())
            if "draft_id" not in recorded:
                draft = client.post(
                    "/api/drafts",
                    headers={"X-CSRF-Token": login.json()["csrf_token"]},
                    json={"title": "Full archive retained draft", "editor": editor()},
                )
                assert draft.status_code == 201
                self.save(draft_id=draft.json()["id"], default_admin=True)
            else:
                assert client.get("/api/drafts/" + recorded["draft_id"]).status_code == 200
        # Transport code is supplied through stdin, excluded from production images.
        if not recorded.get("media"):
            script = (Path(__file__).with_name("archive_media_probe.py")).read_text()
            media = json.loads(self.compose("exec", "-T", "app", "python", input=script))
            self.save(media=media)
        self.browser_library()
        expected = hashlib.sha256(self.state().encode()).hexdigest()
        values = dict(dotenv_values(self.bundle / "config/.env", interpolate=False))
        identity = {
            name: values[name]
            for name in (
                "PRODUCT_JWT_SECRET",
                "DAYLOOM_DB_PASSWORD",
                "OPENAI_API_KEY",
                "GOOGLE_MAPS_API_KEY",
                "DAYLOOM_BASELINE_ID",
            )
        }
        self.compose("stop")
        self.compose("start", "postgres", "app")
        self.wait()
        assert hashlib.sha256(self.state().encode()).hexdigest() == expected
        self.guard()
        assert hashlib.sha256(self.state().encode()).hexdigest() == expected
        self.compose("stop", "app", "postgres")
        self.compose("start", "app")
        time.sleep(2)
        with self.client() as client:
            try:
                assert client.get("/health").status_code != 200
            except httpx.TransportError:
                pass
        self.compose("start", "postgres")
        self.wait()
        assert hashlib.sha256(self.state().encode()).hexdigest() == expected
        retained = dotenv_values(self.bundle / "config/.env", interpolate=False)
        assert {name: retained[name] for name in identity} == identity
        self.save(
            lifecycle=True,
            durable_state_sha256=expected,
            management_sha256=hashlib.sha256(
                (self.bundle / "config/.config-access.json").read_bytes()
            ).hexdigest(),
            private_identity_sha256=hashlib.sha256(
                json.dumps(identity, sort_keys=True).encode()
            ).hexdigest(),
        )

    def browser_library(self):
        import base64
        from urllib.parse import urlsplit

        from playwright.sync_api import expect, sync_playwright

        external_images, denied = [], []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context()

            def intercept(route):
                if route.request.url.startswith(self.origin + "/"):
                    return route.continue_()
                if route.request.resource_type == "image":
                    external_images.append(urlsplit(route.request.url).hostname)
                    return route.fulfill(
                        status=200,
                        content_type="image/png",
                        body=base64.b64decode(
                            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jvS8AAAAASUVORK5CYII="
                        ),
                    )
                denied.append(urlsplit(route.request.url).hostname)
                return route.abort()

            context.route("**/*", intercept)
            response = context.request.post(
                self.origin + "/api/auth/login",
                data={"email": "admin@admin.com", "password": "admin123456"},
                headers={"Origin": self.origin},
            )
            assert response.status == 200
            library = context.request.get(self.origin + "/api/library").json()
            page = context.new_page()
            page.goto(self.origin + "/trips")
            expect(page.get_by_text("Full archive retained draft", exact=True)).to_be_visible()
            trip = next(item for item in library["items"] if item["kind"] == "saved")
            page.goto(self.origin + "/trips/" + trip["id"])
            expect(page.locator(".detail-cover")).to_be_visible()
            page.wait_for_timeout(500)
            page.screenshot(path=str(self.work / "baseline-trip.png"), full_page=True)
            context.close()
            browser.close()
        self.save(
            browser_baseline_trip=True,
            external_images_replaced=len(external_images),
            external_other_blocked=len(denied),
        )

    def recovery(self):
        recorded = json.loads(self.record.read_text())
        backup = self.work / "private.dayloom-backup"
        started = time.monotonic()
        self.launch("upgrade", recorded["metadata"]["app_image"], "--backup", backup.as_posix())
        self.wait()
        expected = recorded["durable_state_sha256"]
        assert hashlib.sha256(self.state().encode()).hexdigest() == expected
        self.launch("verify-backup", backup.as_posix())
        self.save(
            upgrade=True,
            backup_bytes=(backup / "database.pgcustom").stat().st_size,
            backup_seconds=round(time.monotonic() - started, 2),
        )
        self.compose("down", "--volumes", "--remove-orphans")
        recovered = self.work / "recovered"
        self.extract(recovered)
        started = time.monotonic()
        self.launch(
            "restore-backup",
            backup.as_posix(),
            "--project",
            self.args.project + "-restore",
            "--port",
            str(self.args.port + 1),
            bundle=recovered,
        )
        self.wait(self.args.port + 1)
        self.guard(recovered)
        assert hashlib.sha256(self.state(recovered).encode()).hexdigest() == expected
        retained = dotenv_values(recovered / "config/.env", interpolate=False)
        identity = {
            name: retained[name]
            for name in (
                "PRODUCT_JWT_SECRET",
                "DAYLOOM_DB_PASSWORD",
                "OPENAI_API_KEY",
                "GOOGLE_MAPS_API_KEY",
                "DAYLOOM_BASELINE_ID",
            )
        }
        assert (
            hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
            == (recorded["private_identity_sha256"])
        )
        assert (
            hashlib.sha256((recovered / "config/.config-access.json").read_bytes()).hexdigest()
            == (recorded["management_sha256"])
        )
        with self.client(self.args.port + 1) as client:
            assert (
                client.post(
                    "/api/auth/login", json={"email": "admin@admin.com", "password": "admin123456"}
                ).status_code
                == 200
            )
            assert (
                client.get("/api/drafts/" + recorded["draft_id"]).json()["title"]
                == "Full archive retained draft"
            )
        script = (Path(__file__).with_name("archive_media_probe.py")).read_text()
        restored_media = json.loads(
            self.compose(
                "exec", "-T", "app", "python", "-", "--read-only", input=script, bundle=recovered
            )
        )
        self.save(
            restore=True,
            restore_seconds=round(time.monotonic() - started, 2),
            restored_media=restored_media,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["cold", "journey", "recovery"])
    for name in ("work", "archive", "manifest", "source-evidence", "topk-sql"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, default=55781)
    parser.add_argument("--bash", default="bash")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]*test[a-z0-9_-]*", args.project) or not re.fullmatch(
        r"[a-z0-9_]*test[a-z0-9_]*", args.database
    ):
        parser.error("Acceptance requires a test database and project")
    try:
        acceptance = Acceptance(args)
        getattr(acceptance, args.stage)()
        print(
            json.dumps({"stage": args.stage, "status": "passed", "record": str(acceptance.record)})
        )
    except Exception as error:
        import traceback

        traceback.print_tb(error.__traceback__)
        if isinstance(error, RuntimeError):
            print(str(error), file=sys.stderr)
        print(
            f"Acceptance stage failed ({type(error).__name__}); retain private work for diagnosis.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
