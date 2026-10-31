"""Read-only local resource probes; never contact model, map or image providers."""

import asyncio


def check_local_resources():
    from backend.app.product.settings import ProductSettings
    from backend.app.runtime.database import DatabaseSettings

    def database(query):
        import psycopg

        parameters = DatabaseSettings().connection_parameters()
        parameters.update(
            connect_timeout=3,
            options=(
                parameters.get("options", "")
                + " -c default_transaction_read_only=on -c statement_timeout=3000"
            ),
        )
        with psycopg.connect(**parameters) as connection:
            connection.execute(query)

    def tokenizers():
        from backend.app.runtime.token_counting import tokenizer
        from backend.app.tripworld.retrieval.query_tokens import tokenizer as embedding_tokenizer

        tokenizer()
        embedding_tokenizer()

    def retrieval():
        from backend.app.runtime.config_loader import load_product_runtime_config
        from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval
        from scripts.run_api import create_api_loop

        async def prepare():
            config = load_product_runtime_config().tripworld_discovery
            async with RuntimeRetrieval(config) as runtime:
                await runtime.prepare()

        asyncio.run(prepare(), loop_factory=create_api_loop)

    results = []
    for name, probe in (
        ("product_settings", ProductSettings),
        ("database", lambda: database("SELECT 1")),
        ("migrations", lambda: database("SELECT 1 FROM app.schema_migrations LIMIT 1")),
        ("tokenizers", tokenizers),
        ("tripworld", retrieval),
    ):
        try:
            probe()
            ready = True
        except Exception:
            ready = False  # Provider/DB errors may contain credentials; return status only.
        results.append({"id": name, "ready": ready})
    return results
