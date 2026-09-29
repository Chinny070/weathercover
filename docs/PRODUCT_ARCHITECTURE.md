# WeatherResolve + WeatherCover — Product Architecture

Network target: **GenLayer StudioNet only** (chain ID 61999, RPC `https://studio.genlayer.com/api`). No multi-network support in this design.

---

## 1. Architecture Summary

Two contracts, two layers:

- **WeatherResolve** — reusable infrastructure. Owns a canonical Weather Event Registry, a set of versioned Source Policies, an evidence-retrieval/resolution algorithm built on `gl.nondet.web.*`, and a Finalized Observation Registry. Exposes a read/consumer interface.
- **WeatherCover** — first consumer. Holds simple parametric policies (`event_id`, `operator`, `threshold`, `simulated_payout`) that reference a WeatherResolve event and evaluate deterministically to `TRIGGERED` / `NOT_TRIGGERED` / `UNRESOLVED`.

The split exists so that the hard, trust-sensitive problem — "what did the weather actually do" — is solved exactly once per (location, metric, date, source policy) tuple, and reused by any number of downstream consumers. WeatherCover is deliberately thin: it contains no weather logic, only condition evaluation and simulated bookkeeping.

---

## 2. Proposed Contract Boundaries

**Contract A — `WeatherResolve`**
- `create_weather_event(location, metric, observation_period, aggregation, source_policy) -> event_id`
- `get_weather_event(event_id) -> WeatherEvent`
- `resolve_weather_event(event_id)` — nondet method; runs the resolution algorithm, writes the Observation Registry entry
- `get_observation(event_id) -> Observation | None`
- `get_resolution_status(event_id) -> RESOLVED | UNRESOLVED | PENDING`
- `list_events(filter)` — for the explorer UI
- `get_source_policy(policy_id) -> SourcePolicyConfig`

**Contract B — `WeatherCover`**
- `create_policy(weather_event_id, operator, threshold, simulated_payout) -> policy_id`
- `get_policy(policy_id) -> Policy`
- `evaluate_policy(policy_id)` — calls WeatherResolve's `get_observation`/`get_resolution_status` (cross-contract read); deterministic
- `get_simulated_balance(address) -> int`
- `list_policies(owner)`

Cross-contract call direction is one-way: WeatherCover reads WeatherResolve. WeatherResolve has no knowledge of WeatherCover or any other consumer. This is what makes it infrastructure rather than a feature bolted onto one app.

Boundary caveat (needs verification before coding, see §21): exact GenLayer cross-contract-call syntax/permissions on StudioNet must be confirmed against current docs — the interface above is conceptual, not a frozen signature.

---

## 3. Weather Event Model

A Weather Event is an **observation request**, not a result.

Fields:
```
event_id            (bytes32, derived — see §4)
location             normalized string, e.g. "LAGOS_NG" or lat/lon pair
metric               enum, MVP: RAIN_24H
observation_period   canonical date/window, e.g. "2026-08-30" (UTC day)
aggregation          enum, e.g. "24H_TOTAL"
source_policy        versioned id, e.g. "STRICT_V1"
created_at           protocol timestamp (tx context)
observation_window_start / observation_window_end   derived from period + metric
status               PENDING | RESOLVED | UNRESOLVED
consumer_count       incremented each time a new WeatherCover (or other) policy references it
```

Events are created lazily and looked up before creation (§16) — no event is ever created twice for the same canonical inputs.

---

## 4. Event ID / Deduplication Design

`event_id = hash(normalized_location, metric, observation_period, aggregation, source_policy_version)`

All five fields are frozen at creation and are exactly the fields that determine "what observation are we even asking for." Deterministic hashing (not an incrementing counter) means:

- Any consumer computing the same canonical tuple arrives at the same `event_id` without a lookup round-trip first.
- `create_weather_event` becomes idempotent: if the id already exists, return the existing event instead of creating a duplicate.
- Changing `source_policy` version is a deliberate new event, not silently reusing an old resolution under new trust rules.

Normalization rules for `location` must be pinned before coding (canonical city+country string vs. rounded lat/lon) — flagged as an open question in §21.

---

## 5. Weather Source Strategy

Retrieval preference order, cheapest/most-verifiable first:
1. **Structured API** (`gl.nondet.web.get`) — JSON weather API endpoints where available.
2. **Static structured resource** (`gl.nondet.web.get`) — e.g. a plain HTML/CSV table, no JS required.
3. **Rendered dynamic page** (`gl.nondet.web.render(..., mode="text"|"html")`) — only when a source has no API/static path and requires JS execution; use a short `wait_after_loaded` only when required.

