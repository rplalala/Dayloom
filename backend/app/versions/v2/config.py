"""Independent V2 work limits; these never enlarge main or Nearby capacities."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RAGConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    version: Literal["tripworld_runtime_1"] = "tripworld_runtime_1"
    max_queries: int = Field(default=2, ge=1, le=8)
    max_positions: int = Field(default=20, ge=1, le=240)
    total_query_tokens: int = Field(default=1024, ge=1, le=4096)
    top_k: int = Field(default=10, ge=1, le=30)
    resolution_entities: int = Field(default=6, ge=0, le=60)
    details_calls: int = Field(default=8, ge=0, le=60)
    fallback_calls: int = Field(default=2, ge=0, le=8)
    radius_km: Literal[15] = 15
    identity_radius_km: Literal[1] = 1
    deadline_seconds: float = Field(default=30, gt=0, le=600)
    embedding_timeout: float = Field(default=8, gt=0, le=20)
    sql_timeout: float = Field(default=3, gt=0, le=120)
    connect_timeout: float = Field(default=10, gt=0, le=20)
    google_timeout: float = Field(default=4, gt=0, le=10)
    retries: Literal[0] = 0

    @model_validator(mode="after")
    def coordinated_limits(self):
        if self.max_queries * self.top_k > self.max_positions:
            raise ValueError("Query result positions exceed processing capacity")
        if self.max_queries * 512 > self.total_query_tokens:
            raise ValueError("Query token budget must support the configured query count")
        return self
