# Frontend → Contract Trace

Exact UI action → contract call → transaction → state update path for every write flow in the frontend. File references point to the real code, so this doc can't silently drift from what's actually running.

See `docs/CANONICAL_DEPLOYMENT.md` for the current contract address, and `docs/MANUAL_SMOKE_TEST.md` for the full checklist this doc supports.

---

## Create Weather Event

```
User submits the Create Policy form with a NEW location/date/source
policy combination
        ↓
Frontend calls:
  computeEventId(location, metric, period, sourcePolicyId)   [read]
  eventExists(eventId)                                        [read]
        ↓
If it doesn't exist yet:
Frontend calls:
  createWeatherEvent(client, location, metric, period, sourcePolicyId)
        ↓
genlayer-js writes to contract method:
  event_create_weather_event(location, metric, observation_period, source_policy_id)
        ↓
Transaction submitted
        ↓
waitForFinalizedTransaction() observes ACCEPTED as in-progress, then waits for actual FINALIZED
        ↓
Contract stores a new WeatherEvent (status: PENDING) in `self.events`
        ↓
Frontend confirms the event through a latest-final `eventExists()` read before dependent writes
```

Code: `frontend/app/create-policy/page.tsx` (`handleSubmit`, "creating-event" step) → `frontend/lib/genlayer/contract.ts` (`createWeatherEvent`) → `contracts/weather_resolve_cover.py` (`event_create_weather_event`, ~line 1040).

---

## Resolve Weather Event

```
User has "Request resolution immediately" checked (default) on Create
Policy, OR the observation hasn't resolved yet when a Policy Result
page loads
        ↓
Frontend calls:
  resolveWeatherEvent(client, eventId)
        ↓
genlayer-js writes to contract method:
  resolve_weather_event(event_id)
        ↓
Transaction submitted -- this is the slow one: real gl.nondet.web
retrieval + GenLayer validator consensus happens inside this call
        ↓
Contract internally: fetches each configured source (FETCH/RENDER),
classifies retrieval status, validates location/date, extracts and
normalizes the value, checks tolerance across sources, writes an
Observation (RESOLVED or UNRESOLVED) to `self.observations`, updates
the WeatherEvent's status to match
        ↓
Frontend calls (after the tx settles):
  getObservation(eventId)                                     [read]
        ↓
UI (Evidence Explorer) renders the full Evidence Package: every
source's status, location/date match detail, normalized value, and
the overall resolution/consensus summary
```

Code: `frontend/app/create-policy/page.tsx` ("resolving-event" step) and `frontend/app/observations/[eventId]/page.tsx` (read-only view) → `frontend/lib/genlayer/contract.ts` (`resolveWeatherEvent`, `getObservation`) → `contracts/weather_resolve_cover.py` (`resolve_weather_event`, ~line 1186).

---

## Evaluate Policy

```
User clicks "Evaluate Policy" on a PENDING or UNRESOLVED policy's
result page
        ↓
Frontend calls:
  evaluateCoverPolicy(client, policyId)
        ↓
genlayer-js writes to contract method:
  cover_evaluate_policy(policy_id)
        ↓
Transaction submitted -> Pending -> Accepted (still in progress) -> actual FINALIZED
        ↓
Only after FINALIZED, re-read the updated policy from the latest-final contract state
        ↓
Contract internally: reads the linked Observation from
`self.observations`; if not RESOLVED, sets policy status to
UNRESOLVED (no credit, no denial) and returns; if RESOLVED, evaluates
BELOW/ABOVE against the resolved value, sets status to TRIGGERED or
NOT_TRIGGERED, and if TRIGGERED, credits `credited_amount` and
increments `self.simulated_balances[owner]`
        ↓
Frontend calls (after the tx settles, via useContractRead's refetch):
  getCoverPolicyDetail(policyId)                               [read]
        ↓
UI updates: the lifecycle timeline marks "Condition Checked" and
"Final Result" done, the result card shows TRIGGERED / NOT_TRIGGERED /
UNRESOLVED with its own color, and credited units if TRIGGERED
```

