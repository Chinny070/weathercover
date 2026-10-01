# Release Freeze

This document freezes the exact state of the codebase that is approved for manual StudioNet deployment. The contract source, once you deploy it, must be byte-identical to the file whose hash is recorded below — if you edit `contracts/weather_resolve_cover.py` after this freeze, recompute the hash before deploying and update this document.

---

## Final contract source hash

```
File: contracts/weather_resolve_cover.py
SHA-256: d1f8a35a7ed7599bbe0192a1aecdde2d1a413dc8d3c398fa3c0378ee25642d21
Lines: 1544
```

Reproduce with:
```bash
sha256sum contracts/weather_resolve_cover.py
```
(or `Get-FileHash contracts/weather_resolve_cover.py -Algorithm SHA256` on PowerShell)

## Final frontend build status

```
npm run typecheck   →  PASS (0 errors)
npm run lint        →  PASS (0 errors; 2 non-blocking dashboard hook-dependency warnings)
npm run build        →  PASS (5/5 routes generated, 0 errors)
```

Routes: `/` (static), `/dashboard` (static), `/create-policy` (static), `/observations/[eventId]` (dynamic), `/policies/[policyId]` (dynamic).

## Test results

```
python -m pytest tests/ -q   →  53 passed, 0 failed (1 non-failing local cache-permission warning)
```

Coverage: Weather Event Registry (creation, dedup, validation), Source Policy Registry (registration, source config, immutability lock), Location Resolution Profile Registry (canonical name/alias/country/coordinate matching, disambiguation), resolution pipeline (real `gl.nondet.web` calls under mocked HTTP via `gltest`'s `mock_web`, all retrieval-status branches, GenLayer fidelity-judgment path via `run_validator()`), and WeatherCover (policy creation, evaluation, dedup, UNRESOLVED handling, simulated balances).

Contract lint/syntax: `python -m py_compile contracts/weather_resolve_cover.py` → PASS. (No `ruff`/`flake8` is installed in this environment; `py_compile` is the available syntax gate — documented as a known tooling limitation, not a skipped check.)

## Deployment environment

| Setting | Value |
|---|---|
| Network | GenLayer StudioNet only |
| Chain ID | `61999` |
| RPC | `https://studio.genlayer.com/api` |
| Runner pin | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` (contract's own `# {"Depends": ...}` header) |
| `genlayer-js` | `^1.1.8` |
| Next.js | `16.3.5` |
| React | `19.2.8` |

This is the **only** network this project targets or has ever been verified against. No multi-network logic exists anywhere in the contract, tests, or frontend.

## Known limitations

- **Location matching is text/coordinate-based, not a full geocoding system.** A source must mention the registered canonical name, an alias, canonical-name-and-country together, or fall within a configured coordinate radius. A real source phrased in an unanticipated way (e.g. a name not registered as an alias) can be misclassified `WRONG_LOCATION` even though it's genuinely about the right place. This is a deliberate MVP scope limit, not an oversight — see `docs/PRODUCT_ARCHITECTURE.md` §21.3 and the Location Resolution Profile design in `SUBMISSION_ARCHITECTURE.md`.
- **Numeric extraction is a generic heuristic** (last decimal token remaining after masking the date/location/coordinate tokens), tuned against real structured JSON weather APIs (Open-Meteo). It is not guaranteed to correctly extract a value from arbitrary unstructured HTML.
- **RENDER-mode (`gl.nondet.web.render`) reliability against real dynamic pages is unverified beyond one negative data point** — a real StudioNet run against a live dynamic weather page (timeanddate.com) returned `RENDER_FAILED` for reasons the contract's error handling correctly swallows but does not expose further. FETCH-mode against structured APIs is the verified-reliable path; RENDER exists and is tested against mocked HTTP, but has not been proven reliable against a real, JS-dependent page.
- **No "list all events" or "list all policies" contract method** — by design (see `PRODUCT_ARCHITECTURE.md`, WeatherResolve is a keyed registry, not an indexed feed). The frontend's landing-page example and header shortcut depend on hardcoded demo IDs (`frontend/lib/demo/knownData.ts`) that are specific to whichever contract deployment created them, and will need updating after a redeploy (see `MANUAL_DEPLOYMENT.md` §6).
- **A bare country name is never accepted as sufficient location evidence** — a deliberate disambiguation design choice (e.g. "Lagos, Portugal" must not satisfy a Lagos, Nigeria policy), documented and tested, but means a source policy naming only a country will never resolve.
- **Wallet support is limited to `window.ethereum`-injected providers** (MetaMask or compatible). No WalletConnect or other connector is implemented.
- **Maximum 3 sources per source policy** — a contract-enforced constant (`MAX_SOURCES_PER_POLICY`), a deliberate MVP scope limit, not a bug.

## Intentionally excluded features

These were explicitly out of scope for this release, not overlooked:

- Additional weather metrics beyond `RAIN_24H` (architecture supports adding them later; none implemented).
- Additional locations beyond whatever is registered on the deployed contract. Any caller can register a Location Resolution Profile through the frontend's Create Policy flow; source-policy configuration remains owner-controlled.
- Real funds, escrow, or tokenized payouts of any kind — simulated integer balances only.
- A frontend admin UI for registering source policies and sources — these remain owner-only `genlayer write` calls performed manually via the CLI. Location profiles can be registered by any caller through the Create Policy flow.
- Splitting WeatherResolve and WeatherCover into two separately-deployed contracts — deferred until cross-contract-call patterns are independently verified (see `IMPLEMENTATION_PLAN.md` §1).
- Automated or CI-driven deployment of any kind.
- Any backend, database, or server-side component — the frontend reads/writes the contract directly from the browser.
- Analytics, notifications, historical charting, or any dashboard feature beyond the five pages specified in the product brief.

---

**Status: FROZEN FOR MANUAL DEPLOYMENT.** This source includes the validator binding for persisted location-verification fields; manually redeploy it before representing that specific follow-up as live on StudioNet.
