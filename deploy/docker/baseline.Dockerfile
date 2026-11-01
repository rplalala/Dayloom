# syntax=docker/dockerfile:1
FROM pgvector/pgvector:0.8.2-pg17@sha256:feb68f4f15446397d8cac7f4fe48fe4586de83160d1fc48b46283312d1a33966 AS tools
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-psycopg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/dayloom
COPY deploy/__init__.py deploy/__init__.py
COPY deploy/release/ deploy/release/
ENTRYPOINT ["python3", "-m", "deploy.release.baseline"]

FROM tools AS test
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-pytest \
    && rm -rf /var/lib/apt/lists/*

FROM tools AS baseline
COPY --from=baseline-data / /baseline/
RUN python3 -m deploy.release.baseline verify /baseline
# Keep release metadata after the large immutable data layer.
ARG SOURCE_REVISION=unknown
ARG BASELINE_VERSION=unreleased
ARG BASELINE_ID=unreleased
LABEL org.opencontainers.image.source="https://github.com/rplalala/Dayloom" \
      org.opencontainers.image.revision=$SOURCE_REVISION \
      org.opencontainers.image.version=$BASELINE_VERSION \
      io.dayloom.baseline.id=$BASELINE_ID
CMD ["restore", "/baseline"]
