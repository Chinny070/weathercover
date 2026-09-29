# WeatherCover Frontend

A parametric weather coverage application built on **WeatherResolve**, a real-world observation resolution layer on GenLayer. This is a frontend only — see `../docs/DEPLOYMENT.md` for the manual, wallet-controlled deployment workflow and current StudioNet contract address.

## What this is not

Not a weather API dashboard. It does not show you one provider's number. Every observation behind a policy was independently retrieved from multiple real sources, checked against a Location Resolution Profile and the requested date, and only resolved once GenLayer validators reached consensus — see the Evidence Explorer.

## Setup

```bash
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_CONTRACT_ADDRESS if not using the default demo deployment
npm run dev
```

## Design system

See `../docs/FRONTEND_DESIGN_DECISION.md` — Modern Treasury-inspired ("treasury ledger on graph paper"), all tokens in `app/globals.css`.

## Architecture

- `lib/genlayer/config.ts` — StudioNet client + contract address (env-configurable)
- `lib/genlayer/contract.ts` — typed read/write functions, one per contract method actually used
- `lib/genlayer/types.ts` — TypeScript mirrors of the contract's `to_dict()` shapes
- `lib/wallet/WalletProvider.tsx` — wallet connect/chain-switch, no private key ever touches this app
- `hooks/useContractRead.ts` — read-state hook (loading/ready/error)
- `hooks/useTxAction.ts` — write-transaction state machine (idle/submitted/pending/finalized/failed)
- `lib/demo/knownData.ts` — the demo StudioNet event/policy IDs this environment points at by default

No backend, no database, no Supabase, no server code of this app's own — every read/write goes directly from the browser to the deployed Intelligent Contract via `genlayer-js`.
