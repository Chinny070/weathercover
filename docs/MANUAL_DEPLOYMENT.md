# Manual StudioNet Deployment

This document is written for **you** to perform the deployment yourself. Nothing in this repository deploys automatically, accesses a wallet, requests a private key, creates a wallet, or signs a transaction on your behalf. Every step below is a command you run, with your own wallet, on your own machine.

```
Build → Final verification → Freeze release → Manual deployment (you) → Manual smoke test (you)
```

This document covers the first four arrows up to the point of deployment. See [`docs/MANUAL_SMOKE_TEST.md`](MANUAL_SMOKE_TEST.md) for the fifth. See [`docs/RELEASE_FREEZE.md`](RELEASE_FREEZE.md) for the exact frozen source hash and verification results this deployment should match.

---

## 1. Prerequisites

- A GenLayer account already configured in your own local `genlayer` CLI keystore (`genlayer account create` or `genlayer account import`), funded with test GEN on StudioNet. This project never sets this up for you.
- A browser wallet extension (MetaMask or compatible) if you intend to use the frontend for policy creation/evaluation after deployment — separate from the CLI keystore above.
- Node.js (for the frontend) and Python 3.12+ (for the contract/tests) installed locally.

## 2. Required tools

| Tool | Purpose | Verify with |
|---|---|---|
| `genlayer` CLI | Deploy the contract, register infrastructure, run manual writes/reads | `genlayer --version` |
| `python` + `pytest` + `gltest` (genlayer-test) | Run the direct-mode test suite before deploying | `python -m pytest tests/ -q` |
| `node` + `npm` | Build and run the frontend | `node --version` |

## 3. StudioNet-only configuration

This project targets **StudioNet exclusively** — no other network is supported by the contract, the tests, or the frontend.

| Setting | Value |
|---|---|
| Network alias | `studionet` |
| Chain ID | `61999` (hex `0xf22f`) |
| RPC | `https://studio.genlayer.com/api` |

Confirm your CLI is pointed at StudioNet before deploying:

```bash
genlayer network list
genlayer network set studionet   # if it isn't already selected
genlayer network info            # confirm chainId 61999, the RPC above
```

## 4. Contract deployment steps

Run from the repository root. Replace `<your_address>` with your own account's address (the contract's `owner` — the only address permitted to register source policies and location profiles afterward).

```bash
genlayer deploy --contract contracts/weather_resolve_cover.py --args <your_address>
```

The CLI prints a `Transaction Hash` and a `Contract Address` on success. **Capture the Contract Address** — see §5.

### 4a. Post-deploy infrastructure setup (owner-only, still manual)

These are the same owner-only contract calls used throughout this project's own verification runs. Run them against your new contract address:

```bash
# Register a location (example: Lagos, Nigeria, with coordinates for coordinate-proximity matching)
genlayer write <contract_address> location_register_profile \
  --args LAGOS_NG Lagos Nigeria true 652 false 338 false 50

# Register a source policy: id, min_source_count, disagreement_tolerance_mm100, unavailable_behavior, timeout_behavior
genlayer write <contract_address> policy_register_source_policy \
  --args SMOKE_V1 3 350 SKIP SKIP

# Add up to 3 real evidence sources to that policy
genlayer write <contract_address> policy_add_source \
  --args SMOKE_V1 <source_id> "<url>" <get|render> <source_class> <mm|in>
```

Repeat `policy_add_source` for each of up to 3 sources (contract-enforced maximum). See `docs/PRODUCT_ARCHITECTURE.md` §5 for source policy design and `docs/DEPLOYMENT.md` §1 for the exact commands used to build the existing demo policies, as a reference.

## 5. How to capture the deployed contract address

The `genlayer deploy` output includes a JSON-like result block:

```
Result:
{
  'Transaction Hash': '0x...',
  'Contract Address': '0x...'
}
```

Copy the `Contract Address` value exactly (with `0x` prefix, checksummed casing as printed). This is the only value the rest of this workflow needs.

## 6. How to update frontend environment variables

The frontend reads exactly one environment variable for this — no code change is needed.

```bash
cd frontend
cp .env.example .env.local     # if you don't already have one
```

Edit `frontend/.env.local`:

```bash
NEXT_PUBLIC_CONTRACT_ADDRESS=<your deployed contract address>
```

**Note on demo data:** `frontend/lib/demo/knownData.ts` hardcodes event/policy IDs from a *previous* deployment (documented in `docs/DEPLOYMENT.md` §2/§3). Those IDs will not resolve against your new contract until you create equivalent events/policies on it. The landing page's example links and header shortcut will 404/error until then — this does not affect the dashboard or create-policy flow, which work against any deployment immediately. Update `knownData.ts` with your new IDs once you've created a demo event/policy on the new deployment, or leave it as-is if you don't need the landing-page shortcut links to resolve.

## 7. Frontend build after address update

```bash
cd frontend
npm install        # if not already installed
npm run typecheck
npm run build
```

Both must pass with zero errors before serving the build. `next build` embeds `NEXT_PUBLIC_CONTRACT_ADDRESS` at build time — **rebuild after changing `.env.local`**, a dev server (`npm run dev`) picks up the change on restart without a full build.

## 8. Verification commands (post-deploy, before smoke test)

Run these read-only checks against your new contract address before moving to the full smoke test:

```bash
# Confirm the contract responds and the owner is correct
genlayer call <contract_address> location_exists --args LAGOS_NG

# Confirm a registered source policy exists
genlayer call <contract_address> policy_exists --args SMOKE_V1
```

Both should return `true` if §4a was completed. If either returns `false` or errors, do not proceed to the smoke test — re-run the corresponding `genlayer write` command from §4a.

Once these pass, continue to [`docs/MANUAL_SMOKE_TEST.md`](MANUAL_SMOKE_TEST.md).
