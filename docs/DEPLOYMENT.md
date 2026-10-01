# Deployment, Configuration, and Smoke Test

This project's deployment workflow is, and remains, **manual and wallet-controlled by the project owner**. Nothing in this repository — the contract, the test suite, or the frontend — deploys a contract automatically, requests a private key, or holds wallet credentials. This document exists so that stays true as the project grows.

> **Canonical address:** this project has gone through several disposable verification deployments while being built and audited. **`docs/CANONICAL_DEPLOYMENT.md` is the single source of truth** for which address is current — if anything below ever looks inconsistent with it, that document wins.

---

## 1. Contract deployment (manual, owner-performed)

Deployment is performed with the `genlayer` CLI against StudioNet, using an account already configured in the deployer's own local keystore (`genlayer account create` / `genlayer account import`, done once, outside any tool in this repo). No agent, script, or CI job in this project has generated or imported a private key. StudioNet setup transactions in this project are signed by the project owner's configured CLI account.

```bash
genlayer deploy --contract contracts/weather_resolve_cover.py --args <owner_address>
```

This prints a `Contract Address`. That address is the one value the rest of this project needs.

**Post-deploy setup** (manual, owner-signed for source policies and sources; location registration is open to any caller):

```bash
# 1. Register a Location Resolution Profile (generic infra, no location hardcoded in code)
genlayer write <contract> location_register_profile \
  --args <location_id> <canonical_name> <country> <has_coordinates> \
         <lat_hundredths> <lat_is_south> <lon_hundredths> <lon_is_west> <radius_km>

# 2. Register a Source Policy (min sources, tolerance, failure behavior)
genlayer write <contract> policy_register_source_policy \
  --args <policy_id> <min_source_count> <tolerance_mm100> <unavailable_behavior> <timeout_behavior>

# 3. Add up to 3 real evidence sources to that policy
genlayer write <contract> policy_add_source \
  --args <policy_id> <source_id> <url> <get|render> <source_class> <mm|in>
```

The exact commands used to produce the currently-deployed demo contract's data are the ones executed live during the Stage 6/7 StudioNet verification runs (see the conversation history / commit log for the literal command sequence and resulting addresses).

---

## 2. Currently deployed StudioNet contract (demo data)

See `docs/CANONICAL_DEPLOYMENT.md` for the authoritative address record. As of that document:

| Field | Value |
|---|---|
| Network | GenLayer StudioNet, chain ID `61999`, RPC `https://studio.genlayer.com/api` |
| Contract address | `0x35f33d089500d5554c803A201a19aEa9eD073022` |
| Location profile | `LAGOS_NG` (canonical name "Lagos", country "Nigeria", coordinates 6.52°N/3.38°E, radius 50km) — location registration is open to any caller |
| Source policy (RESOLVED demo) | `AUDIT_V1` — three Open-Meteo historical archive model queries, min 3, tolerance 3.50mm |
| Resolved event | `3d603813dbd7ae98` — `LAGOS_NG`/`RAIN_24H`/`2026-08-30` → **RESOLVED**, 12.30mm (12.30, 10.40, 12.30 inputs) |
| Source policy (UNRESOLVED demo) | `AUDIT_UNRES_V1` — one source deliberately queried at coordinates outside the Lagos profile radius |
| Unresolved event | `f96bbf7bf2a964ae` — `LAGOS_NG`/`RAIN_24H`/`2026-08-25` → **UNRESOLVED**, `INSUFFICIENT_SOURCES` (`WRONG_LOCATION`) |
| Demo cover policies | `cover-1` (TRIGGERED), `cover-2` (NOT_TRIGGERED), `cover-3` (UNRESOLVED) |

This is the current manually deployed verification instance. Its configuration and demonstration data were recreated and read back on the new address; see `docs/CANONICAL_DEPLOYMENT.md` for transaction evidence. The three sources are model-specific queries from the same Open-Meteo archive provider, not three independent providers. The Vercel production frontend is now configured to use this contract.

---

## 3. Frontend configuration

The frontend never hardcodes a contract address as truth — it reads one environment variable:

```bash
# frontend/.env.local (gitignored, never committed)
NEXT_PUBLIC_CONTRACT_ADDRESS=0x35f33d089500d5554c803A201a19aEa9eD073022
```

See `frontend/.env.example` for the template. To point the frontend at a different deployment (e.g. after a future manual redeploy), change only this value — no code change needed. `frontend/lib/genlayer/config.ts` reads it with a fallback to the address above, purely so local development has real data without any setup step.

`frontend/lib/demo/knownData.ts` holds the specific demo event/policy IDs listed in the table above, used by the landing page and header links. **If the contract is redeployed, this file's IDs will no longer resolve** (each deployment has independent storage) — update it to point at newly-created demo data, or remove the hardcoded links and rely on the dashboard/create-policy flow instead.

### Final frontend setup (polish pass)

The frontend is feature-complete for the demo scope: 5 pages, mobile-responsive down to a 375px viewport, and a full read/write contract integration layer. Nothing below changes the deployment model above — this section documents what "finished" means for the frontend specifically.

