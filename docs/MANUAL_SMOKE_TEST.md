# Manual Post-Deployment Smoke Test

Run this checklist in order, against your freshly deployed contract, after completing [`docs/MANUAL_DEPLOYMENT.md`](MANUAL_DEPLOYMENT.md). Every step is something **you** perform with your own wallet/CLI keystore — nothing here is automated.

---

## Contract verification

Run these with the `genlayer` CLI, in order. Each depends on the previous step succeeding.

- [ ] **Contract deployed** — `genlayer deploy` returned a `Contract Address` with no error (§4 of `MANUAL_DEPLOYMENT.md`).
- [ ] **Schema check** — the contract responds to a basic read call:
  ```bash
  genlayer schema <contract_address>
  ```
  Should list the contract's methods (`event_create_weather_event`, `cover_evaluate_policy`, etc.) without error.
- [ ] **Create location/source policy if required** — confirm both exist (skip if already done in `MANUAL_DEPLOYMENT.md` §4a/§8):
  ```bash
  genlayer call <contract_address> location_exists --args LAGOS_NG
  genlayer call <contract_address> policy_exists --args SMOKE_V1
  ```
  Both must return `true` before continuing.
- [ ] **Create weather event**:
  ```bash
  genlayer write <contract_address> event_create_weather_event --args LAGOS_NG RAIN_24H <YYYY-MM-DD> SMOKE_V1
  ```
  Use a date **at least one full day in the past** relative to today — `resolve_weather_event` rejects a date whose observation window hasn't ended yet.
- [ ] **Compute and note the event ID**:
  ```bash
  genlayer call <contract_address> event_compute_id --args LAGOS_NG RAIN_24H <YYYY-MM-DD> SMOKE_V1
  ```
- [ ] **Resolve weather observation**:
  ```bash
  genlayer write <contract_address> resolve_weather_event --args <event_id>
  ```
  This performs real `gl.nondet.web` retrieval against your configured sources — expect it to take longer than other writes (validator consensus over live web calls).
- [ ] **Verify Observation Registry result**:
  ```bash
  genlayer call <contract_address> observation_get_observation --args <event_id>
  ```
  Confirm the response has `"status": "RESOLVED"` (or a legitimate `"UNRESOLVED"` with a specific `resolution_reason` — see the UNRESOLVED check below) and that `evidence` lists each configured source with a real `retrieval_status`.
- [ ] **Create WeatherCover policy**:
  ```bash
  genlayer write <contract_address> cover_create_policy --args <event_id> BELOW <threshold_mm100> <simulated_payout>
  ```
  e.g. `--args <event_id> BELOW 1500 1000` for a "BELOW 15.00mm, payout 1000 units" policy.
- [ ] **Evaluate policy**:
  ```bash
  genlayer write <contract_address> cover_evaluate_policy --args <policy_id>
  ```
- [ ] **Verify TRIGGERED result** — create a policy whose threshold the resolved value satisfies (e.g. `BELOW` a value higher than the resolved mm), evaluate it, then:
  ```bash
  genlayer call <contract_address> cover_get_policy --args <policy_id>
  ```
  Confirm `"status": "TRIGGERED"` and `"credited_amount"` equals the configured payout.
- [ ] **Verify NOT_TRIGGERED result** — create a second policy whose threshold the resolved value does *not* satisfy, evaluate it, confirm `"status": "NOT_TRIGGERED"` and `"credited_amount": 0`.
- [ ] **Verify UNRESOLVED result** — either evaluate a policy before its event resolves, or deliberately register a source policy with a source that will fail (wrong coordinates, unreachable URL, etc.), resolve that event, create/evaluate a policy against it, and confirm `"status": "UNRESOLVED"` with a specific `resolution_reason` in the linked observation (`INSUFFICIENT_SOURCES`, `DISAGREEMENT`, etc.) — not a generic error.

---

## Frontend verification

Requires `frontend/.env.local` pointed at your deployed address (§6 of `MANUAL_DEPLOYMENT.md`) and `npm run build`/`npm run dev` already run against it.

- [ ] **Connect wallet** — open the app, click "Connect Wallet" in the header; your wallet extension prompts for connection.
- [ ] **Switch to StudioNet** — if your wallet is on a different network, the header shows a plum "Wrong network — switch to StudioNet" button; click it and confirm the prompt in your wallet. The button should disappear once switched.
- [ ] **Dashboard loads** — `/dashboard` shows a loading state, then either your real policies or an empty state (never a blank crash).
- [ ] **Policies display** — each policy card shows location, condition, observation date, observed value (or "not yet resolved"), and status, matching what `cover_get_policy`/`observation_get_observation` return for the same IDs via the CLI.
- [ ] **Evidence Explorer loads** — navigate to `/observations/<event_id>` for the event you resolved above.
- [ ] **Observation details display** — the page shows the resolved value (or UNRESOLVED reason), the 4-stage verification flow, every configured source with its retrieval status and location/date match detail, and the resolution/consensus summary — cross-check against the CLI's `observation_get_observation` output; they must match exactly.
- [ ] **Create policy flow works** — with a wallet connected, submit the Create Policy form; watch it progress through event-check → (event creation if needed) → resolution → policy creation, then land on the new policy's result page.
- [ ] **Evaluate policy transaction works** — on a `PENDING`/`UNRESOLVED` policy's result page, click "Evaluate Policy"; it should complete and update the displayed status.
- [ ] **Transaction states display correctly** — during both write flows above, confirm you visibly see, in order: **Submitted** (wallet signature prompt) → **Pending** (broadcast, tx hash shown) → **Finalized** (green if accepted) or **Failed** (plum, with an error message) — never a silent hang with no state shown.

---

## If a step fails

Stop at the first failing step and do not proceed to later steps that depend on it (the checklist above is ordered by dependency). Re-read the specific write/read command's output for the exact `EXPECTED:*` revert reason from the contract (these are self-explanatory, e.g. `EXPECTED:OBSERVATION_WINDOW_NOT_ENDED`), and consult `docs/PRODUCT_ARCHITECTURE.md` or `docs/SUBMISSION_ARCHITECTURE.md` for what that stage is supposed to do before retrying.
