"""Host-controlled deployment wiring, separate from editable provider configuration."""

import getpass
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from dotenv import dotenv_values
from dotenv.parser import parse_stream

from backend.app.product.configuration import LocalConfiguration, configuration_file_lock
from backend.app.product.configuration_files import replace_configuration_files
from deploy.docker.instance import bootstrap_instance


def origin_document(path, origin):
    text = path.read_text(encoding="utf-8")
    root = yaml.compose(text)
    if root.flow_style or any(isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken))
                              for token in yaml.scan(text)):
        data = yaml.safe_load(text)
        data["origin"] = origin
        return yaml.safe_dump(data, sort_keys=False)
    node = next((value for key, value in root.value if key.value == "origin"), None)
    if node is None:
        return text.rstrip("\n") + "\norigin: " + json.dumps(origin) + "\n"
    return text[:node.start_mark.index] + json.dumps(origin) + text[node.end_mark.index:]


def update_wiring(directory, values, *, origin=None):
    directory = Path(directory)
    path = directory / ".env"
    if path.is_symlink():
        raise ValueError("Instance configuration must not be a symbolic link")
    with configuration_file_lock(directory / ".env.config.lock"):
        with path.open(encoding="utf-8") as stream:
            retained = "".join(item.original.string for item in parse_stream(stream)
                               if item.key not in values)
        if retained and not retained.endswith("\n"):
            retained += "\n"
        retained += "".join(f"{key}={json.dumps(str(value))}\n" for key, value in values.items())
        replacements = {path: retained}
        if origin is not None:
            deployment = directory / "product.yaml"
            replacements[deployment] = origin_document(deployment, origin)
        replace_configuration_files(replacements)
        os.chmod(path, 0o600)


def prepare_deployment(directory, origin, app_image, baseline_image, baseline_id, uid, gid,
                       project, database_name="dayloom", database_user="dayloom",
                       database_host="postgres", database_port=5432):
    for image in (app_image, baseline_image):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:/@._-]{0,511}", image):
            raise ValueError("Invalid image reference")
    if not re.fullmatch(r"[a-f0-9]{64}", baseline_id):
        raise ValueError("A released baseline identity is required")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", project):
        raise ValueError("Invalid Compose project name")
    if min(uid, gid) < 0:
        raise ValueError("Invalid runtime UID/GID")
    existing = dotenv_values(Path(directory) / ".env", interpolate=False)
    if existing.get("DAYLOOM_BASELINE_ID") not in (None, "", baseline_id):
        raise ValueError("Installed baseline differs; use its existing baseline identity")
    for key, value in (("DAYLOOM_DB_NAME", database_name), ("DAYLOOM_DB_USER", database_user)):
        if existing.get(key) not in (None, "", value):
            raise ValueError("Existing database identity differs; connection edits do not migrate")
    result = bootstrap_instance(
        directory, origin, database_host=database_host, database_port=database_port,
        database_name=database_name, database_user=database_user,
    )
    update_wiring(directory, {
        "DAYLOOM_APP_IMAGE": app_image, "DAYLOOM_BASELINE_IMAGE": baseline_image,
        "DAYLOOM_BASELINE_ID": baseline_id, "DAYLOOM_RUN_UID": uid, "DAYLOOM_RUN_GID": gid,
        "DAYLOOM_HOST_PORT": urlsplit(origin).port or 80, "COMPOSE_PROJECT_NAME": project,
    }, origin=origin)
    return result


def configure_providers(directory):
    directory = Path(directory)
    manager = LocalConfiguration(directory, origin="http://localhost", environment={})
    changes = {}
    for key in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY",
                "OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "UNSPLASH_API_KEY"):
        prompt = key + " (blank keeps saved value): "
        value = getpass.getpass(prompt) if key.endswith("KEY") else input(prompt)
        if value:
            changes[key] = value
    manager.save(manager.view()["revision"], changes)
    return {"saved": True, "restart_required": True}


def set_management_peers(directory, peers):
    from ipaddress import ip_address

    addresses = [str(ip_address(peer.strip())) for peer in peers.split(",") if peer.strip()]
    if not addresses:
        raise ValueError("An explicit forwarding peer is required")
    update_wiring(directory, {"DAYLOOM_MANAGEMENT_PEERS": ",".join(addresses)})
    return {"management_peers": addresses}


def prepare_logs(directory, uid, gid):
    path = Path(directory)
    if path.resolve() != Path("/opt/dayloom/logs") or path.is_symlink():
        raise ValueError("Only the application's dedicated log mount can be prepared")
    path.mkdir(exist_ok=True)
    os.chown(path, uid, gid)
    os.chmod(path, 0o700)
    return {"logs_prepared": True}


def deployment_status(directory):
    directory = Path(directory)
    manager = LocalConfiguration(directory, origin="http://localhost", environment={})
    readiness = manager.readiness()
    return {"setup_required": not readiness["ready"], "missing": readiness["missing"],
            "resources": readiness["resources"], "credentials_verified": False}
