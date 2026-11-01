# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim@sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY backend/app/product/examples/ /build/backend/app/product/examples/
COPY backend/app/product/example_media.json /build/backend/app/product/example_media.json
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.12.13@sha256:b485bd65cc2cf1c9a93b3554012c9c3778cf7b1b5fd3d3096ce9e1226c97e1e6 AS uv

FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3 AS runtime
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/rplalala/Dayloom" \
      org.opencontainers.image.revision=$SOURCE_REVISION
COPY --from=uv /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    DAYLOOM_CONFIG_DIR=/instance \
    PRODUCT_LOG_DIRECTORY=/opt/dayloom/logs/product \
    PATH=/opt/dayloom/.venv/bin:$PATH
WORKDIR /opt/dayloom
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --group retrieval --no-install-project
COPY backend/ backend/
COPY scripts/ scripts/
COPY tools/ tools/
COPY config/ config/
COPY deploy/ deploy/
COPY product.example.yaml ./
COPY data/tripworld/ data/tripworld/
COPY --from=frontend /build/frontend/dist frontend/dist/
COPY --from=runtime-resources /.cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790 .cache/tokenizer/fb374d419588a4632f3f557e76b4b70aebbca790
COPY --from=runtime-resources /data/tripworld/tokenizer_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4 data/tripworld/tokenizer_cache/9b5ad71b2ce5302211f9c61530b329a4922fc6a4
COPY --from=runtime-resources /data/tripworld/artifacts/retrieval_entities.parquet.manifest.json data/tripworld/artifacts/retrieval_entities.parquet.manifest.json
COPY --from=runtime-resources /data/tripworld/reports/phase5_embedding_run.json data/tripworld/reports/phase5_embedding_run.json
RUN uv sync --locked --no-dev --group retrieval \
    && dayloom tokenizers --offline \
    && groupadd --gid 1000 dayloom \
    && useradd --uid 1000 --gid 1000 --no-create-home dayloom \
    && mkdir -p /instance /opt/dayloom/logs \
    && chown dayloom:dayloom /instance /opt/dayloom/logs
USER 1000:1000
EXPOSE 5173
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5173/health', timeout=3)"]
ENTRYPOINT ["python", "-m", "deploy.docker.app_entrypoint"]
CMD ["serve"]
