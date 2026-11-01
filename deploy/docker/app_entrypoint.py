"""Explicit host-controlled setup and application-container startup."""

import argparse
import json
import os
import sys

from deploy.docker.instance import bootstrap_instance, reset_management_password


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("--directory", required=True)
    bootstrap.add_argument("--origin", default="http://localhost:5173")
    bootstrap.add_argument("--database-host", default="postgres")
    bootstrap.add_argument("--database-port", type=int, default=5432)
    bootstrap.add_argument("--database-name", default="dayloom")
    bootstrap.add_argument("--database-user", default="dayloom")
    reset = commands.add_parser("reset-management-password")
    reset.add_argument("--directory", required=True)
    prepare = commands.add_parser("prepare", parents=[], add_help=True)
    prepare.add_argument("--directory", required=True)
    prepare.add_argument("--origin", required=True)
    prepare.add_argument("--app-image", required=True)
    prepare.add_argument("--baseline-image", required=True)
    prepare.add_argument("--baseline-id", required=True)
    prepare.add_argument("--uid", type=int, required=True)
    prepare.add_argument("--gid", type=int, required=True)
    prepare.add_argument("--project", required=True)
    prepare.add_argument("--database-name", default="dayloom")
    prepare.add_argument("--database-user", default="dayloom")
    probe = commands.add_parser("probe-directory")
    probe.add_argument("--directory", required=True)
    peers = commands.add_parser("set-management-peers")
    peers.add_argument("--directory", required=True)
    peers.add_argument("--peers", required=True)
    providers = commands.add_parser("configure-providers")
    providers.add_argument("--directory", required=True)
    status = commands.add_parser("status")
    status.add_argument("--directory", required=True)
    logs = commands.add_parser("prepare-logs")
    logs.add_argument("--directory", default="/opt/dayloom/logs")
    logs.add_argument("--uid", type=int, required=True)
    logs.add_argument("--gid", type=int, required=True)
    check = commands.add_parser("check-installation")
    check.add_argument("--baseline-id", required=True)
    check.add_argument("--startup-timeout", type=float, default=30)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=5173)
    serve.add_argument("--management-peer", action="append", default=[])
    serve.add_argument("--require-installation", action="store_true")
    serve.add_argument("--baseline-id", default=os.environ.get("DAYLOOM_BASELINE_ID", ""))
    serve.add_argument("--startup-timeout", type=float, default=1800)
    args = parser.parse_args(argv)
    try:
        values = vars(args)
        command = values.pop("command")
        if command == "serve":
            from scripts.run_product import main as run_product

            if args.require_installation or args.baseline_id:
                from deploy.docker.startup import prepare_database

                prepare_database(args.baseline_id, args.startup_timeout)
            peers = args.management_peer or [
                peer.strip() for peer in os.environ.get("DAYLOOM_MANAGEMENT_PEERS", "").split(",")
                if peer.strip()
            ]
            arguments = ["--container-local", "--host", args.host, "--port", str(args.port)]
            for peer in peers:
                arguments.extend(["--management-peer", peer])
            run_product(arguments)
        elif command == "check-installation":
            from deploy.docker.startup import prepare_database

            prepare_database(args.baseline_id, args.startup_timeout)
            print(json.dumps({"installed": True}))
        elif command == "reset-management-password":
            print(json.dumps(reset_management_password(**values)))
        elif command == "probe-directory":
            from pathlib import Path

            info = Path(args.directory).stat()
            print(str(info.st_uid) + ":" + str(info.st_gid))
        elif command in {"prepare", "set-management-peers", "configure-providers",
                         "prepare-logs", "status"}:
            from deploy.docker import launch_settings

            actions = {"prepare": launch_settings.prepare_deployment,
                       "set-management-peers": launch_settings.set_management_peers,
                       "configure-providers": launch_settings.configure_providers,
                       "prepare-logs": launch_settings.prepare_logs,
                       "status": launch_settings.deployment_status}
            print(json.dumps(actions[command](**values)))
        else:
            print(json.dumps(bootstrap_instance(**values)))
        return 0
    except Exception as error:
        message = "Instance command failed (" + type(error).__name__ + ")."
        print(message + " Check private configuration.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
