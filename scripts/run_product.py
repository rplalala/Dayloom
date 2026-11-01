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
    from backend.app.runtime.event_loop import create_api_loop
    from backend.app.runtime.token_counting import tokenizer
    from backend.app.tripworld.retrieval.query_tokens import tokenizer as embedding_tokenizer
    from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval
    from backend.app.versions.v1.config import V1Settings

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
    from backend.app.product.configuration import FIELDS, LocalConfiguration
    from backend.app.product.configuration_api import enable_local_configuration
    from backend.app.runtime.deployment import ProductPolicySettings
    from backend.app.runtime.event_loop import create_api_loop

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument(
        "--check", action="store_true", help="Check local readiness without live calls"
    )
    args = parser.parse_args(argv)
    os.chdir(PROJECT_ROOT)
    external_environment = dict(os.environ)
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    manager = None
    try:
        application = create_product_application()
        policy = ProductPolicySettings()
        origin = urlsplit(policy.origin)
        expected_port = origin.port or (443 if origin.scheme == "https" else 80)
        if origin.scheme == "http" and expected_port != args.port:
            parser.error("The listening port must match product.yaml origin or PRODUCT_ORIGIN")
        if (args.host in {"127.0.0.1", "localhost", "::1"}
                and origin.scheme == "http"
                and origin.hostname in {"localhost", "127.0.0.1", "::1"}):
            manager = LocalConfiguration(
                PROJECT_ROOT, origin=policy.origin, environment=external_environment,
            )
            # Pin editable fields, including missing values, until process restart.
            # Existing settings readers must not pick up partially applied edits.
            for key in list(os.environ):
                if key.upper() in FIELDS:
                    del os.environ[key]
            os.environ.update(manager.initial)
        try:
            check_runtime()
            ready = True
        except Exception:
            if args.check or manager is None:
                raise
            ready = False
        if manager is not None:
            enable_local_configuration(application, manager, ready=ready)
    except ValidationError as error:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in error.errors())
        raise SystemExit("Invalid runtime configuration fields: " + fields) from None
    except Exception as error:
        # Database/provider errors may embed credentials; never print their representations.
        raise SystemExit(
            "Product local readiness failed (" + type(error).__name__ + "). "
            "Check frontend build, Product migrations, provider settings and TripWorld resources."
        ) from None
    if ready:
        print("Local Product resources ready; real providers configured; no live calls performed.")
    else:
        print("Local setup required. Open " + manager.origin + "/config to configure providers "
              "and inspect local resources.")
    if args.check:
        return
    import uvicorn

    print("Dayloom: " + policy.origin)
    if manager is not None:
        print("Local configuration: " + manager.origin + "/config")
        print("Configuration access: " + (
            "password verification enabled." if manager.access_view()["password_required"]
            else "opens directly; optional password verification is available on the page."
        ))
    server = uvicorn.Server(uvicorn.Config(
        application, host=args.host, port=args.port, proxy_headers=False,
    ))
    asyncio.run(server.serve(), loop_factory=create_api_loop)


if __name__ == "__main__":
    main()
