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
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=5173)
    serve.add_argument("--management-peer", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        values = vars(args)
        command = values.pop("command")
        if command == "serve":
            from scripts.run_product import main as run_product

            peers = args.management_peer or [
                peer.strip() for peer in os.environ.get("DAYLOOM_MANAGEMENT_PEERS", "").split(",")
                if peer.strip()
            ]
            arguments = ["--container-local", "--host", args.host, "--port", str(args.port)]
            for peer in peers:
                arguments.extend(["--management-peer", peer])
            run_product(arguments)
        elif command == "reset-management-password":
            print(json.dumps(reset_management_password(**values)))
        else:
            print(json.dumps(bootstrap_instance(**values)))
        return 0
    except Exception as error:
        message = "Instance command failed (" + type(error).__name__ + ")."
        print(message + " Check private configuration.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
