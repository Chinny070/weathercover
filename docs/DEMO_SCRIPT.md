# Demo Script — 3-Minute Judge Walkthrough

Live contract (canonical, see `docs/CANONICAL_DEPLOYMENT.md`): `0xFd7160411e5812bD873089368b1BF687e644a959` on GenLayer StudioNet. Every screen below shows real on-chain data, not a mock. See `docs/DEPLOYMENT.md` for exact commands if you want to reproduce any of it live during Q&A.

Open these tabs before starting: `/`, `/observations/3d603813dbd7ae98`, `/policies/cover-1`, `/policies/cover-3`, `/dashboard`.

---

### 0:00 – Problem

> "Parametric insurance needs to answer one question honestly: what actually happened in the real world? A normal smart contract can enforce a policy's math perfectly, but it can't independently verify a real-world weather condition — it has to trust whatever single oracle feeds it a number. If that source is wrong, or down, the contract has no way to know."

Stay on a blank browser or slide — no screen needed yet.

### 0:30 – WeatherCover overview

**Screen: `/` (landing page)**

> "WeatherCover is parametric weather coverage, but it's not the interesting part. It's built on WeatherResolve — reusable infrastructure that retrieves weather evidence from multiple independently retrieved sources and only resolves an observation once GenLayer validators agree it's real. WeatherCover is just the first application built on top of that registry."

Scroll to the 5-step flow diagram: "Every policy follows this same path — nothing is decided until the evidence is in."

### 1:00 – Evidence Explorer demonstration

**Screen: `/observations/3d603813dbd7ae98`**

> "This is a real observation, resolved live on StudioNet — 12.30mm of rain in Lagos on August 30th. Here's the actual verification pipeline: source retrieval, evidence validation, observation resolution, policy evaluation."

Scroll to the evidence table.

> "Three independent Open-Meteo historical queries. Each one was checked against a Location Resolution Profile — canonical name, aliases, country, **or coordinate proximity**, because real weather APIs never say 'Lagos' in their JSON, they just return coordinates. All three values agree within tolerance — 12.30, 10.50, 13.60mm — and GenLayer validators reached `MAJORITY_AGREE` on this evidence independently. This isn't one API call I'm asking you to trust."

### 1:45 – Create / evaluate policy

**Screen: `/create-policy`** (narrate the flow; live wallet interaction if a judge wants to see it, otherwise describe)

> "Creating a policy is three fields that matter: which resolved event, a BELOW/ABOVE condition and threshold, and a simulated payout. No GenLayer knowledge required — the user just picks a condition."

**Screen: `/policies/cover-1`**

> "Here's a real policy: BELOW 15mm against that same 12.30mm observation. The timeline shows every step — created, observation requested, evidence retrieved, resolved, condition checked, result."

Point at the TRIGGERED result and the `+1000 simulated units` credit line.

> "12.30 is below 15, so it triggered, and a simulated balance was credited — no real funds, this is StudioNet, but the mechanism is exactly what a production version would run."

### 2:30 – Show TRIGGERED and UNRESOLVED cases

**Screen: `/policies/cover-3`**

> "And here's the honest case. This policy is linked to an event where a configured source was pointed at the wrong coordinates. WeatherResolve didn't guess — it came back UNRESOLVED, plainly, with the reason visible in the Evidence Package. This policy stays pending; it can be evaluated again if the observation ever resolves. That's the whole design principle: WeatherResolve would rather say 'I don't know yet' than fabricate a number to keep the pipeline moving."

(Optional, if time: `/dashboard` with a connected wallet — "this is what a real user sees: their policies, their simulated balance.")

### 3:00 – Why GenLayer enables this

> "A deterministic contract can do the payout math perfectly — that part needs no blockchain innovation. What it cannot do is fetch a webpage and know the result is true. GenLayer lets a contract itself retrieve real-world evidence non-deterministically and only accept it once independent validators, each fetching it themselves, reach consensus. WeatherResolve turns that into reusable infrastructure — any future application, not just WeatherCover, can read the same Observation Registry without re-solving the oracle problem. That's the thing a normal smart contract, or a single-oracle design, structurally cannot offer."

