"""Run the real light Bash launcher through a controlled Docker CLI boundary."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("light", [True, False])
def test_launcher_selects_only_the_expected_mode_and_keeps_configuration(tmp_path, light):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    for name in (
        "start.sh",
        "compose.light.yaml",
        "light.env.example",
        "compose.yaml",
        ".env.example",
    ):
        (bundle / name).write_bytes((ROOT / "deploy" / name).read_bytes())
    commands = tmp_path / "bin"
    commands.mkdir()
    script = tmp_path / "docker.py"
    script.write_text(
        """import json, os, pathlib, sys
sys.path.insert(0, os.environ["PYTHONPATH"])
args=sys.argv[1:]
root=pathlib.Path(os.environ["FIXTURE_DIR"])
with (root/"calls.jsonl").open("a") as log: log.write(json.dumps(args)+"\\n")
if os.environ["TEST_LIGHT"] == "1":
 assert not any("baseline" in value or value in {"postgres", "init"} for value in args), args
if args[0]=="info":
 print("linux/amd64" if "--format" in args else "ready")
elif args[0]=="version": print("28.0.0")
elif args[:3]==["compose","up","--help"]: print("--wait-timeout")
elif args[:2]==["image","inspect"]: print("[]")
elif args[:2]==["network","ls"]: print("light-network")
elif args[:2]==["network","inspect"]: print("172.31.0.1")
elif args[0]=="inspect": print("172.31.0.1")
elif args[0]=="run":
 if "probe-directory" in args: print("1000:1000")
 else:
  from deploy.docker.app_entrypoint import main
  helpers={"prepare", "prepare-remote", "set-management-peers"}
  command=next(value for value in args if value in helpers)
  selected=args[args.index(command):]
  selected[selected.index("--directory")+1]=str(root/"bundle/config")
  assert main(selected)==0
elif args[0]=="compose":
 if "exec" in args: print('{"setup_required":true}')
 elif "ps" in args: print("controlled-postgres")
else: raise SystemExit("Unexpected Docker command")
""",
        encoding="utf-8",
    )
    docker = commands / "docker"
    docker.write_bytes(b'#!/usr/bin/env bash\nexec "$TEST_PYTHON" "$FIXTURE_DIR/docker.py" "$@"\n')
    docker.chmod(0o755)
    env = {
        k: v
        for k, v in os.environ.items()
        if k.upper()
        in {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "COMSPEC",
            "PATHEXT",
        }
    }
    env.update(
        PYTHONPATH=str(ROOT),
        TEST_PYTHON=sys.executable,
        FIXTURE_DIR=tmp_path.as_posix(),
        DAYLOOM_APP_IMAGE="dayloom-app:controlled",
        DAYLOOM_HOST_PORT="15877",
        TEST_LIGHT="1" if light else "0",
    )
    if not light:
        env.update(DAYLOOM_BASELINE_IMAGE="baseline:controlled", DAYLOOM_BASELINE_ID="b" * 64)
    env["TEST_COMMAND_DIR"] = (
        "/" + commands.drive[0].lower() + commands.as_posix()[2:]
        if os.name == "nt"
        else str(commands)
    )
    git = shutil.which("git")
    windows_bash = Path(git).parent.parent / "bin/bash.exe" if git else Path("missing")
    bash = str(windows_bash) if windows_bash.is_file() else shutil.which("bash")
    result = subprocess.run(
        [
            bash,
            "-c",
            'export PATH="$TEST_COMMAND_DIR:$PATH"; bash start.sh '
            + ("--light " if light else "")
            + "--non-interactive",
        ],
        cwd=bundle,
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    values = dotenv_values(bundle / "config/.env")
    if light:
        assert values["DAYLOOM_DEPLOYMENT_MODE"] == "remote"
        assert values["DAYLOOM_DB_PASSWORD"] == ""
    else:
        assert values["DAYLOOM_BASELINE_ID"] == "b" * 64
        assert len(values["DAYLOOM_DB_PASSWORD"]) >= 32
    assert values["DAYLOOM_MANAGEMENT_PEERS"] == "172.31.0.1"
    calls = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    compose = [call for call in calls if call[0] == "compose" and "--project-directory" in call]
    if light:
        assert any(call[-2:] == ["create", "app"] for call in compose)
    assert any("up" in call for call in compose)
    assert all(("compose.light.yaml" in " ".join(call)) == light for call in compose)
    assert not (bundle / "config/product.yaml").is_symlink()
