"""Provider-free complete database export, verification and initialization CLI."""

import argparse
import json
import sys

from deploy.release.baseline_artifact import BaselineError, verify_release


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("directory")
    verify.add_argument("--expect-id")
    export = commands.add_parser("export")
    export.add_argument("--output", required=True)
    export.add_argument("--runtime-root", required=True)
    export.add_argument("--source-revision", required=True)
    export.add_argument("--notice", action="append", default=[])
    export.add_argument("--dsn-env", default="DAYLOOM_DB_URL")
    restore = commands.add_parser("restore")
    restore.add_argument("directory")
    restore.add_argument("--expect-id")
    restore.add_argument("--dsn-env", default="DAYLOOM_DB_URL")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--dsn-env", default="DAYLOOM_DB_URL")
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_release(args.directory, args.expect_id)
        else:
            from deploy.release.baseline_database import connect, connection_parameters, inventory
            from deploy.release.baseline_operations import export_baseline, restore_baseline
            parameters = connection_parameters(args.dsn_env)
            if args.command == "export":
                result = export_baseline(args.output, args.runtime_root, args.source_revision,
                                         args.notice, parameters)
            elif args.command == "restore":
                result = restore_baseline(args.directory, parameters, args.expect_id)
            else:
                with connect(parameters) as connection, connection.transaction():
                    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    result = inventory(connection)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        # Driver/client diagnostics may embed secrets, filenames or private row values.
        message = str(error) if isinstance(error, BaselineError) else "Baseline operation failed"
        print(message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