- **Pages**: `/` (landing), `/dashboard`, `/create-policy`, `/observations/[eventId]` (Evidence Explorer), `/policies/[policyId]` (Policy Result). All five verified against the live demo contract in a real browser, not just compiled.
- **Wallet UX states**: not connected (prompts to connect, disabled where a wallet is required) → connecting → connected (green dot + truncated address, click to disconnect) → **wrong network** (a distinct plum-colored "Wrong network — switch to StudioNet" button that calls `wallet_switchEthereumChain`/`wallet_addEthereumChain` directly, via `useWallet().switchNetwork`). No private key is ever requested or seen by this app at any state.
- **Transaction states**: every write (`event_create_weather_event`, `resolve_weather_event`, `cover_create_policy`, `cover_evaluate_policy`) passes through `useTxAction`, which visibly distinguishes **Submitted** (wallet signature pending) → **Pending** (broadcast, awaiting GenLayer consensus, tx hash shown) → **Finalized** (re-read from the transaction record, green if `ACCEPTED`/`FINALIZED`, plum otherwise) → **Failed** (wallet rejection or unreadable receipt), each with its own color and a pulsing indicator while in flight. The write is never trusted from its return hash alone — state is always re-read after settling.
- **Evidence Explorer verification flow**: an explicit 4-stage diagram — Source retrieval → Evidence validation → Observation resolution → Policy evaluation — sits above the evidence table, so the page reads as a pipeline, not a static report. Evidence rows reveal with a short staggered fade so multi-source retrieval reads as "checked one at a time," not one bulk response.
- **Mobile responsiveness**: verified at a 375×812 viewport (iPhone-class) for all 5 pages. The one real bug this pass found — evidence-row text overlapping its status badges when the source name and URL had no natural word-break points — is fixed (rows stack vertically below `sm`, `break-words` on the source name).
- **Motion**: restrained per the design decision doc — short (≤320ms) one-time fade/slide reveals on cards, timeline nodes, and evidence rows; a pulsing dot only on in-flight states; `prefers-reduced-motion: reduce` disables all of it. No looping background animation, no motion on the graph-paper canvas itself.
- **Verification commands** (both must pass before any deployment of the frontend build output): `npm run typecheck` and `npm run build` — see 4d below.

---

## 4. Smoke test instructions

### 4a. Contract-level (no frontend needed)

```bash
cd path/to/Wheatheresolve
python -m pytest tests/ -q
```

All 53 direct-mode tests should pass. This exercises the full pipeline (event registry, source policies, location profiles, resolution with real `gl.nondet.web` calls under mocked HTTP, WeatherCover) without touching a live network.

### 4b. Live StudioNet read check (no wallet needed)

```bash
genlayer call 0x35f33d089500d5554c803A201a19aEa9eD073022 observation_get_observation --args 3d603813dbd7ae98
```

Should return the RESOLVED Evidence Package with `value_mm100: 1230` and 3 `AVAILABLE` sources.

### 4c. Frontend smoke test

```bash
cd frontend
npm install
cp .env.example .env.local   # or edit NEXT_PUBLIC_CONTRACT_ADDRESS directly
npm run dev
```

Then, with no wallet connected:
1. Open `http://localhost:3000` — the landing page should render with the real 12.30mm example.
2. Navigate to **Evidence Explorer** (header link) — should show the 3 real Open-Meteo sources, all `AVAILABLE`, location/date verification both green.
3. Navigate to a known policy result, e.g. `http://localhost:3000/policies/cover-1` — should show `TRIGGERED` with a 1000-unit simulated credit.

With a wallet connected (MetaMask or compatible):
4. Connect on a network other than StudioNet first — the header should show a plum "Wrong network — switch to StudioNet" button; clicking it should prompt the wallet to switch (or add) StudioNet and clear the warning once done.
5. **Dashboard** — should show that wallet's real on-chain policies (empty for a fresh wallet).
6. **Create Policy** — submit the form; each step (event check → event creation if needed → resolution → policy creation) should show a live Submitted → Pending → Finalized transaction status, then redirect to the new policy's result page.
7. On the new policy's result page, click **Evaluate Policy** — should show the same transaction-state sequence, then display TRIGGERED, NOT_TRIGGERED, or UNRESOLVED depending on the real resolved observation.

### 4c-1. Mobile check

Resize the browser (or use device emulation) to a ~375px-wide viewport and repeat steps 1–3. The header should collapse to a compact scrollable nav row, hero/CTA buttons should stack full-width, and every Evidence Explorer source row should show its name, badges, and value on their own lines with no overlapping text.

### 4d. Type/build check

```bash
cd frontend
npm run typecheck
npm run build
```

Both should complete without errors before any deployment of the frontend itself (e.g. to a static host — this app has no server component of its own, so any static/Node hosting works; see next.config.ts).

---

## 5. What this project will never do on its own

- Generate, import, request, or store a private key.
- Deploy a contract without the owner explicitly running the `genlayer deploy` command themselves.
- Sign a transaction on the owner's behalf outside of the owner's own connected wallet extension (for frontend writes) or the owner's own CLI keystore (for infrastructure setup).
- Stand up a backend, database, or external service — every read in the frontend goes directly to the deployed contract via `genlayer-js`.

Final production deployment, and any change to the currently-deployed demo contract's configuration, remains a manual action performed by the project owner with their own wallet.
