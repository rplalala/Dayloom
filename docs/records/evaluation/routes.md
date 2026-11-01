# Independent route engineering evidence

October 2026 work separated submitted transport, physical venue association, coordinates,
provider support and feasibility. Current semantics belong to the
[opening/route contract](../../contracts/0004-opening-routes.md). Historical UNKNOWN
means insufficient applicable evidence, not feasibility or infeasibility. Source outputs
were never retimed to improve results; local paths below identify private evidence.

## Offline scorer and coordinate boundary

The 2–3 October implementation scored directed same-day primary pairs against original
reserved time, fixed/protected deadlines and mode caps. Review corrected exact hard
boundaries, unresolved populations understating burden and using disconnected free spans.
Independent snapshots supplied coordinates without letting planner caches become truth.
Malformed `places:null` search material was handled explicitly. Initial scorer/CLI fixes
passed 86 route checks; later full backend after the separate timeout-test repair passed
2,234 with ten skips. These checkpoints overlap and have different revisions.

## Seoul acquisition and identity diagnosis

On 5 October, revision `0f0120dc63ac25b492fd5d474c1d04826c5ab22f`, nine searches returned
HTTP 200 in 3.328s, with no Details/routes/model/retries. No reference reached automatic
adoption: two required review and seven had malformed-address diagnostics. Repeated
numbered Korean sublocalities shared broad types, while one component had no types.
The parser's uniqueness assumption was too restrictive; this did not prove wrong venues.
Four route verdicts stayed UNKNOWN. Reference consumption was USD 0.315, not an invoice.
Evidence: `artifacts/v0-route-execution-20261005/`.

A separate one-send identity-assistance pilot used nine references/fourteen candidate
occurrences and existing facts. It completed in 6.094s with 4,213 input/1,007 output tokens;
all nine supplied matches agreed with an independently recorded agent field assessment.
This was consistency between agents, not human gold or measured accuracy. Historical
adoption retained high-impact/review boundaries and explicit legacy replay.

## Korean provider support

By 7 October, current correspondence established eight visits plus one requirement,
with independent coordinates for all four legs. Three WALK legs remained region-blocked
and TRANSIT conditional. Ready budget was USD 0; four unready queries were hypothetical
USD 0.02, not authorized evidence. All route verdicts stayed UNKNOWN despite identity readiness.

The documentation-only review at `49a6fef135945e3612722a10b4394e6afe49d846` considered
Kakao, TMAP, ODsay and Naver. It identified differences in mode support, departure-time
semantics and units; none became an adapter or supplied new route facts. Displayed
computed times were not timetable routing. No coordinate, mode, date or provider substitution
was made. Evidence: `artifacts/v0-route-requests-86-20261007/`.

## Australian preparation

Australian WALK readiness required current identities, independent coordinates and a
continuous free span. Repeated occurrence legs retained their population while duplicate
provider queries shared allowance. Development request preparation moved into
`backend/evaluation/tools/`, preserving planner-free ordinary scorers. At
`2a2b1e1a04a052b84ff51911871486a41af307d7`, affected checks passed 109 and a separate
full backend passed 3,017 with ten skips.

The first Sydney packet included an exact-two daily request that was only producer-prepared
wording. It was removed before the later natural-input generation; the old packet remained
historical evidence rather than becoming user intent. See [generation evidence](../v0-v3/development-pilots.md).

## Sydney acquisition and physical follow-up

On 8 October, `8b70852431631f32a87c2c49bd0838c2570f38b4`, six Details and two Matrix
sends completed with HTTP 200, no retries, USD 0.130 reference cost. Four opening checks
passed; Opera House/Powerhouse lacked usable periods, and Australian Museum was initially
unqueried because grounding failed. WALK observations of 893s/1,108m and 1,083s/1,384m fit
the original 20-minute intervals. The Museum→QVB leg remained unqueried.

After physical-association correction, original Museum address grounding stayed FAIL while
its independent physical ID could support downstream checks. At
`3f608c7a76be31054cdfd18ab088eec47399c64f`, two incremental HTTP 200 sends in 1.046s
cost reference USD 0.025. Museum hours passed using weaker regular fallback and WALK to
QVB was 562s/678m within 1,200s. Combined opening was five PASS/two UNKNOWN; the three
evaluable routes passed. An unnamed generic-food journey stayed unbound, and exact-once
Opera House/non-overlap still had unresolved scope.

Collector review corrected swallowed timeout and phase-only HTTP bounds: a whole-request
stopping exception prevented a second send after timeout. Existing public checks passed 69;
no new full backend run was claimed. All 240 protected hashes and eight reused observations
remained exact. Evidence: `artifacts/sydney-v0-museum-followup-20261008/`.

## Interpretation limits

These single-source diagnostics did not qualify four-version quality intake: the native
consumer correctly rejected missing companion versions. Time-independent WALK is not a
future-conditions guarantee, regular hours are weaker than applicable current periods,
and physical association does not repair grounding FAIL. Later complete four-final
integration belongs to the [intake record](intake-identity-usage.md).