Each source in a policy is configured with: identifier, endpoint/URL, retrieval method (`get` vs `render`), and expected response shape (for parsing). No single source is ever treated as ground truth — the source policy's minimum-count and agreement rules (§6) govern whether a resolution can happen at all. This directly avoids "one weather provider = truth."

---

## 6. Source Policy Design

Policies are versioned, named configs, stored in the registry and referenced by id (e.g. `STANDARD_V1`, `STRICT_V1`, `FAST_V1`). A policy fixes:

```
policy_id
min_source_count
required_source_classes        e.g. ["authoritative_met_service"] for STRICT_V1
disagreement_tolerance          e.g. max 2mm absolute diff, or % relative
unavailable_source_behavior     SKIP | FAIL_POLICY
timeout_seconds
unit_normalization_required     bool (effectively always true)
sources[]                       list of configured Source entries (see §5)
```

- **STRICT_V1**: ≥3 sources, at least one from an authoritative class, tight disagreement tolerance, any source `FETCH_FAILED`/`TIMEOUT` beyond the allowed slack → `UNRESOLVED` rather than resolving on fewer sources.
- **STANDARD_V1**: ≥2 sources, looser disagreement tolerance, tolerates one failed source if remaining sources agree within tolerance.
- **FAST_V1**: single authoritative API source, no disagreement check — cheapest/fastest, explicitly weaker guarantee, useful for demo/dev.

Policies are immutable once versioned; a new ruleset ships as `STRICT_V2`, never a silent mutation of `STRICT_V1` (this is what makes "source_policy_version" a safe input to the event-id hash in §4).

---

## 7. Timestamp / Observation-Window Design

Each metric type defines how `observation_period` maps to a window:
- `RAIN_24H` for period `2026-08-30` → window = `[2026-08-30T00:00:00Z, 2026-08-31T00:00:00Z)`.

Rules:
- `resolve_weather_event` is only callable once `observation_window_end` has passed, checked against GenLayer's deterministic transaction-context clock (not wall-clock from any single node).
- Calling it before the window ends must revert/return a clear "not yet resolvable" state, not attempt resolution.
- All periods are normalized to UTC at creation; the frontend is responsible for converting to the user's local timezone for display only.
- "Late resolution" (window ended long ago) is allowed indefinitely — sources may no longer have same-day data, which naturally surfaces as `UNRESOLVED` via retrieval/date-validation failures rather than a special late-binding code path.

---

## 8. Timeout / Failure Handling

