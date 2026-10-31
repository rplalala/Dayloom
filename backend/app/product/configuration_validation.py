"""Shared endpoint admission for local configuration editing and API probes."""

from urllib.parse import urlsplit


def supported_foundry_endpoint(value: str) -> bool:
    try:
        url = urlsplit(value)
        return bool(
            url.scheme == "https"
            and url.hostname
            and url.hostname.endswith(
                (
                    ".openai.azure.com",
                    ".services.ai.azure.com",
                    ".cognitiveservices.azure.com",
                )
            )
            and url.port in (None, 443)
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and url.path.rstrip("/") == "/openai/v1"
        )
    except ValueError:
        return False
