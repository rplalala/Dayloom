"""Serve the built Dayloom frontend and real API together from the local runtime database."""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_runtime():
    """Check local resources only; never call a model, embedding or other external service."""
    import psycopg

    from backend.app.product.settings import ProductSettings
    from backend.app.runtime.config_loader import load_runtime_config
    from backend.app.runtime.token_counting import tokenizer
    from backend.app.tripworld.retrieval.query_tokens import tokenizer as embedding_tokenizer
    from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval
    from backend.app.versions.v1.config import V1Settings
    from scripts.run_api import create_api_loop

    settings = ProductSettings()
    V1Settings()
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("Set OPENAI_API_KEY for live query embeddings")
    tokenizer()
    embedding_tokenizer()
    with psycopg.connect(
        settings.database_url.get_secret_value(), connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=5000",
    ) as connection:
        connection.execute("SELECT 1 FROM app.schema_migrations LIMIT 1")

    async def check_retrieval():
        async with RuntimeRetrieval(load_runtime_config().tripworld_discovery) as retrieval:
            await retrieval.prepare()

    asyncio.run(check_retrieval(), loop_factory=create_api_loop)
    return settings


def main(argv=None):
    from dotenv import load_dotenv
    from pydantic import ValidationError

    from backend.app.product.application import create_product_application
    from scripts.run_api import create_api_loop

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument(
        "--check", action="store_true", help="Check local readiness without live calls"
    )
    args = parser.parse_args(argv)
    os.chdir(PROJECT_ROOT)
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    load_dotenv(PROJECT_ROOT / ".env.tripworld", override=False)
    try:
        application = create_product_application()
        settings = check_runtime()
        origin = urlsplit(settings.origin)
        expected_port = origin.port or (443 if origin.scheme == "https" else 80)
        if origin.scheme == "http" and expected_port != args.port:
            parser.error("The listening port must match PRODUCT_ORIGIN")
    except ValidationError as error:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in error.errors())
        raise SystemExit("Invalid runtime configuration fields: " + fields) from None
    except Exception as error:
        # Database/provider errors may embed credentials; never print their representations.
        raise SystemExit(
            "Product local readiness failed (" + type(error).__name__ + "). "
            "Check frontend build, Product migrations, provider settings and TripWorld resources."
        ) from None
    print("Local Product resources ready; real providers configured; no live calls performed.")
    if args.check:
        return
    import uvicorn

    print("Dayloom: " + settings.origin)
    server = uvicorn.Server(uvicorn.Config(application, host=args.host, port=args.port))
    asyncio.run(server.serve(), loop_factory=create_api_loop)


if __name__ == "__main__":
    main()
