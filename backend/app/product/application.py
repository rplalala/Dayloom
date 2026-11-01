"""Same-origin delivery of the built React application and unmodified real APIs."""

import re
from pathlib import Path

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from backend.app.main import create_app

FRONTEND_DIRECTORY = Path(__file__).resolve().parents[3] / "frontend" / "dist"


class ProductFrontend(StaticFiles):
    async def get_response(self, path, scope):
        path = path.replace("\\", "/").lstrip("/")
        # Missing APIs and assets must retain their HTTP failure rather than return HTML.
        if path.split("/", 1)[0] in {"api", "health", "docs", "redoc", "openapi.json"}:
            raise HTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if (
                error.status_code != 404
                or scope["method"] not in {"GET", "HEAD"}
                or path.split("/", 1)[0] in {"assets", "dayloom"}
                or "." in Path(path).name
            ):
                raise
            response = await super().get_response("index.html", scope)
        if response.media_type == "text/html":
            response.headers["Cache-Control"] = "no-cache"
        elif re.fullmatch(r"dayloom/examples/[a-z-]+-[0-9a-f]{12}\.(?:jpg|svg)", path):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def create_product_application(frontend_directory: Path = FRONTEND_DIRECTORY):
    """Use the normal provider wiring; no test factory or dependency override is installed."""
    if not (frontend_directory / "index.html").is_file():
        raise ValueError("Build the frontend first: npm --prefix frontend run build")
    application = create_app()
    application.mount("/", ProductFrontend(directory=frontend_directory, html=True))
    return application
