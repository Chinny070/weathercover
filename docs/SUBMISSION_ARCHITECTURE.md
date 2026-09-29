# Submission Architecture

A concise system architecture. For the full design rationale, deduplication logic, and the complete judge Q&A this project was originally designed against, see [`PRODUCT_ARCHITECTURE.md`](PRODUCT_ARCHITECTURE.md).

---

## 1. System overview

One deployed GenLayer Intelligent Contract, `WeatherResolveCover`, containing two internal layers:

```
                    ┌─────────────────────────────────┐
                    │         WeatherResolveCover        │
                    │         (one contract)             │
                    │                                     │
   real-world   →   │  WeatherResolve layer               │
   weather data      │  - event registry                  │
                    │  - source policies                  │
                    │  - location resolution profiles     │
                    │  - evidence retrieval + resolution  │
                    │  - Observation Registry              │
                    │                                     │
                    │         reads ↓                     │
                    │                                     │
                    │  WeatherCover layer                 │
                    │  - policy creation                  │
                    │  - condition evaluation             │
                    │  - simulated balances               │
                    └─────────────────────────────────┘
                                    ↑
                          frontend (Next.js, this repo)
                          reads/writes via genlayer-js
```

The two layers are a single deployment (not two contracts) because cross-contract-call patterns were not part of the verified GenLayer API surface at build time — see `IMPLEMENTATION_PLAN.md` §1. The internal boundary is still real: WeatherCover only ever *reads* `events`/`observations` via plain function calls; it never writes to WeatherResolve's storage.

## 2. Contract responsibilities

| Responsibility | Owner | Notes |
|---|---|---|
| Canonical Weather Event Registry | WeatherResolve | Deterministic `event_id` = hash(location, metric, period, source_policy_id) → automatic dedup |
| Location Resolution Profile registry | WeatherResolve | Generic: canonical name, aliases, country, coordinates+radius — no location hardcoded in retrieval code |
| Source Policy registry | WeatherResolve | Owner-configured: min source count, disagreement tolerance, failure behavior — versioned, immutable once referenced |
| Evidence retrieval + validation | WeatherResolve | `gl.nondet.web.get`/`.render` + `gl.vm.run_nondet` leader/validator consensus, per source |
| Observation resolution | WeatherResolve | Deterministic aggregation (median) + tolerance check → `RESOLVED`/`UNRESOLVED` |
| Observation Registry | WeatherResolve | Immutable once `RESOLVED`; the reusable read surface for any consumer |
| Policy creation | WeatherCover | Denormalizes display fields from the referenced event; owner/operator/threshold/payout |
| Condition evaluation | WeatherCover | Deterministic `BELOW`/`ABOVE` comparison against the resolved value |
| Simulated payout tracking | WeatherCover | Plain integer balance per address; no tokens, no escrow |

## 3. Data flow

```
Real-world weather data
        ↓
WeatherResolve          event_create_weather_event()  →  resolve_weather_event()
        ↓
Evidence Package        one row per source: retrieval status, location/date match,
                         normalized value, provenance fingerprint
        ↓
Observation Registry    RESOLVED (value + evidence) or UNRESOLVED (reason) — immutable, reusable
        ↓
WeatherCover Policy     cover_create_policy() references the event; cover_evaluate_policy()
                        reads the Observation Registry once
        ↓
TRIGGERED / NOT_TRIGGERED / UNRESOLVED
```

Every arrow above is a real, separately-callable contract method — there is no hidden step. The frontend's `lib/genlayer/contract.ts` exposes exactly these calls and nothing else invented.

## 4. Deterministic vs. GenLayer operations

This split is the core design discipline of the whole project (see `PRODUCT_ARCHITECTURE.md` §13 and `IMPLEMENTATION_PLAN.md` §4 for the original design decision):

| Deterministic (plain Python, every validator computes the same thing) | GenLayer non-deterministic (requires consensus) |
|---|---|
| Unit conversion (inches → mm, exact integer arithmetic) | `gl.nondet.web.get(url)` / `gl.nondet.web.render(url, mode="text")` — the actual HTTP retrieval |
| Numeric extraction from retrieved text (generic decimal-token scan) | `gl.vm.run_nondet(leader_fn, validator_fn)` — leader/validator retrieval consensus |
| Location match (name/alias/country substring, coordinate-distance formula) | `gl.nondet.exec_prompt(...)` — **only** when leader and validator retrieve byte-different text for the same URL, to judge whether it's substantively the same source |
| Date match (exact string check) | GenLayer's Optimistic Democracy consensus itself — validators must independently agree before a resolution becomes state |
| Disagreement/tolerance check, median aggregation | |
| `BELOW`/`ABOVE` condition evaluation (WeatherCover) | |
| Simulated balance arithmetic | |

**The LLM (`gl.nondet.exec_prompt`) never touches a number.** It is invoked in exactly one place — judging retrieval fidelity when two independent fetches of the same URL disagree at the byte level (e.g. incidental timestamp/ad differences) — never for extraction, conversion, comparison, or aggregation. This is a deliberate, narrow use of GenLayer judgment, not a general "ask an AI" pattern.

## 5. Evidence verification flow

For each configured source, per resolution attempt:

```
1. FETCH or RENDER the source URL (gl.nondet.web.get/.render)
     ├─ exception / timeout / non-2xx → classified FETCH_FAILED / RENDER_FAILED / UNAVAILABLE / TIMEOUT
     └─ success → raw text
2. Location check: does the text match the requested location's canonical name,
   an alias, (name AND country together), or fall within its coordinate radius?
     └─ no → WRONG_LOCATION
3. Date check: does the text contain the requested observation date?
     └─ no → WRONG_DATE
4. Numeric extraction: mask out the date/location/coordinate tokens, take the
   LAST remaining decimal number (structured APIs put the real reading after
   their echoed metadata) → normalize to mm×100
     └─ no number found → INVALID_RESPONSE
5. AVAILABLE, with a normalized value
```

Across all configured sources:

```
6. Apply the source policy's failure behavior (SKIP or FAIL_POLICY) to any
   non-AVAILABLE source
7. Require ≥ min_source_count AVAILABLE sources, else UNRESOLVED(INSUFFICIENT_SOURCES)
8. Require required source classes present, else UNRESOLVED(MISSING_REQUIRED_CLASS)
9. Require spread ≤ disagreement_tolerance, else UNRESOLVED(DISAGREEMENT)
10. Resolve to the median of the agreeing values → RESOLVED
```

Every one of these ten steps is visible per-source in the Evidence Explorer — nothing is summarized away.

## 6. Why this cannot be a normal deterministic smart contract

A deterministic contract can execute step 10 perfectly (median, comparison, aggregation are pure math). It categorically cannot execute steps 1–6: it has no way to make an HTTP request, no way to know if a real-world value is true, and no way for independent parties to agree on what a web page said *at the time of execution* without either (a) trusting one centralized oracle to feed it a pre-computed answer, or (b) a mechanism for independent nodes to fetch the same evidence themselves and reach consensus on it.

GenLayer's non-deterministic execution (`gl.nondet.web.*`) plus its Optimistic Democracy consensus over `gl.vm.run_nondet` leader/validator results *is* that mechanism, built into the contract layer itself rather than bolted on as an external oracle service. WeatherResolve is only possible because that primitive exists — and because it can produce `UNRESOLVED` instead of being forced to output *some* value even when the evidence doesn't support one, which no oracle-fed deterministic contract can do honestly (an oracle either delivers a number or the whole system halts; it cannot express "evidence was insufficient" as a first-class on-chain outcome the way WeatherResolve's own resolution algorithm does).
