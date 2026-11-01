# Opt-in attempt usage capture

Capture is owned by the selected-run producer. The opt-in
[development CLI](../../../docs/guides/experiments.md#generate-v0v3-outputs) wraps the existing
request runtime, including dependency setup and cleanup. Product APIs and existing runner
scripts retain their current behavior. A custom producer can wrap its already authorized
selected-version invocation and client cleanup:

```python
from backend.app.observability.usage_capture import capture_attempt

usage_records = []
result = await capture_attempt(
    invoke_selected_version,  # zero-argument async callable
    group_id=group_id,
    run_id=run_id,
    version="v3",
    sink=usage_records.append,
    cleanup=close_caller_owned_clients,  # omit when invoke already owns cleanup
    serialize=lambda result: result.model_dump_json(indent=2, ensure_ascii=True).encode("utf-8"),
    adapter_coverage="default_adapters",
)
```

Save the result using the identical serializer/bytes, and save the envelope as the selected version's usage file. Never reconstruct missing token data from text length. For failures, the sink still receives an unlinked failure envelope; keep that in the benchmark attempt ledger, not a qualified evaluation group. Do not invoke this example without separate live-run authorization.

The default adapter_coverage is unverified. Only declare default_adapters when using the instrumented Foundry/LangChain, official Responses, retrieval embedding, JSON/page HTTP and request-cache paths. Injected fakes or external clients do not automatically produce complete usage. Use a supplied UsageLedger to inspect diagnostics if a sink may fail. A sink error cannot override a planner result or primary exception.

The common timer includes invoke and cleanup, excluding serializer/sink and anything constructed before invoke. Prefer a callable that owns dependency creation and disposal consistently across versions. Existing PlannerRuntime.run already performs cleanup. V3's final request_resources remains in the untouched returned result.

Model observations use provider usage only. HTTP events count transport attempts, not billing; no-response events remain incomplete. Model SDK sends are included in total HTTP observations and can be separated by operation; do not add model event counts to HTTP counts as a single billable number. Cache lookup hits and actual get_or_create reuse are reported separately. Repair is a subset of event IDs, not an extra total. Inclusive stage timings may overlap; unattributed work is explicit.

For researcher-facing offline comparisons:

```powershell
uv run rtpeval usage v0_usage.json v1_usage.json v2_usage.json v3_usage.json
```

The report is descriptive, preserves request pairing/missingness and contributes no quality score. It is not displayed to blinded raters. Independent oracle usage uses a separate namespace and ledger; native oracle snapshots
can be normalized by the offline cost-report command.

Reported `cache_write_input_tokens` supplements cached reads and reasoning tokens.
`usage_details` preserves allowlisted nonnegative numeric provider fields, excluding
private text. Cache reads and writes partition input; reasoning partitions output and
carries no additional output charge. Missing cache quantities remain absent/null in usage.
A price snapshot can explicitly request conservative missing-cache estimation; those
assumptions appear in cost-report pricing and preserve the captured envelope.
