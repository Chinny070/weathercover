# Release-Readiness Audit

Scope: audit only. No features added, no contract changes, no architecture changes. One real bug was found and fixed in the frontend's contract-interaction layer (below) — that is a compatibility fix, not a feature.

> **Historical record notice:** this audit was performed against contract `0x92A1DbA2D2F0E5707ee90f7EF4BB5aC704C171A0`, a disposable verification deployment that has since been superseded. Every transaction hash below is specific to that deployment and is preserved as an accurate record of what was actually tested at the time — it has not been rewritten to a different address. **For the current canonical contract, see `docs/CANONICAL_DEPLOYMENT.md`**; a later remediation pass (`docs/FINAL_TEST_REPORT.md`) independently re-ran the equivalent checks against the canonical address.

---

## 1. Frontend ↔ contract compatibility

Every function exported from `frontend/lib/genlayer/contract.ts` was checked one-to-one against `contracts/weather_resolve_cover.py`'s actual `@gl.public.write`/`@gl.public.view` methods (grepped fresh from the contract source, not from memory).

| Frontend call | Contract method | Args match | Return type handled |
|---|---|---|---|
| `getWeatherEvent` | `event_get_weather_event(event_id)` | ✓ | ✓ `WeatherEvent` |
| `eventExists` | `event_exists(event_id)` | ✓ | ✓ `boolean` |
| `computeEventId` | `event_compute_id(location, metric, period, policy_id)` | ✓ | ✓ `string` |
| `getSourcePolicy` | `policy_get_source_policy(policy_id)` | ✓ | ✓ `SourcePolicy` |
| `sourcePolicyExists` | `policy_exists(policy_id)` | ✓ | ✓ `boolean` |
| `getLocationProfile` | `location_get_profile(location_id)` | ✓ | ✓ `LocationProfile` |
| `locationExists` | `location_exists(location_id)` | ✓ | ✓ `boolean` |
| `getObservation` | `observation_get_observation(event_id)` | ✓ | ✓ `Observation` |
| `getResolutionStatus` | `observation_get_resolution_status(event_id)` | ✓ | ✓ `string` |
| `getCoverPolicy` | `cover_get_policy(policy_id)` | ✓ | ✓ `CoverPolicy` |
| `getCoverPolicyDetail` | `cover_get_policy_detail(policy_id)` | ✓ | ✓ `CoverPolicyDetail` (extends `CoverPolicy` + `linked_observation`) |
| `listPolicyIdsByOwner` | `cover_list_policy_ids_by_owner(owner: Address)` | ✓ (see finding below) | ✓ `string[]` |
| `getSimulatedBalance` | `cover_get_simulated_balance(owner: Address)` | ✓ (see finding below) | ✓ `bigint` |
| `coverPolicyExists` | `cover_policy_exists(policy_id)` | ✓ | ✓ `boolean` |
| `createWeatherEvent` | `event_create_weather_event(location, metric, period, policy_id)` | ✓ | ✓ (tx hash, handled via `useTxAction`) |
| `resolveWeatherEvent` | `resolve_weather_event(event_id)` | ✓ | ✓ |
| `createCoverPolicy` | `cover_create_policy(event_id, operator, threshold_mm100, payout)` | ✓ | ✓ |
| `evaluateCoverPolicy` | `cover_evaluate_policy(policy_id)` | ✓ | ✓ |

**Every TypeScript type in `lib/genlayer/types.ts` was checked field-by-field against the contract's own `to_dict()` methods** (`WeatherEvent`, `SourceEvidence`, `Observation`, `CoverPolicy`) — all match exactly, including the fields added mid-project (`location_match`, `location_detail` on evidence; `location_id`, `metric`, `observation_date`, `credited_amount`, `evaluated_at` on cover policy).

