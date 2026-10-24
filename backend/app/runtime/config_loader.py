"""Load an explicitly selected, complete non-secret runtime policy."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import yaml
from yaml.constructor import ConstructorError

from backend.app.runtime.config_models import RuntimeConfig

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_CONFIG_PATH = PROJECT_ROOT / "config" / "runtime.yaml"


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Keep SafeLoader semantics but reject silently overwritten YAML keys."""

    def construct_mapping(self, node, deep=False):
        seen: set[object] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise ConstructorError(
                    None, None, f"Duplicate YAML key: {key}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


@lru_cache(maxsize=1)
def load_runtime_config() -> RuntimeConfig:
    """Read the committed policy independently of the shell working directory."""

    return load_runtime_config_file(DEFAULT_RUNTIME_CONFIG_PATH)


def load_runtime_config_file(path: Path) -> RuntimeConfig:
    """Read one explicit YAML file; primarily used by deterministic tests."""

    document = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeySafeLoader)
    return RuntimeConfig.model_validate(document)


@lru_cache(maxsize=2)
def load_runtime_profile(profile: str) -> RuntimeConfig:
    """Select a complete policy; independent runners retain development by default."""
    if profile == "development":
        return load_runtime_config()
    if profile == "acceptance":
        return load_runtime_config_file(PROJECT_ROOT / "config" / "runtime.acceptance.yaml")
    raise ValueError("Unknown runtime resource profile")


def load_product_runtime_config() -> RuntimeConfig:
    from backend.app.runtime.deployment import ProductPolicySettings

    return load_runtime_profile(ProductPolicySettings().runtime_profile)


def resolve_trace_directory(directory: Path) -> Path:
    """Resolve relative trace paths against the repository root."""

    return directory if directory.is_absolute() else PROJECT_ROOT / directory


def runtime_config_snapshot(
    config: RuntimeConfig,
    *,
    effective_budget: dict[str, int] | None = None,
) -> tuple[dict[str, object], str]:
    """Return only allowlisted non-secret policy and its stable SHA-256 digest."""

    snapshot = config.model_dump(mode="json")
    if effective_budget is not None:
        snapshot["effective_tool_budget"] = effective_budget
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return snapshot, hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def tool_limits(config):
    """Build limits only from the explicitly selected immutable configuration."""
    from backend.app.runtime.budget import ToolBudgetLimits

    return ToolBudgetLimits.model_validate(
        {
            **{f"max_{key.value}": value for key, value in config.budget.as_key_limits().items()},
            "max_baseline_route_matrix_elements_per_request": (
                config.budget.routes.baseline_elements_per_request
            ),
        }
    )