Code: `frontend/app/policies/[policyId]/page.tsx` (`run((c) => evaluateCoverPolicy(...))`) → `frontend/lib/genlayer/contract.ts` (`evaluateCoverPolicy`, `getCoverPolicyDetail`) → `contracts/weather_resolve_cover.py` (`cover_evaluate_policy`, ~line 1432).

---

## Create Policy (full flow, including the two steps above)

```
User clicks "Create Policy"
        ↓
Frontend calls:
  locationExists(location)                                     [read]
  (if missing) registerLocation(client, ...)                   [write: location_register_profile]
  computeEventId(...) / eventExists(...)                        [read]
  (if missing) createWeatherEvent(client, ...)                  [write: event_create_weather_event]
  (if checked) resolveWeatherEvent(client, eventId)              [write: resolve_weather_event]
        ↓
Frontend calls:
  createCoverPolicy(client, eventId, operator, thresholdMm100, simulatedPayout)
        ↓
genlayer-js writes to contract method:
  cover_create_policy(weather_event_id, operator, threshold_mm100, simulated_payout)
        ↓
Transaction submitted; on settle, contract has stored a new CoverPolicy
(status: PENDING) and returned its policy_id as the call's return value
        ↓
Frontend calls:
  listPolicyIdsByOwner(address)                                 [read]
        ↓
UI redirects to /policies/<newest policy id>
```

Code: `frontend/app/create-policy/page.tsx` (`handleSubmit`, full function) → `frontend/lib/genlayer/contract.ts` (`locationExists`, `registerLocation`, `computeEventId`, `eventExists`, `createWeatherEvent`, `resolveWeatherEvent`, `createCoverPolicy`, `listPolicyIdsByOwner`) → `contracts/weather_resolve_cover.py` (`location_register_profile`, `event_create_weather_event`, `resolve_weather_event`, `cover_create_policy`).

---

## Simulated Payout Balance

```
(Happens as a side effect of Evaluate Policy above, triggering ONLY on
TRIGGERED -- documented separately here because it's the fact most
worth tracing end to end.)

cover_evaluate_policy() determines TRIGGERED
        ↓
Contract internally:
  policy.credited_amount = policy.simulated_payout
  self.simulated_balances[owner_key] += policy.simulated_payout
        ↓
Frontend calls (Dashboard page, on load):
  getSimulatedBalance(address)                                  [read: cover_get_simulated_balance]
        ↓
UI shows the running simulated balance for the connected wallet
```

Code: `frontend/app/dashboard/page.tsx` (`balanceState`) → `frontend/lib/genlayer/contract.ts` (`getSimulatedBalance`, note the `toCalldataAddress` wrapping required for this `Address`-typed read parameter) → `contracts/weather_resolve_cover.py` (`cover_evaluate_policy`'s crediting block, `cover_get_simulated_balance`, ~line 1496).

**Important, no real funds anywhere in this trace**: `simulated_balances` is a plain `TreeMap[str, u256]` integer counter inside the contract. There is no token, no escrow account, no transfer call, and no GEN value attached to any of the above transactions (every write in this document sends `value: 0n`).

---

## What every trace above has in common

- Every write passes through `frontend/hooks/useTxAction.ts`, which refuses to treat the write call's return value (a bare transaction hash) as proof of anything — it waits for a real status, re-reads the transaction record, and only then tells the caller to re-read contract state.
- Every read passes through `frontend/hooks/useContractRead.ts` (loading/ready/error), reading directly from the deployed contract via `genlayer-js` — no backend, no cache, no intermediate database.
- Nothing in any trace above depends on a static demo ID to *function* — `frontend/lib/demo/knownData.ts` only supplies the landing page's example links and Create Policy's pre-filled defaults; every flow above works against any event/policy ID the contract actually has, including ones a user creates fresh.
