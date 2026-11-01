"""Candidate-image preflight: installed resources first, then supported migrations."""

import argparse
import json
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-id")
    parser.add_argument("--check-local-target", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_local_target:
            from dotenv import dotenv_values

            from backend.app.runtime.configuration_paths import configuration_directory
            from backend.app.runtime.database import DatabaseSettings

            settings = DatabaseSettings()
            values = dotenv_values(configuration_directory() / ".env", interpolate=False)
            if (
                settings.url is not None
                or settings.host != "postgres"
                or settings.port != 5432
                or settings.name != values.get("DAYLOOM_DB_NAME")
                or settings.user != values.get("DAYLOOM_DB_USER")
            ):
                print(
                    "Maintenance requires this Compose project's postgres service and split "
                    "connection fields. External/URL database configurations are preserved "
                    "and require an explicitly separate backup procedure.",
                    file=sys.stderr,
                )
                return 2
            print(json.dumps({"status": "local-target"}))
            return 0
        if not args.baseline_id:
            parser.error("--baseline-id is required for candidate compatibility")
        from backend.app.product.local_readiness import check_local_resources
        from deploy.docker.startup import prepare_database

        # These probes read local files/database only; no provider client sends requests.
        resources = check_local_resources()
        failed = [item["id"] for item in resources if not item["ready"]]
        if failed:
            print(
                "Candidate local resources are incompatible: "
                + ", ".join(failed)
                + ". Keep the installed image and private backup; corpus replacement "
                + "requires a separate migration.",
                file=sys.stderr,
            )
            return 2
        prepare_database(args.baseline_id, 30)
        print(json.dumps({"status": "compatible", "providers_checked": False}))
        return 0
    except Exception:
        print(
            "Candidate installation/migration contract rejected. Preserve the backup; "
            "recover the pre-upgrade database/configuration if required.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
