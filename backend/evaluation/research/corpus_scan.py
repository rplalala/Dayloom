"""Compatible saved entity artifacts and production eligibility observations."""

from backend.app.tripworld.database.policy import POLICY_VERSION, exclusion_reasons, text_hash
from backend.app.tripworld.retrieval.entities import RetrievalEntity
from backend.app.tripworld.retrieval.geography import haversine_km
from backend.cli.collection import _json, _require


def dataset_rows(request, sources, manifest):
    source = request["source"]
    raw = sources.read_bytes(source["dataset_ref"])
    if source["dataset_ref"].get("media_type") == "application/vnd.apache.parquet":
        from pyarrow import BufferReader
        from pyarrow.parquet import ParquetFile

        data = ParquetFile(BufferReader(raw))
        _require(data.metadata.num_rows == manifest["entity_count"], "Dataset row count drift")
        rows = (
            row
            for batch in data.iter_batches(
                batch_size=request["measurement_configuration"]["batch_size"]
            )
            for row in batch.to_pylist()
        )
    else:
        value = _json(raw)
        _require(
            value.get("schema_version") == "rtpeval_corpus_entities_1"
            and isinstance(value.get("entities"), list),
            "Compatible saved entities required",
        )
        _require(len(value["entities"]) == manifest["entity_count"], "Dataset row count drift")
        rows = iter(value["entities"])
    index = sources.read_ref(source["embedding_index_ref"])
    hashes = set(index["text_hashes"])
    for row in rows:
        entity = RetrievalEntity.model_validate(row)
        yield {
            "entity": entity.model_dump(mode="json"),
            "artifact_hash": request["snapshot_identity"]["artifact_sha256"],
            "policy_version": POLICY_VERSION,
            "text_hash": text_hash(entity.retrieval_text),
            "discovery_allowed": not exclusion_reasons(entity),
            "has_embedding": text_hash(entity.retrieval_text) in hashes,
        }


def eligible(observation, request, manifest):
    entity = RetrievalEntity.model_validate(observation["entity"])
    _require(
        observation.get("artifact_hash") == request["snapshot_identity"]["artifact_sha256"]
        and observation.get("policy_version") == POLICY_VERSION,
        "Measured entity snapshot/policy drift",
    )
    for field, expected in manifest["inputs"].items():
        if field in (
            "tripworld_revision",
            "semantic_mapping_version",
            "retrieval_entity_builder_version",
            "retrieval_text_template_version",
        ):
            _require(
                getattr(entity, field) == expected,
                "Measured entity/manifest version mismatch: " + field,
            )
    allowed = not exclusion_reasons(entity)
    _require(
        type(observation.get("has_embedding")) is bool
        and type(observation.get("discovery_allowed")) is bool,
        "Explicit entity eligibility/embedding observation required",
    )
    _require(
        observation["discovery_allowed"] == allowed
        and observation.get("text_hash") == text_hash(entity.retrieval_text),
        "Measured production eligibility/text drift",
    )
    if not allowed or not observation["has_embedding"]:
        return False
    latitude, longitude = entity.latitude, entity.longitude
    if latitude is None or longitude is None:
        return False
    scope = request["scope"]
    if scope["kind"] == "bounding_box":
        return (
            scope["south"] <= latitude <= scope["north"]
            and scope["west"] <= longitude <= scope["east"]
        )
    return (
        haversine_km(scope["latitude"], scope["longitude"], latitude, longitude) * 1000
        <= scope["radius_m"] + 1e-6
    )