Per-source retrieval states (§7 of the spec, reproduced as the contract's enum):
`AVAILABLE, UNAVAILABLE, FETCH_FAILED, RENDER_FAILED, TIMEOUT, INVALID_RESPONSE, WRONG_LOCATION, WRONG_DATE, UNSUPPORTED_UNIT, CONFLICTING`

Each `gl.nondet.web.*` call for a configured source is wrapped so that any exception/timeout is captured as a state rather than propagated as a contract-level error — a single bad source must never abort the whole resolution unless the active policy's `unavailable_source_behavior = FAIL_POLICY`.

The resolution algorithm (§13) then evaluates "do I have enough valid, agreeing sources under this policy" — if not, it returns `UNRESOLVED(reason)` with a machine-readable reason (`INSUFFICIENT_SOURCES`, `DISAGREEMENT`, `LOCATION_UNVERIFIED`, `PERIOD_UNVERIFIED`). This makes timeout/failure behavior a first-class, testable protocol outcome rather than an implementation detail.

---

## 9. Web-Render Strategy

- Default to `gl.nondet.web.get(url)` for any source with a stable structured/static response.
- Use `gl.nondet.web.render(url, mode="text", wait_after_loaded=<short>)` only for sources whose current value requires JS execution to appear (identified per-source at config time, not decided dynamically at call time).
- The retrieved content (text/JSON) is what gets parsed into `reported_value` + `reported_unit`; the raw payload is not itself compared across validators via strict equality (see §13 consensus notes) — only the extracted, normalized fields are.
- This satisfies the "must actually retrieve the source" requirement: validators independently call `gl.nondet.web.get/render` against the real URL inside the equivalence-controlled block; nothing is pre-fetched off-chain and merely asserted.

---

## 10. Weather Normalization Model

Deterministic, plain-code normalization (no LLM arithmetic):
- **Units** → canonical unit per metric (`RAIN_24H` → millimeters). Inches, hundredths-of-inch, etc. converted with fixed-point deterministic math.
- **Location** → canonical identifier (normalized city+country token for MVP; lat/lon rounding reserved for a later metric that needs station-level precision).
- **Observation period** → canonical UTC window (§7); a source reporting local-time values must be shifted into UTC using a fixed, source-configured offset (not looked up dynamically per call, to keep it deterministic).
- **Aggregation** → if a source only exposes hourly data, summing into a 24h total is deterministic code, not an LLM judgment call.

The nondeterministic part is strictly limited to *retrieving and extracting* raw fields from the page/response equivalently across validators; all arithmetic after extraction is deterministic.

---

## 11. Resolution Algorithm

```
1. load Weather Event by event_id
2. require observation_window_end has passed
3. load Source Policy by source_policy id
4. for each configured source:
     retrieve via gl.nondet.web.get/render
     classify retrieval status (AVAILABLE / FETCH_FAILED / TIMEOUT / ...)
     if AVAILABLE: validate location match, validate date/period match
     if valid: normalize unit + value -> normalized_observation
5. discard sources that are not AVAILABLE+valid
6. if len(valid_sources) < policy.min_source_count -> return UNRESOLVED(INSUFFICIENT_SOURCES)
7. if policy.required_source_classes not satisfied -> return UNRESOLVED(MISSING_REQUIRED_CLASS)
8. compute agreement across valid_sources' normalized values
9. if disagreement exceeds policy.disagreement_tolerance -> return UNRESOLVED(DISAGREEMENT)
10. compute resolved value (e.g. median or policy-defined aggregator of agreeing sources)
11. write Observation (value, unit, source_count, evidence_status, resolved_at)
12. return RESOLVED(value)
```

Every branch point is a named, testable outcome — there is no hidden "pick whichever source looks best" step.

---

## 12. Evidence Package Design

Per resolution attempt (persisted regardless of outcome, so `UNRESOLVED` is auditable too):

```
event_id
location, metric, observation_period, source_policy
resolution_requested_at
sources: [
  {
    source_id, url, retrieval_method,       # get | render
    retrieval_status,                        # enum from §8
    reported_value, reported_unit,
    normalized_value,
    station_metadata,                        # optional
    observation_timestamp,
    source_provenance                        # e.g. response hash/digest
  }, ...
]
evidence_status          SUFFICIENT | INSUFFICIENT
resolution_status        RESOLVED | UNRESOLVED
resolved_at
```

Explicit non-claim: `source_provenance` (a digest of what validators retrieved and agreed on) proves *what data was used*, not that the underlying real-world observation is correct. This distinction is stated directly in the Evidence Package UI (§21 Weather Proof component) to avoid overclaiming.

---

## 13. Finalized Observation Registry

On `RESOLVED`, a compact, immutable record is written and is the only thing most consumers need to read:

```json
{
  "event_id": "...",
  "location": "Lagos, Nigeria",
  "metric": "RAIN_24H",
  "observation_period": "2026-08-30",
  "value": 8.6,
  "unit": "mm",
  "status": "RESOLVED",
  "source_count": 3,
  "evidence_status": "SUFFICIENT",
  "source_policy": "STRICT_V1"
}
```

Once written, RESOLVED observations are immutable — a resolution is never silently overwritten. If a policy's rules were later found wrong, that's a new source-policy version and a new event_id, not a mutation of history.

**Consensus note (mechanism, ties to §13/14 of the spec):** the equivalence strategy applies to the *inputs feeding this record* — normalized numeric values and classification enums — using `strict_eq` where structured API data makes exact agreement realistic, or a tolerance/comparative strategy where sources may legitimately report slightly different readings. Raw HTML, rendered markup, request metadata, and timestamps are never the compared object — only the deterministically-normalized value and status fields are.

---

## 14. Consumer Interface

Minimal, reusable read surface any future contract can call:

```
get_weather_event(event_id) -> WeatherEvent
get_observation(event_id) -> Observation | null
get_resolution_status(event_id) -> RESOLVED | UNRESOLVED | PENDING
evaluate_condition(event_id, operator, threshold) -> TRUE | FALSE | UNRESOLVED
```

`evaluate_condition` is a deterministic helper living in WeatherResolve so that *every* consumer (WeatherCover, a future prediction market, etc.) gets identical BELOW/ABOVE semantics against the same canonical observation, instead of each consumer reimplementing comparison logic slightly differently.

Exact method signatures remain provisional pending verification of GenLayer's current cross-contract-call and storage patterns on StudioNet (§21).

---

## 15. WeatherCover Model

```
policy_id
owner                    address
weather_event_id         reference into WeatherResolve
operator                 BELOW | ABOVE
threshold                normalized numeric value (same unit as the metric)
simulated_payout         int, simulated units
created_at
status                   PENDING | TRIGGERED | NOT_TRIGGERED | UNRESOLVED
```

`evaluate_policy(policy_id)`:
1. read `get_resolution_status(weather_event_id)` from WeatherResolve
2. if `UNRESOLVED` or `PENDING` → policy stays `UNRESOLVED`/`PENDING` (no credit, no denial)
3. if `RESOLVED` → call `evaluate_condition(weather_event_id, operator, threshold)`
4. `TRUE` → `TRIGGERED`, credit simulated balance; `FALSE` → `NOT_TRIGGERED`, no credit

---

## 16. Simulated Payout Model

No real funds anywhere in MVP — no GEN escrow, no ERC-20, no USDC, no pool, no premium/underwriting engine.

```
simulated_balance: address -> int
```

On `TRIGGERED`: `simulated_balance[owner] += policy.simulated_payout`. On `NOT_TRIGGERED`: no change. On `UNRESOLVED`: policy remains pending indefinitely — re-evaluatable later once/if the underlying event resolves (e.g. a retry after a transient source outage). This is purely an in-contract counter for demo purposes; it is explicitly not a token and not withdrawable.

---

## 17. MVP Scope

In scope (matches spec §28, restated as the actual build list):
1. Canonical Weather Event Registry + dedup (§3–4)
2. Versioned Source Policies: STANDARD_V1, STRICT_V1, FAST_V1 (§6)
3. RAIN_24H only (§10 leaves room for more)
4. Real API/web retrieval via `gl.nondet.web.get`/`render` (§5, §9)
5. Observation-window enforcement (§7)
6. Timeout/failure handling as explicit states (§8)
7. Deterministic unit/date normalization (§10)
8. Multi-source evidence + disagreement tolerance (§6, §11)
9. GenLayer consensus over normalized fields (§13 note)
10. RESOLVED / UNRESOLVED as first-class outcomes (§11)
11. Finalized Observation Registry (§13)
12. Resolution reuse via deterministic event_id (§4)
13. Consumer read interface (§14)
14. WeatherCover: create policy, evaluate, BELOW/ABOVE, simulated payout (§15–16)
15. Basic Explorer + Policy UI (frontend, not built yet — architecture only)

Out of scope for MVP: every metric beyond RAIN_24H, any real money movement, an SDK/package, multi-network deployment, automated resolution scheduling (resolution is triggered by an explicit call, not a cron).

---

## 18. Scaling Strategy

- **Horizontal reuse**: because `event_id` is a pure function of canonical inputs, any number of consumer contracts (WeatherCover policies, a future prediction market, etc.) can reference the same event without WeatherResolve needing to know they exist. `consumer_count` on the event is an optional usage-tracking increment, not a dependency.
- **New metrics**: adding `TEMP_MIN`, `WIND_MAX`, etc. means adding a metric enum entry + its normalization/aggregation rule + suitable source configs to a policy — the registry, dedup, and resolution algorithm shapes don't change.
- **New source policies**: versioned and additive; existing events keep referencing their original policy version forever (immutability, §6).
- **New consumers**: only need the four read methods in §14; they never touch retrieval/consensus logic.
- **Explorer as network-effect surface**: showing `consumer_count` per event and cross-project reuse is the visible proof that this is shared infrastructure, not a single-app oracle (this is also the strongest judge-facing argument, §20).

---

## 19. Biggest Technical Risks

1. **`gl.nondet.web.get/render` API surface may differ from assumed usage** (params, wait semantics, error types) — must be verified against current GenLayer docs/runner before any contract code is written. Flagged as blocking in §21.
2. **Cross-contract call pattern on StudioNet** (how WeatherCover reads WeatherResolve state/methods) is not yet confirmed — affects whether §14's interface is directly callable or needs an intermediate pattern.
3. **Real-world source availability/stability** for a chosen Lagos rainfall source — need at least one authoritative, scrape-or-API-friendly source that reliably returns parseable RAIN_24H data for STRICT_V1's required-class rule.
4. **Consensus/equivalence strategy tuning** — picking a disagreement tolerance that's realistic for actual rainfall reporting variance (sources can legitimately differ by more than a naive tolerance) without making STRICT_V1 impossible to satisfy.
5. **Timezone/window edge cases** — a source reporting "today's rainfall" in local time vs. the contract's UTC window could produce false `WRONG_DATE` classifications if not handled carefully.
6. **Demo reliability** — a live demo depends on real external weather sites being reachable at demo time; needs a rehearsed, verified-working event before presenting.

---

## 20. Judge / Portal Review

1. **Why does this require GenLayer?** Determining real-world weather truth from possibly-disagreeing web sources needs nondeterministic web access plus validator consensus over the *result* of that access — a deterministic-only smart contract cannot fetch or agree on external data at all.
2. **Why is it not simply a weather API oracle?** A single-API oracle assumes that one provider is correct and available. WeatherResolve requires multiple independent sources, applies explicit disagreement tolerance, and can validly return `UNRESOLVED` — an oracle wrapper around one API cannot express "I don't have confident evidence."
3. **Why is WeatherResolve reusable infrastructure?** It resolves an observation, not a payout decision. Any number of unrelated consumer contracts can read the same immutable, deduplicated Observation via four generic read methods, without re-running retrieval/consensus.
4. **How can other projects integrate it?** Call `get_weather_event`/`create_weather_event` to get an `event_id`, then `get_observation`/`evaluate_condition` once resolved. No dependency on WeatherCover.
5. **What creates network effects?** Every new consumer referencing an existing canonical event increases `consumer_count` and reduces the marginal cost (gas + retrieval + consensus rounds) of the *next* consumer needing the same fact.
6. **How does event deduplication improve scalability?** 500 policies needing "Lagos RAIN_24H Aug 30 STRICT_V1" trigger exactly one resolution; the deterministic `event_id` hash makes this dedup automatic rather than requiring an off-chain registry.
7. **How do Source Policies prevent blind trust in one provider?** Policies fix minimum source counts, required source classes, and disagreement tolerance; a resolution with too few or disagreeing sources cannot produce `RESOLVED` under STRICT_V1.
8. **How is a valid web render demonstrated?** Each configured source is retrieved live inside the resolution call via `gl.nondet.web.get` or `.render`, executed independently by validators under GenLayer's equivalence principle — not pre-fetched off-chain and asserted.
9. **How are timestamps enforced?** `resolve_weather_event` requires the deterministic transaction-context clock to show the observation window has ended; premature resolution is rejected at the protocol level.
10. **How are source timeouts handled?** Each source call is isolated; a `TIMEOUT` becomes a per-source status, evaluated against the active policy's minimums — one slow source doesn't crash the resolution unless the policy demands it.
11. **How do conflicting sources produce UNRESOLVED?** Disagreement beyond the policy's tolerance is a named branch in the resolution algorithm returning `UNRESOLVED(DISAGREEMENT)`, with the conflicting Evidence Package preserved for inspection.
12. **What could cause this project to score poorly?** Fragile/unreachable real sources during the live demo; an under-verified `gl.nondet.web` API usage; too-thin evidence UI that hides the disagreement/timeout mechanics that are the actual differentiator.
13. **What must work in the live demo?** One live end-to-end resolution (ideally a real, current Lagos rainfall event) reaching `RESOLVED`, one deliberately forced `UNRESOLVED` case (e.g. via a bad/unreachable source), and a WeatherCover policy evaluating against the resolved event.
14. **What should be cut from the MVP?** Anything beyond RAIN_24H, any SDK/embeddable component beyond a basic evidence view, and multi-metric source policy tuning — keep STRICT_V1 as the one deeply tested policy.
15. **How does this continue to have value after the portal submission?** As infrastructure, it keeps value independent of WeatherCover: any future weather-dependent contract (agriculture, logistics, prediction markets) can integrate against the same Observation Registry without re-solving the oracle problem.

---

## 21. Exact Questions Requiring Approval Before Implementation

1. **`gl.nondet.web.*` verification** — confirm exact current signatures/params for `get`, `render`, `request` against the installed StudioNet runner before any retrieval code is written (spec explicitly forbids guessing).
2. **Cross-contract call mechanism** — confirm how WeatherCover should call WeatherResolve's read methods on StudioNet (direct call vs. required pattern), which affects §2/§14's interface shape.
3. **Location normalization format** — pick one: canonical city+country string (e.g. `"LAGOS_NG"`) vs. rounded lat/lon pair, for the event-id hash (§4). Recommend city+country string for MVP simplicity; confirm before freezing the hash function.
4. **Concrete source list for RAIN_24H / Lagos** — which specific weather sources (API or web) will populate STRICT_V1/STANDARD_V1/FAST_V1 for the demo, and confirm at least one is reliably reachable via `gl.nondet.web.get`.
5. **Disagreement tolerance values** — need a concrete numeric tolerance (e.g. mm difference or %) for STRICT_V1 vs STANDARD_V1, informed by real source variance once sources are chosen.
6. **Consensus/equivalence strategy per field** — confirm whether `strict_eq` on normalized values is viable given real source precision, or whether a comparative/custom strategy is required from the start.

Architecture complete. Awaiting approval before any contract code is written.
