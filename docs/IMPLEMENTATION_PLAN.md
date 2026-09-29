# WeatherResolve + WeatherCover — Implementation Plan

Status: architecture approved with modifications (see `PRODUCT_ARCHITECTURE.md`). This plan incorporates all ten approved changes and records the API verification performed before writing any contract code.

---

## 0. API Verification (done, not guessed)

Per change #10, the GenLayer Intelligent Contract API was verified against a **working, tested contract that existed on the original development machine** — `protocolcourt/contracts/protocol_court.py`, a separate GenLayer project outside this repository, not a path within it — rather than against memory or the spec's suggested calls in isolation. That contract was exercised by a real `gltest` direct-mode test suite, so its usage was proof, not assumption. It is referenced throughout this document by name as the source of each verified pattern; if you don't have that project available, treat these as "this exact usage was confirmed working against a real GenVM runner before it was reused here," not as a link to follow.

Confirmed, in-use API surface (pinned runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`):

| Call | Verified shape | Notes |
|---|---|---|
| `gl.nondet.web.get(url)` | returns object with `.body` (`bytes \| None`) and `.status` (int) | Treat `body is None or status >= 400` as failure |
| `gl.nondet.web.render(url, mode="text")` | returns `str` directly, or raises | Wrap in `try/except Exception` |
| `gl.vm.run_nondet(leader_fn, validator_fn)` | the **recommended** nondet-execution API in this toolchain | `leader_fn()` runs and produces a result; `validator_fn(leaders_result)` receives a `gl.vm.Return` wrapping `.calldata` and returns `bool` |
| `gl.nondet.exec_prompt(prompt, response_format="json")` | LLM call, mockable via `vm.mock_llm` in tests | Used only inside `validator_fn`, only when deterministic comparison of two leader/validator payloads is insufficient |
| `gl.eq_principle.strict_eq` / `.prompt_comparative` / `.prompt_non_comparative` | **confirmed NOT usable** in this workspace's `gltest` direct-mode harness (genlayer-test 0.29.2 has no handler for the internal `ExecPromptTemplate` call these wrappers issue) | Do not use these wrappers; use `gl.vm.run_nondet` + `gl.nondet.exec_prompt` instead, exactly as `protocol_court.py` does |
| `gl.Contract` subclass with typed fields | `Address`, `u256`, `TreeMap[str, DataClass]`, `DynArray[str]` | Storage model confirmed working |
| `@gl.public.write`, `@gl.public.write.payable`, `@gl.public.view` | method decorators confirmed in active use | |
| `gl.message.sender_address` | confirmed | |

This resolves architecture open questions §21.1 (`gl.nondet.web.*` signatures) and §21.6 (consensus mechanism) with verified, not guessed, answers.

**Windows dev-loop gotcha (carried over):** `protocolcourt/tests/conftest.py` patches a bug in `gltest.direct.loader._inject_message_to_fd0` that raises `PermissionError` on Windows during direct-mode tests (it tries to unlink a file while a duplicated fd is still open — POSIX-only behavior). This project will reuse the same conftest shim verbatim rather than rediscover the issue.

**Still unverified / to confirm when needed:**
- Cross-contract call syntax on StudioNet — **not needed**, see §1 below (deliberately avoided for MVP).
- Concrete real-world source URL(s) for Lagos RAIN_24H that respond well to `gl.nondet.web.get`/`.render` — to be selected during §5 implementation, tested live against StudioNet before freezing.

---

## 1. Single-Contract MVP Decision (change #2)

Cross-contract-call patterns on StudioNet were not part of the verified evidence above — `protocol_court.py`, the one real precedent available, does everything in **one** `gl.Contract` subclass. Rather than spend implementation time verifying a cross-contract pattern this MVP doesn't strictly need, **WeatherResolve and WeatherCover ship as one deployed contract, `WeatherResolveCover`**, for StudioNet MVP.

The two-layer *architecture* is preserved as an internal boundary, not a deployment boundary:

- All WeatherResolve responsibilities (event registry, source policies, retrieval, resolution algorithm, Observation Registry) live in one clearly-separated section of the file, with methods prefixed `event_*`/`resolve_*`/`observation_*`.
- All WeatherCover responsibilities (policies, evaluation, simulated balances) live in a second section, with methods prefixed `policy_*`.
- WeatherCover's internal methods call WeatherResolve's internal methods as **plain Python function calls within the same contract**, not `gl`-level cross-contract calls — i.e. `self.policy_evaluate(...)` calls `self._get_observation(...)` directly.
- Storage is still logically partitioned (separate `TreeMap`s per concern), so splitting into two real deployed contracts later — once cross-contract calls are verified — is a mechanical extraction, not a redesign.

This directly satisfies "keep the separation in the architecture" (unmodified) while satisfying "reduce deployment risk via single-contract if cross-contract calls are unverified" (the actual constraint that applies here).

---

## 2. Storage Schema

```python
class WeatherResolveCover(gl.Contract):
    # --- WeatherResolve state ---
    events: TreeMap[str, WeatherEvent]          # event_id -> event
    observations: TreeMap[str, Observation]      # event_id -> resolved/unresolved result
    source_policies: TreeMap[str, SourcePolicy]  # policy_id -> config (configurable, change #5)
    next_event_seq: u256

    # --- WeatherCover state ---
    policies: TreeMap[str, CoverPolicy]          # policy_id -> policy
    policy_ids_by_owner: TreeMap[str, DynArray[str]]
    simulated_balances: TreeMap[str, u256]       # address-as-str -> balance
    next_policy_seq: u256

    owner: Address   # deployer; only address allowed to register/update source policies
```

`WeatherEvent`, `Observation`, `SourcePolicy`, `CoverPolicy` are `@gl.contract.dataclass` (or equivalent local dataclass pattern used by `protocol_court.py`'s `Protocol`/`Commitment`/etc.) — mirrored from that file's proven pattern rather than invented fresh.

### `SourcePolicy` (configurable — changes #5, #6)

```python
@dataclass
class SourceConfig:
    source_id: str
    url: str
    fetch_mode: str          # "get" | "render"
    source_class: str        # e.g. "authoritative_met", "aggregator"

@dataclass
class SourcePolicy:
    policy_id: str
    min_source_count: u256
    required_source_classes: DynArray[str]     # e.g. ["authoritative_met"], may be empty
    disagreement_tolerance_mm: u256            # configurable numeric tolerance (change #6), fixed-point (x100 for 2dp mm)
    unavailable_source_behavior: str           # "SKIP" | "FAIL_POLICY"
    timeout_behavior: str                      # "SKIP" | "FAIL_POLICY"
    sources: DynArray[SourceConfig]
    version_locked: bool                       # true once any event references it (immutability, arch §6)
```

Policies are **owner-configurable at deploy/setup time** via `register_source_policy(...)` / `update_source_policy(...)` calls (only before `version_locked`), rather than hardcoded `STANDARD_V1`/`STRICT_V1`/`FAST_V1` constants baked into contract code. This directly implements change #5. The three named profiles from the architecture doc become **seed data** registered via a setup script after deploy, not compiled-in behavior — so tolerance and thresholds can be tuned without redeploying (change #6).

---

## 3. Event Model (unchanged from architecture, location format frozen)

```python
@dataclass
class WeatherEvent:
    event_id: str
    location: str              # CITY_COUNTRY format, frozen (change #3): "LAGOS_NG"
    metric: str                # "RAIN_24H" only (change #4)
    observation_period: str    # "2026-08-30", UTC calendar day
    source_policy_id: str
    created_at: str            # ISO timestamp from gl.message / block context
    status: str                # "PENDING" | "RESOLVED" | "UNRESOLVED"
    consumer_count: u256
```

`event_id = fnv1a_hex(f"{location}|{metric}|{observation_period}|{source_policy_id}")` — same deterministic-hash dedup approach already proven in `protocol_court.py` (`_fnv1a`, used there for evidence fingerprinting), reused for event IDs here.

**CITY_COUNTRY normalization rule (change #3, frozen):** uppercase, underscore-joined city token + ISO-3166 alpha-2 country code, e.g. `"Lagos, Nigeria"` → `"LAGOS_NG"`. A small deterministic lookup/normalization function maps accepted free-text inputs to this canonical form; unmappable input is rejected at `create_weather_event` with `EXPECTED:UNKNOWN_LOCATION`.

---

## 4. Deterministic Aggregation vs. GenLayer Judgment (changes #7, #8)

This is the most important behavioral rule from the approved changes, and it maps directly onto the working precedent:

- **Deterministic Python code** (no LLM, no nondet) does:
  - unit conversion (inches → mm, etc.)
  - numeric parsing of a source's reported value
  - the actual disagreement/tolerance check and the aggregation function (median of valid normalized values) once all sources are classified `AVAILABLE`
  - date/period/location string matching

- **GenLayer nondet judgment** (`gl.vm.run_nondet` + `gl.nondet.exec_prompt`, exactly the Tier‑1 pattern in `protocol_court.py`) is used **only** for the one place semantic interpretation is unavoidable: deciding whether leader and validator retrieved *substantively the same source content* when the raw bytes/text differ (ads, timestamps, formatting noise) — the same "retrieval fidelity, not byte equality" judgment already proven working. It is never used to parse a number, convert a unit, or decide a comparison outcome.

Concretely, for each configured source:
```python
def leader_fn():
    return _fetch_and_extract(url, fetch_mode, metric)   # returns raw retrieval + extracted numeric value

def validator_fn(leaders_result):
    if not isinstance(leaders_result, gl.vm.Return): return False
    leader_data = leaders_result.calldata
    my_data = _fetch_and_extract(url, fetch_mode, metric)
    if my_data["status"] != leader_data["status"]: return False
    if my_data["status"] != "AVAILABLE": return True
    if my_data["raw_text"] == leader_data["raw_text"]: return True
    # only here does semantic judgment enter, exactly as protocol_court's fidelity check:
    judgment = gl.nondet.exec_prompt(_fidelity_prompt(url, leader_data["raw_text"], my_data["raw_text"]), response_format="json")
    return _judged_faithful(judgment)

data = gl.vm.run_nondet(leader_fn, validator_fn)
```

`_fetch_and_extract` itself does deterministic numeric extraction (regex/parse) from the retrieved text — the LLM is never asked "what is the rainfall value," only "are these two retrievals of the same source substantively the same."

---

## 5. Resolution Algorithm (unchanged in shape, now grounded in verified calls)

```
resolve_weather_event(event_id):
  1. load event; require status == PENDING
  2. require now >= observation_window_end(event)      # deterministic date check, no wall clock
  3. load source_policy(event.source_policy_id)
  4. for each source in policy.sources:
       data = gl.vm.run_nondet(leader_fn, validator_fn)   # per §4
       classify retrieval_status; if AVAILABLE, deterministically extract+normalize numeric value
  5. drop sources not AVAILABLE+valid (location/date match)
  6. if valid_count < policy.min_source_count -> UNRESOLVED(INSUFFICIENT_SOURCES)
  7. if required_source_classes not covered -> UNRESOLVED(MISSING_REQUIRED_CLASS)
  8. compute deterministic spread of normalized values; if max-min > policy.disagreement_tolerance_mm -> UNRESOLVED(DISAGREEMENT)
  9. resolved_value = median(normalized values)          # deterministic aggregation, change #7
  10. write Observation(event_id, resolved_value, "mm", RESOLVED, evidence_status=SUFFICIENT)
  11. event.status = RESOLVED
```

Each `UNRESOLVED` path writes an Evidence Package (kept per change #9) so the reason is inspectable even without a successful resolution.

---

## 6. Kept From Architecture Unchanged (change #9)

- Evidence Package per resolution attempt (sources, statuses, raw/normalized values, provenance fingerprint via `_fnv1a`, reused from `protocol_court.py`).
- Retrieval status enum: `AVAILABLE, UNAVAILABLE, FETCH_FAILED, RENDER_FAILED, TIMEOUT, INVALID_RESPONSE, WRONG_LOCATION, WRONG_DATE, UNSUPPORTED_UNIT, CONFLICTING`.
- `RESOLVED`/`UNRESOLVED` as first-class Observation statuses; `TRIGGERED`/`NOT_TRIGGERED`/`UNRESOLVED` as first-class CoverPolicy statuses.
- Timestamp/observation-window enforcement using deterministic transaction/block context, not wall-clock.
- Web retrieval via `gl.nondet.web.get`/`.render`, preferring `get` (structured/static) over `render`.
- Finalized Observation Registry as the immutable, reusable read surface.

---

## 7. Consumer / WeatherCover Interface (single-contract form)

```python
@gl.public.write
def create_weather_event(location, metric, observation_period, source_policy_id) -> str: ...
@gl.public.write
def resolve_weather_event(event_id) -> None: ...
@gl.public.view
def get_observation(event_id) -> dict | None: ...
@gl.public.view
def get_resolution_status(event_id) -> str: ...

@gl.public.write
def create_policy(weather_event_id, operator, threshold, simulated_payout) -> str: ...
@gl.public.write
def evaluate_policy(policy_id) -> None: ...
@gl.public.view
def get_policy(policy_id) -> dict: ...
@gl.public.view
def get_simulated_balance(address) -> u256: ...

@gl.public.write   # owner-only, change #5
def register_source_policy(policy_id, min_source_count, required_source_classes, disagreement_tolerance_mm, unavailable_source_behavior, timeout_behavior, sources) -> None: ...
```

`evaluate_policy` internally calls `_get_observation`/`_evaluate_condition` as plain function calls (§1) — no `gl`-level cross-contract call needed for MVP.

---

## 8. File/Module Layout

```
Wheatheresolve/
  docs/
    PRODUCT_ARCHITECTURE.md         (done)
    IMPLEMENTATION_PLAN.md          (this file)
  contracts/
    weather_resolve_cover.py        (single deployed contract, per §1)
  tests/
    conftest.py                     (Windows fd0 shim, copied verbatim from protocolcourt)
    direct/
      test_event_registry.py        (create/dedup/lookup)
      test_source_policy.py         (register/configure/lock)
      test_resolution.py            (leader/validator retrieval, RESOLVED/UNRESOLVED branches, tolerance)
      test_policy_evaluation.py     (WeatherCover BELOW/ABOVE, TRIGGERED/NOT_TRIGGERED/UNRESOLVED, simulated balances)
  scripts/
    seed_source_policies.py         (registers STANDARD_V1/STRICT_V1/FAST_V1 as configured data post-deploy)
```

---

## 9. Test Plan (direct-mode, `gltest`, mirroring `protocolcourt`'s proven harness)

1. **Event registry**: create event, verify deterministic `event_id`; re-create with identical inputs returns same id (dedup); different `source_policy_id` → different id.
2. **Source policy configuration**: register a policy, verify fields stored; attempt to mutate after it's referenced by a resolved event → rejected (`version_locked`).
3. **Retrieval classification**: using `direct_vm.mock_web` (or equivalent cheatcode used in `protocolcourt`'s test suite) to simulate `AVAILABLE`, `FETCH_FAILED`, `TIMEOUT` per source; assert correct per-source status.
4. **Resolution — RESOLVED path**: enough agreeing sources under a policy's tolerance → `RESOLVED` with correct median value.
5. **Resolution — UNRESOLVED paths**: insufficient sources, missing required class, disagreement beyond configured tolerance — each asserted with the correct reason code.
6. **Fidelity judgment path**: two mocked sources returning byte-different but semantically-equivalent text → `gl.nondet.exec_prompt` mocked via `vm.mock_llm` to return "faithful" → resolution proceeds; mocked "unfaithful" → validator disagreement → exercised via `vm.run_validator()` exactly as `protocolcourt`'s evidence tests do.
7. **Observation window enforcement**: resolving before `observation_period` end is rejected.
8. **WeatherCover evaluation**: `TRIGGERED`/`NOT_TRIGGERED` for BELOW/ABOVE against a resolved observation; `UNRESOLVED` policy stays pending (no balance change) when the referenced event is `UNRESOLVED`.
9. **Simulated balance accounting**: balance increments only on `TRIGGERED`, never on `NOT_TRIGGERED`/`UNRESOLVED`.

Everything above runs against **StudioNet-pinned `direct` mode** (no live network calls in the unit suite); a small number of scripts under `scripts/` will separately perform real `gl.nondet.web.get`/`.render` calls against actual weather sources on StudioNet itself as release-candidate verification (architecture §27), once concrete source URLs are chosen.

---

## 10. Sequencing

1. Write dataclasses + storage skeleton, no logic — confirm it deploys in direct mode.
2. Implement event registry + dedup + source-policy registration/config (owner-only writes).
3. Implement `_fetch_and_extract` + `leader_fn`/`validator_fn` + `gl.vm.run_nondet` wiring for a single mocked source; get one green resolution test.
4. Extend to multi-source aggregation, tolerance, and all `UNRESOLVED` branches.
5. Implement WeatherCover policy creation/evaluation/simulated balances on top of the now-working Observation Registry.
6. Full direct-mode test suite green.
7. Pick and verify at least one real Lagos RAIN_24H source live against StudioNet (manual script, not part of unit tests).
8. Freeze contract source, hash it, prepare manual-deployment docs (per architecture §26–27) — implementation stops there; deployment remains yours.

---

Ready to begin step 1 (storage skeleton) on your go-ahead.
