# WeatherCover

**Weather conditions verified. Coverage decisions automated.**

WeatherCover is a parametric weather insurance application. A policy says something simple — "pay out if rainfall in Lagos is below 10mm on this date" — and the interesting part isn't the payout logic, it's how the weather condition gets verified before that logic ever runs.

WeatherCover is built on **WeatherResolve**, a reusable real-world observation layer on [GenLayer](https://genlayer.com). WeatherResolve is the infrastructure; WeatherCover is the first application built on top of it.

---

## The problem

A parametric insurance contract needs to know one fact: what really happened in the physical world. A traditional smart contract cannot find that out on its own — it can only trust whatever single price feed or oracle hands it a number. If that one source is wrong, down, or misconfigured, the contract has no way to know, and no way to say so.

## Why GenLayer is required

GenLayer Intelligent Contracts can execute non-deterministic operations — including live web retrieval — inside a contract, and then reach **validator consensus** on the result before it becomes on-chain state. That is not possible in a normal deterministic smart contract, and it is exactly what "verifying a real-world weather condition" requires: independently fetching evidence from multiple sources, and only accepting a value once independent validators agree it's real. See [`docs/SUBMISSION_ARCHITECTURE.md`](docs/SUBMISSION_ARCHITECTURE.md) for exactly which operations are deterministic and which require GenLayer, and why.

## WeatherResolve — the infrastructure layer

WeatherResolve retrieves weather evidence from multiple independently retrieved weather evidence sources, verifies that each source's response actually pertains to the requested **location** (via a generic Location Resolution Profile — canonical name, aliases, country, or coordinate proximity, never an internal ID a real source would never contain) and the requested **date**, normalizes every value to a common unit, and resolves one canonical observation once enough of those independently retrieved sources agree.

A resolution can also honestly come back **UNRESOLVED** — too few valid sources, disagreement beyond tolerance, or a location/date mismatch. That is a first-class, expected outcome, not an error: WeatherResolve would rather say "I don't know yet" than fabricate a number.

Every resolved (or unresolved) observation is written to a canonical, deduplicated **Observation Registry**, keyed deterministically by location + metric + date + source policy. Any number of future applications — not just WeatherCover — can read that registry without re-solving the oracle problem themselves.

## WeatherCover — the application layer

WeatherCover holds no retrieval, verification, or resolution logic of its own. A policy references one WeatherResolve event, defines a condition (`BELOW`/`ABOVE` a threshold) and a simulated payout, and is evaluated by reading the Observation Registry once:

- If the observation is **RESOLVED**, the condition is checked deterministically and the policy becomes `TRIGGERED` or `NOT_TRIGGERED`.
- If the observation is **UNRESOLVED**, the policy stays `UNRESOLVED` — no payout is credited or denied, and it can be evaluated again later.

Payouts in this build are **simulated units only** — no real funds, escrow, or tokens exist anywhere in this product.

## How the full lifecycle works

```
Real-world weather data
        ↓
WeatherResolve            (retrieves evidence from multiple independently retrieved sources)
        ↓
Evidence Package          (per-source: retrieval status, location/date match, normalized value)
        ↓
Observation Registry      (GenLayer validator consensus reaches RESOLVED or UNRESOLVED)
        ↓
WeatherCover Policy       (reads the resolved observation, evaluates BELOW/ABOVE)
        ↓
TRIGGERED / NOT_TRIGGERED / UNRESOLVED
```

This lifecycle was verified end-to-end on live GenLayer StudioNet — not simulated — including a real historical Lagos rainfall observation resolved from 3 independently retrieved weather evidence sources, and a real coverage policy evaluated to `TRIGGERED` against it. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the exact addresses and transaction hashes.

---

## Project layout

```
contracts/weather_resolve_cover.py   The Intelligent Contract (WeatherResolve + WeatherCover, single deployment)
tests/                                47 direct-mode tests (pytest + gltest), no live network required
frontend/                             Next.js app -- landing, dashboard, create policy, Evidence Explorer, policy result
docs/
  SUBMISSION_ARCHITECTURE.md          Concise system architecture for judges/reviewers
  DEMO_SCRIPT.md                      3-minute judge walkthrough
  JUDGE_EXPLANATION.md                Direct answers to "why does this need GenLayer" and related questions
  PRODUCT_ARCHITECTURE.md             Full architecture: event model, source policies, resolution algorithm
  IMPLEMENTATION_PLAN.md              Build plan + GenLayer API verification performed before writing contract code
  FRONTEND_DESIGN_DECISION.md         Design system selection (Modern Treasury-inspired) and rationale
  DEPLOYMENT.md                       Manual deployment workflow, current StudioNet address, smoke test instructions
  AUDIT.md                            Pre-release audit: contract/frontend compatibility, security review
```

## Status

- **Contract**: implemented, 47/47 direct-mode tests passing, verified end-to-end on live GenLayer StudioNet.
- **Frontend**: implemented, mobile-responsive, typechecked and built clean, verified in-browser against the live StudioNet contract.
- **Deployment**: manual only — see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). No automated deploys, no private key handling anywhere in this repository.

## Quick start

**Run the contract test suite:**
```bash
python -m pytest tests/ -q
```

**Run the frontend against the currently deployed demo contract:**
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Full instructions, the current contract address, and smoke-test steps: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Documentation index

| Document | Covers |
|---|---|
| [`docs/SUBMISSION_ARCHITECTURE.md`](docs/SUBMISSION_ARCHITECTURE.md) | Concise system overview, contract responsibilities, data flow, deterministic vs. GenLayer operations |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | 3-minute judge walkthrough |
| [`docs/JUDGE_EXPLANATION.md`](docs/JUDGE_EXPLANATION.md) | Direct answers: why GenLayer, why not just a weather API, why WeatherResolve is reusable infrastructure |
| [`docs/PRODUCT_ARCHITECTURE.md`](docs/PRODUCT_ARCHITECTURE.md) | Full architecture: event model, dedup, source policies, resolution algorithm, Evidence Package |
| [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) | Build sequencing and the GenLayer API verification done before any contract code |
| [`docs/FRONTEND_DESIGN_DECISION.md`](docs/FRONTEND_DESIGN_DECISION.md) | Design system selection and how it communicates trust/verification |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Manual deployment workflow, current contract address, configuration, smoke tests |
| [`docs/AUDIT.md`](docs/AUDIT.md) | Release-readiness audit: contract/frontend compatibility, demo-value review, security review |
| [`docs/MANUAL_DEPLOYMENT.md`](docs/MANUAL_DEPLOYMENT.md) | Step-by-step manual StudioNet deployment guide (for the person deploying with their own wallet) |
| [`docs/MANUAL_SMOKE_TEST.md`](docs/MANUAL_SMOKE_TEST.md) | Full post-deployment checklist: contract verification + frontend verification |
| [`docs/RELEASE_FREEZE.md`](docs/RELEASE_FREEZE.md) | Frozen contract hash, build/test results, known limitations, intentionally excluded features |
| [`frontend/README.md`](frontend/README.md) | Frontend-specific setup and architecture |