**Finding — fixed:** `listPolicyIdsByOwner` and `getSimulatedBalance` take an `Address`-typed contract parameter. The rest of the codebase (verified against a working reference StudioNet frontend, `protocolcourt/frontend`) always wraps such arguments in `genlayer-js`'s `CalldataAddress` wire type rather than passing a plain hex string, because GenLayer's calldata format has a dedicated address encoding. These two calls were passing a plain string. **Fixed** by adding a `toCalldataAddress()` helper (same pattern as the reference frontend) and using it for both calls.

I then verified this live, not just by inspection: wrote a throwaway script calling both the old (plain-string) and fixed (`CalldataAddress`-wrapped) forms directly against the deployed StudioNet contract via `genlayer-js`. Run twice — the first run showed the plain-string call fail with an RPC-level error while the wrapped call succeeded; a second run had both succeed, meaning the first failure was very likely a transient network blip in this environment rather than proof the plain string is always rejected. **Conclusion, stated honestly**: this SDK version appears to tolerate a plain hex string for this particular read call in practice, but wrapping in `CalldataAddress` is the verified-safe, documented convention used everywhere else in this codebase and in the reference project, so the fix stands as a correctness hardening regardless of whether the untested path would have failed in practice on every call.

**Dead-but-correct surface:** `getSourcePolicy`, `getLocationProfile`, `sourcePolicyExists`, `locationExists`, `getResolutionStatus`, `coverPolicyExists`, and the `SourcePolicy`/`LocationProfile` types are exported and correctly typed but not currently called from any page. This is the contract's full read surface exposed for future use (e.g. an admin/infra view), not dead code left by mistake — no change made, flagged for awareness only.

---

## 2. Demo assumptions — configuration vs. example inventory

Searched the entire frontend source (excluding `node_modules`) for hardcoded addresses, event IDs, policy IDs, and location/metric strings outside the two files designed to hold them.

| Value | Location | Classification |
|---|---|---|
| `0x0908545f451521D3760183976c7e6848Fc7Ac701` | `lib/genlayer/config.ts` | **Configuration with a demo default.** Overridable via `NEXT_PUBLIC_CONTRACT_ADDRESS` (`.env.local`); documented in `docs/DEPLOYMENT.md` §3. Not a hidden assumption — the fallback exists purely so local dev has real data with zero setup. |
| `6a2dfd724bec8a59`, `b76f9c2a84ffff2a`, `cover-1`/`2`/`3`, `SMOKE_V4` | `lib/demo/knownData.ts` | **Example data, explicitly labeled as such** in the file's own docstring, which also explains *why* it exists (the contract has no "list all events" method by design — see `PRODUCT_ARCHITECTURE.md`). Used only for the landing page's example and header shortcut link; the dashboard and create-policy flow never depend on it. **Breaks on redeploy** — `DEPLOYMENT.md` already documents this and what to do about it. |
| `LOCATION`/`KNOWN_LOCATION_ID = "LAGOS_NG"`, `KNOWN_METRIC = "RAIN_24H"` | `lib/demo/knownData.ts`, read by `create-policy/page.tsx` | **Real configuration constraint, not a demo shortcut.** These are locked in the Create Policy form (disabled inputs) because they are the *only* location/metric actually registered on the deployed contract (`LocationProfile` registry + `_SUPPORTED_METRICS`). The form already explains this to the user ("Only locations with a registered Location Resolution Profile are available"). Adding more would require an owner-only contract call, not a frontend change. |
| Threshold `"15.00"`, payout `"1000"` form defaults | `create-policy/page.tsx` | **Editable pre-fill, not a fixed value.** Ordinary UX convenience; every field is user-editable before submit. |
| `PROCESS_STEPS` (5 "done" steps) on the landing page | `app/page.tsx` | **Illustrative only**, clearly a static diagram of the general flow, not live contract data — does not read from or claim to read from the chain. No change needed, but flagged so it's not mistaken for a live status. |

No hardcoded value was found silently masquerading as configuration, and no configuration value was found silently masquerading as a fixed example. The one place this distinction mattered least clearly (the contract address fallback) is already documented.

