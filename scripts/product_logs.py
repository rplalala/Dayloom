"""Read or expire local Product diagnostics without accessing providers or the database."""

import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.observability.product_logs import ProductLogs, ProductLogSettings  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", type=UUID)
    parser.add_argument("--run-id", type=UUID)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument(
        "--prune", action="store_true", help="Apply retention to finished Product runs"
    )
    args = parser.parse_args(argv)
    try:
        settings = ProductLogSettings(**({"directory": args.directory} if args.directory else {}))
        logs = ProductLogs(settings)
        if args.prune:
            logs.prune()
            if logs.failed:
                return 1
        for row in logs.read(
            task_id=str(args.task_id) if args.task_id else None,
            run_id=str(args.run_id) if args.run_id else None,
            summaries_only=args.summary,
        ):
            print(json.dumps(row, ensure_ascii=True))
        return 0
    except Exception as error:
        print(
            "Product diagnostics could not be read (" + type(error).__name__ + ").", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
