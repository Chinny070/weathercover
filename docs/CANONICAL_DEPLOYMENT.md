# Canonical Deployment

This is the **single source of truth** for which contract address this project currently points at. Earlier working sessions deployed multiple disposable verification contracts while the product was being built and audited (documented in `docs/DEPLOYMENT.md`'s history and `docs/AUDIT.md`); this document exists so there is exactly one address to treat as authoritative going forward, instead of three.

---

```
Contract name:       WeatherResolveCover
Network:             GenLayer StudioNet
Chain ID:            61999
RPC:                 https://studio.genlayer.com/api
Contract address:    0x8a07659C329e1e1d865667A23745d472a696b073
Deployment commit:   c310b6df272469c9b17211ccb2f334c4b92f2e6f
                      ("Open location registration to any caller")
Deployment tx hash:  not captured in this repo's records -- deployed
                      manually by the project owner through the GenLayer
                      Studio web IDE rather than the `genlayer` CLI, so
                      no deploy-tx hash was logged here. Visible on the
                      contract's own page in GenLayer Studio / the
                      StudioNet explorer if needed.
Frontend env var:    NEXT_PUBLIC_CONTRACT_ADDRESS (see
                      frontend/.env.example and docs/DEPLOYMENT.md §3)
```

## Why this address, specifically

This is the deployment that includes the numeric-consensus-binding fix (`docs/CANONICAL_DEPLOYMENT.md` companion: see Issue 1 in the final audit remediation) and the open-location-registration change, and it is the one currently configured in `frontend/.env.local` and verified live end-to-end: a real Lagos rainfall observation resolved from 3 independent retrievals (event `3d603813dbd7ae98`, `RESOLVED`, 12.30mm) and a real policy (`cover-1`) evaluated to `TRIGGERED` with a 1000-unit simulated payout credited.

## Superseded addresses

These addresses appear in this repository's history (git log, prior docs, and `docs/AUDIT.md`'s findings) as earlier disposable verification deployments. They are **not** canonical and should not be used for new work:

| Address | Context it was used for |
|---|---|
| `0x0908545f451521D3760183976c7e6848Fc7Ac701` | Stage 7 WeatherCover lifecycle verification (original TRIGGERED/NOT_TRIGGERED/UNRESOLVED demo) |
| `0x92A1DbA2D2F0E5707ee90f7EF4BB5aC704C171A0` | First manual owner-performed deployment; post-deployment payout audit (`docs/AUDIT.md`) |

Historical documents (`docs/AUDIT.md`, parts of `docs/DEMO_SCRIPT.md`) retain their original transaction hashes and addresses as an accurate record of what was actually tested at the time -- those specific tx hashes only exist on those specific contracts and were not fabricated against the canonical address. Where those documents describe the *current* live state of the product, they have been updated to point at the canonical address above; where they describe a specific historical verification run, they say so explicitly instead of being silently rewritten.

## If this contract is redeployed again

1. Update the table above with the new address, commit SHA, and deploy tx hash.
2. Update `frontend/lib/genlayer/config.ts`'s fallback constant and `frontend/.env.example`'s default.
3. Update `frontend/.env.local` (not committed) and redeploy the frontend.
4. Update `frontend/lib/demo/knownData.ts` if the new contract doesn't have equivalent demo event/policy IDs already set up (see `docs/MANUAL_DEPLOYMENT.md` §6).
5. Move the old address into the "Superseded addresses" table above, noting what it was used for.