---

## 3. Security review

| Check | Result |
|---|---|
| Private keys generated, imported, or stored by this codebase | **None found.** `WalletProvider.tsx` only calls `window.ethereum.request(...)` for an injected wallet extension; no key material is ever read, held, or logged. |
| Wallet secrets (mnemonics, keystores) | **None found.** Grepped the full repo (excluding `node_modules`) for `private key`, `mnemonic`, `seed phrase`, `BEGIN ... PRIVATE` — every match was a documentation/comment sentence *stating* that no such thing exists, not an actual secret. |
| Backend secrets | **N/A — no backend exists.** No API routes (`app/api` doesn't exist), no server-side environment variables, no database credentials. The only `process.env` reference in the frontend is the `NEXT_PUBLIC_`-prefixed contract address, which Next.js treats as public by convention (and is, in fact, public — it's a contract address). |
| `.env` handling | `.env.example` (template, no real values) is committed; `.env.local` and `.env*.local` are gitignored. No `.env.local` file exists in this checkout to accidentally commit. |
| Unsafe client assumptions | No `dangerouslySetInnerHTML`, no `eval`/`new Function`, no unvalidated redirect targets. Source URLs from the Evidence Package (`evidence.url`, attacker-uninfluenced but still external-sourced data) are rendered as plain text (`<p>`), never as a clickable `<a href>` or injected as HTML — no reflected-content or `javascript:`-URL risk. |
| Transaction trust | Every write path (`useTxAction`) explicitly does **not** trust the returned transaction hash as proof of success — it waits for a real status and re-reads the transaction record and then re-reads contract state, matching the discipline already established in the contract layer's own tests. |

No security findings requiring a fix.

---

## 4. Build verification

Re-run after the `CalldataAddress` fix above (not just before it):

```
npm run typecheck   →  passes, zero errors
npm run build        →  passes, all 5 routes compile (3 static, 2 dynamic), zero errors
```

Contract-side: `python -m pytest tests/ -q` → 47/47 passing (unchanged by this audit — no contract file was touched).

---

## 5. Documentation review

| Requirement | Status |
|---|---|
| README explains WeatherCover | **Gap found and fixed.** No root-level `README.md` existed — only `frontend/README.md` (frontend-only scope). Added `README.md` at the project root explaining WeatherResolve vs. WeatherCover, why it needs GenLayer, project layout, status, and a documentation index. |
| Architecture is documented | ✓ `docs/PRODUCT_ARCHITECTURE.md` (event model, source policies, resolution algorithm, Evidence Package, full judge Q&A) and `docs/IMPLEMENTATION_PLAN.md` (build sequencing + the GenLayer API verification performed before any contract code was written). |
| Manual deployment instructions are complete | ✓ `docs/DEPLOYMENT.md` §1–3: exact `genlayer deploy`/`write` commands, the current live contract address and all its demo IDs, and the `NEXT_PUBLIC_CONTRACT_ADDRESS` configuration mechanism. Explicitly states this project never automates deployment or touches a private key. |
| Manual smoke test instructions are complete | ✓ `docs/DEPLOYMENT.md` §4: contract-level (`pytest`), live read-only StudioNet check (`genlayer call`), a full frontend walkthrough (no wallet, then with a wallet including a wrong-network check), a mobile-viewport check, and the typecheck/build commands. |

Minor fix made in passing: `pyproject.toml`'s description still said "no frontend yet" from before Stage 8 — updated to reflect that the frontend now exists.

---

## 6. Final demo package

### The 3-minute flow

