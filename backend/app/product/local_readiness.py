"""Read-only local resource probes; never contact model, map or image providers."""

import asyncio


def check_local_resources(*, remote_database=False):
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
        from backend.app.runtime.event_loop import create_api_loop
        from backend.app.tripworld.retrieval.runtime import RuntimeRetrieval

        async def prepare():
            config = load_product_runtime_config().tripworld_discovery
            async with RuntimeRetrieval(config) as runtime:
                await runtime.prepare()

        asyncio.run(prepare(), loop_factory=create_api_loop)

    def remote_migrations():
        from backend.app.product.database import check_migrations

        check_migrations(DatabaseSettings().connection_parameters())

    results = []
    for name, probe in (
        ("product_settings", ProductSettings),
        ("remote_database" if remote_database else "database", lambda: database("SELECT 1")),
        (("remote_migrations", remote_migrations) if remote_database else
         ("migrations", lambda: database("SELECT 1 FROM app.schema_migrations LIMIT 1"))),
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
