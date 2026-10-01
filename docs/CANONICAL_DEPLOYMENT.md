# Canonical Deployment

This is the **single source of truth** for which contract address this project currently points at. Earlier working sessions deployed multiple disposable verification contracts while the product was being built and audited (documented in `docs/DEPLOYMENT.md`'s history and `docs/AUDIT.md`); this document exists so there is exactly one address to treat as authoritative going forward, instead of three.

---

```
Contract name:       WeatherResolveCover
Network:             GenLayer StudioNet
Chain ID:            61999
RPC:                 https://studio.genlayer.com/api
Contract address:    0xFd7160411e5812bD873089368b1BF687e644a959
Deployment commit:   9ed54f78382a5e6e5db6e144d4b5b02199b661e0
                      ("Final audit remediation: numeric consensus
                      binding, canonical deployment, source-independence
                      wording")
Deployment tx hash:  0xf60ad5c926a43748e8e9b564f8d5f4aafd2865d15ce97790156157572c2b1cb0
Deployed:            2026-10-01, manually by the project owner through
                      the GenLayer Studio web IDE. Confirmed ACCEPTED /
                      SUCCESS on the StudioNet explorer.
Frontend env var:    NEXT_PUBLIC_CONTRACT_ADDRESS (see
                      frontend/.env.example and docs/DEPLOYMENT.md §3)
```

## Why this address, specifically

This is the deployment of the contract code that fixes the numeric-consensus-binding gap (Issue 1 of the final audit remediation pass — the validator now independently recomputes and compares `raw_value`/normalized value, not just text fidelity, before approving consensus). It supersedes `0x8a07659C329e1e1d865667A23745d472a696b073`, which was still running the pre-fix code. It is the one currently configured in `frontend/.env.local` and verified live end-to-end after redeployment: a real Lagos rainfall observation resolved from 3 independently retrieved sources (event `3d603813dbd7ae98`, `RESOLVED`, 12.30mm), a real policy (`cover-1`) evaluated to `TRIGGERED` with a 1000-unit simulated payout credited, `cover-2` to `NOT_TRIGGERED`, and `cover-3` (linked to a deliberately-misconfigured source) to `UNRESOLVED` — all independently re-verified on this address, not copied forward from the superseded deployment.

**Release-candidate note (2026-10-01):** the source tree now adds validator binding for the persisted Evidence Package fields `location_match` and `location_detail` (SHA-256 `d1f8a35a7ed7599bbe0192a1aecdde2d1a413dc8d3c398fa3c0378ee25642d21`). That change has passed all local tests but is not in this already-manually-deployed contract. The address above remains the one active frontend target; manually redeploy the frozen release in `docs/RELEASE_FREEZE.md` before presenting the location-evidence binding as live.

## Superseded addresses

These addresses appear in this repository's history (git log, prior docs, and `docs/AUDIT.md`'s findings) as earlier deployments. They are **not** canonical and should not be used for new work:

| Address | Context it was used for |
|---|---|
| `0x8a07659C329e1e1d865667A23745d472a696b073` | Canonical deployment used throughout the final audit remediation pass up to and including Issues 1-6, **before** the numeric-consensus-binding fix was deployed; still running pre-fix contract code |
| `0x0908545f451521D3760183976c7e6848Fc7Ac701` | Stage 7 WeatherCover lifecycle verification (original TRIGGERED/NOT_TRIGGERED/UNRESOLVED demo) |
| `0x92A1DbA2D2F0E5707ee90f7EF4BB5aC704C171A0` | First manual owner-performed deployment; post-deployment payout audit (`docs/AUDIT.md`) |

Historical documents (`docs/AUDIT.md`, parts of `docs/DEMO_SCRIPT.md`) retain their original transaction hashes and addresses as an accurate record of what was actually tested at the time -- those specific tx hashes only exist on those specific contracts and were not fabricated against the canonical address. Where those documents describe the *current* live state of the product, they have been updated to point at the canonical address above; where they describe a specific historical verification run, they say so explicitly instead of being silently rewritten.

## If this contract is redeployed again

1. Update the table above with the new address, commit SHA, and deploy tx hash.
2. Update `frontend/lib/genlayer/config.ts`'s fallback constant and `frontend/.env.example`'s default.
3. Update `frontend/.env.local` (not committed) and redeploy the frontend.
4. Update `frontend/lib/demo/knownData.ts` if the new contract doesn't have equivalent demo event/policy IDs already set up (see `docs/MANUAL_DEPLOYMENT.md` §6).
5. Move the old address into the "Superseded addresses" table above, noting what it was used for.