---

## Verified payout lifecycle

This is the exact mechanism behind "TRIGGERED → payout credited" in the 1:45–2:30 section above, spelled out as its own flow and independently re-verified live on the canonical StudioNet deployment (`0xFd7160411e5812bD873089368b1BF687e644a959`, see `docs/CANONICAL_DEPLOYMENT.md`) during the final audit remediation pass. Useful if a judge asks "how does the payout actually work" directly.

```
Observation resolved
        ↓
Policy evaluated
        ↓
   TRIGGERED
        ↓
Simulated payout credited
        ↓
Balance updated
```

Each arrow is one real, separately-callable contract step — `resolve_weather_event` → `cover_evaluate_policy` → (contract-internal condition check) → `credited_amount` set → `simulated_balances[owner]` incremented — read back with `cover_get_policy` and `cover_get_simulated_balance`. Nothing here is simulated in the frontend layer; the crediting happens inside the contract itself.

### TRIGGERED — payout credited

Policy `cover-1`: `RAIN_24H BELOW 15.00mm` against a real resolved observation of `12.30mm`.

| Step | Result |
|---|---|
| Observation resolved | `RESOLVED`, `value_mm100: 1230` |
| Policy evaluated | `cover_evaluate_policy(cover-1)` — tx `0x7467699a4705d4a8a4faf7632661103c12320336665672cb6167bcaefcfa38d3`, `ACCEPTED` |
| Result | `status: "TRIGGERED"` (1230 < 1500) |
| Payout credited | `credited_amount: 1000` (== configured `simulated_payout`) |
| Balance updated | simulated balance for the owner: `0 → 1000` |

### NOT_TRIGGERED — no payout

Policy `cover-2`: `RAIN_24H BELOW 10.00mm` against the same `12.30mm` observation.

| Step | Result |
|---|---|
| Observation resolved | `RESOLVED`, `value_mm100: 1230` |
| Policy evaluated | `cover_evaluate_policy(cover-2)` — tx `0x557b08c36e3e8e1d59ad53da1c40a0b3d39b0bad2a241c7fb1fe55de73b91f29`, `ACCEPTED` |
| Result | `status: "NOT_TRIGGERED"` (1230 is not < 1000) |
| Payout credited | `credited_amount: 0` |
| Balance updated | unchanged — stayed at `1000` (from the TRIGGERED case above; a fresh wallet would stay at `0`) |

### UNRESOLVED — no payout

Policy `cover-3`: linked to an event whose only configured source was deliberately queried at the wrong coordinates, correctly resolving `UNRESOLVED`.

| Step | Result |
|---|---|
| Observation resolved | `UNRESOLVED`, `resolution_reason: "INSUFFICIENT_SOURCES"` |
| Policy evaluated | `cover_evaluate_policy(cover-3)` — tx `0xac943d2ef438bc4201a0c3f0f9b963406c1508b2081ee7a901e0482a2f6e4ff4`, `ACCEPTED` |
| Result | `status: "UNRESOLVED"` — no condition check is even attempted while the underlying observation isn't `RESOLVED` |
| Payout credited | `credited_amount: 0` — no credit, no denial |
| Balance updated | unchanged |

**What this proves**: the balance only ever moved once, on the one policy that genuinely satisfied its condition against a genuinely resolved observation — and stayed untouched through both the NOT_TRIGGERED and UNRESOLVED cases evaluated immediately after. The payout path is real and conditional, not decorative.

---

## If something doesn't load live

Every screen above has a static fallback: the exact JSON each page renders is reproducible with `genlayer call <contract> <method> --args ...` (commands in `docs/DEPLOYMENT.md` §4b) and can be read aloud from a terminal if the frontend or network hiccups mid-demo.