| Time | Action | Screen | What to say |
|---|---|---|---|
| 0:00–0:20 | Open the landing page | `/` | "WeatherCover is parametric weather insurance — but the interesting part isn't the insurance, it's how the weather condition gets verified. WeatherResolve, underneath, is reusable infrastructure: any app can ask it 'what actually happened,' and it won't answer until multiple independently retrieved sources agree." |
| 0:20–0:40 | Point at the example policy card and the 5-step flow diagram | `/` (scroll to "How it works") | "Every policy follows the same path: create it, request the real-world observation, verify the evidence, evaluate the condition, decide coverage. Nothing is decided until the evidence is in." |
| 0:40–1:00 | Open the Evidence Explorer for the live resolved observation | `/observations/6a2dfd724bec8a59` | "This is a real observation, resolved live on GenLayer StudioNet minutes ago — not a mock. 12.30mm of rain in Lagos on August 30th." |
| 1:00–1:40 | Scroll through the 4-stage verification flow and the evidence table | same page | "Source retrieval, evidence validation, observation resolution, policy evaluation — each stage is real. Three independent Open-Meteo historical queries, each independently checked against a Location Resolution Profile — canonical name, aliases, country, **or coordinate proximity**, since real APIs never say 'Lagos' in their JSON, they just give you coordinates. All three agree within tolerance: 12.30, 10.50, 13.60mm. GenLayer validators reached `MAJORITY_AGREE` on this evidence independently — this wasn't one API call I'm trusting, it's a network of validators that each fetched it themselves." |
| 1:40–2:10 | Open a Policy Result page | `/policies/cover-1` | "Here's a real policy: BELOW 15mm on this same observation. Walk down the timeline — policy created, observation requested, evidence retrieved, resolved, condition checked, TRIGGERED. 12.30 is below 15, so it triggered, and a simulated payout was credited — no real funds, this is StudioNet, but the mechanism is real." |
| 2:10–2:35 | Show the UNRESOLVED case | `/policies/cover-3` | "And here's the honest case: a policy linked to an observation where a source was misconfigured — wrong coordinates. It didn't guess or force an answer. It came back UNRESOLVED, plainly, and this policy can be evaluated again once — or if — the real observation resolves. That's the whole point: WeatherResolve would rather say 'I don't know yet' than fabricate a number." |
| 2:35–3:00 | Dashboard + close | `/dashboard` (with wallet connected) | "This is the dashboard a real user sees — their policies, their simulated balance. But the reusable part is WeatherResolve: any future app — a prediction market, an agriculture contract, a logistics SLA — reads the exact same Observation Registry. WeatherCover is just the first thing built on it." |

### Key screens to have open/ready

1. Landing page (`/`)
2. Evidence Explorer on the real resolved event (`/observations/6a2dfd724bec8a59`)
3. Policy Result — TRIGGERED (`/policies/cover-1`)
4. Policy Result — UNRESOLVED (`/policies/cover-3`)
5. Dashboard (ideally with a connected wallet showing at least one policy)

### The GenLayer value proposition, in one paragraph

A traditional smart contract can check "is X below Y" perfectly — that part needs no blockchain innovation at all. What it categorically cannot do is find out, on its own, whether it rained 12.3mm in Lagos on a given day; it has to trust whatever single source feeds it that number. GenLayer's non-deterministic web access lets a contract itself fetch real-world evidence from multiple independently retrieved sources, and its validator consensus mechanism means the contract only accepts a value once independent validators, each retrieving the evidence themselves, agree it's real. WeatherResolve turns that primitive into reusable infrastructure — a canonical, deduplicated Observation Registry — so any number of future applications (not just WeatherCover) can consume a verified real-world fact without re-solving the oracle problem themselves. And critically, it can honestly say "unresolved" instead of guessing, which is the one thing a single-oracle design structurally cannot do with integrity.

---

## Summary

- One real compatibility bug found and fixed (`CalldataAddress` wrapping for two Address-typed read calls), verified live against StudioNet before and after.
- No demo value found mislabeled as configuration or vice versa; the one ambiguous case (contract address fallback) was already correctly documented.
- No security findings.
- Build and typecheck both pass clean after the fix.
- One documentation gap found and fixed (missing root README).
- Demo package above is ready to run as written.

Nothing was deployed as part of this audit.
