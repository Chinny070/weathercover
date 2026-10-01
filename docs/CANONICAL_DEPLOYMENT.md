# Canonical Deployment

This is the **single source of truth** for which contract address this project currently points at. Earlier working sessions deployed multiple disposable verification contracts while the product was being built and audited (documented in `docs/DEPLOYMENT.md`'s history and `docs/AUDIT.md`); this document exists so there is exactly one address to treat as authoritative going forward, instead of three.

---

```
Contract name:       WeatherResolveCover
Network:             GenLayer StudioNet
Chain ID:            61999
RPC:                 https://studio.genlayer.com/api
Contract address:    0x35f33d089500d5554c803A201a19aEa9eD073022
Deployment commit:   061e171e3de024dd705840f0cbbd695c70ac8a1a
                      ("Bind validator evidence fields and enable lint")
Contract source SHA: d1f8a35a7ed7599bbe0192a1aecdde2d1a413dc8d3c398fa3c0378ee25642d21
Deployment tx hash:  0xc22461a89601662618633ec12a7192f4f9e78bd73301d597732c5410dd8330b7
Deployed:            2026-10-01 14:01:47 Africa/Lagos, manually by the
                      project owner through the GenLayer Studio web IDE.
                      Confirmed ACCEPTED / SUCCESS on StudioNet Explorer.
Frontend env var:    NEXT_PUBLIC_CONTRACT_ADDRESS (see
                      frontend/.env.example and docs/DEPLOYMENT.md §3)
```

## Why this address, specifically

This is the deployment of the full audited contract source: validators independently bind the extracted numeric value, normalized value, and the persisted location-verification evidence fields before approving consensus. It supersedes the earlier StudioNet deployments listed below.

**Setup completed:** the Lagos profile and both source policies were registered, the resolved and unresolved observations were created, and the three policy outcomes were recreated and checked against this address. The local frontend and Vercel production environment point here. Vercel production deployment `dpl_JAEiaTKE8S3yhMNpeSdhSjknF5rj` is Ready at [frontend-chinny070s-projects.vercel.app](https://frontend-chinny070s-projects.vercel.app). Production `NEXT_PUBLIC_CONTRACT_ADDRESS` was updated before building and deploying.

### Live demo state

| Item | Verified state |
|---|---|
| Resolved event | `3d603813dbd7ae98` — `RESOLVED`, `RAIN_24H = 12.30 mm`, 3 available evidence rows, `SUFFICIENT`, reason `OK` |
| Evidence values | Open-Meteo archive model queries: `best_match` 12.30 mm, `era5` 10.40 mm, `ecmwf_ifs` 12.30 mm; median 12.30 mm |
| `cover-1` | `BELOW 15 mm` → `TRIGGERED`; 1,000 simulated units credited |
| `cover-2` | `BELOW 10 mm` → `NOT_TRIGGERED`; 0 credited |
| Unresolved event | `f96bbf7bf2a964ae` — source coordinates rejected as `WRONG_LOCATION`; event is `UNRESOLVED` for `INSUFFICIENT_SOURCES` |
| `cover-3` | Linked to the unresolved event → `UNRESOLVED`; 0 credited |
| Owner simulated balance | 1,000 units |

### Setup transaction evidence

| Action | StudioNet transaction |
|---|---|
| Contract deployment | `0xc22461a89601662618633ec12a7192f4f9e78bd73301d597732c5410dd8330b7` |
| Register Lagos profile | `0xc83054c5fd662fca45bbfbfafe4ab5b03a2acdb0c5a9544ecd60fa3dfb72952d` |
| Register `AUDIT_V1` | `0xc876f0e4f9479f8c6918dcc5b249242d4b4eeea6082df2c99e179e749ede0f0d` |
| Add best-match source | `0x1cdc00e266502d112adffb3c97b5ebd49905e3597bbb082786407c29992027bf` |
| Add ERA5 source | `0x48fbe5a56bdd4f1ff23db97b9f15e6643928427622d2807b1e17ec0db60fe36d` |
| Add ECMWF IFS source | `0x69433142ebb6a255cc05e7d56a7ff9459c2eb0c9d03e202195c1f21e72e85104` |
| Create resolved event | `0x345c428e7bd72cbed6d32ec0fbc69a10a96aa82a68ca5ba552536f36fc3f9922` |
| Resolve event | `0x51136c9965fc62319e25cc8099ebee26082bee4de5b43abb5a483245848b9913` |
| Evaluate `cover-1` | `0x8c79c8a1b2aafc14eebcc5bcb5f85f8ebd7f0194f899acb694f25481d97d1c67` |
| Create `cover-2` | `0x950750c924076d4ccf2cddd72ecb0eedfa4d8e61620fa5d10fc58945c6f3160f` |
| Evaluate `cover-2` | `0xcc1533a9799efc74a0d50e4a0e51af448ba5882c37ed8adbbf77b5b21d422c6a` |
| Register `AUDIT_UNRES_V1` | `0x790055879e2da2c7c8c2660d0821d2f0ff6d6edc95db32a3e0403788ed30f3f8` |
| Add wrong-location source | `0xc37bae994632bb0180bed3a6c16805291e99f8780987475cae5a01d35b7822e3` |
| Create unresolved event | `0x5ee5e00e4ebda253f115d0769e9d0bc43e35c5e2cf58ad0fa2f50016a0c35c3d` |
| Resolve unresolved event | `0x6fe34fa8844284dd6b167140cb5abc02c178ce32bb7eb387b07f685078162863` |
| Create `cover-3` | `0x9315d473bbf4dc6db4877aaa074c01d9b0f00839baffb08f6ed549e1e3820da6` |
| Evaluate `cover-3` | `0x0cfd16b22984722d78d4c7f627b79c264318cd40e397be3358d52aa08d88f2c6` |

The `cover-1` creation transaction was accepted and the policy is confirmed by a finalized read; its CLI transaction hash was not captured in the setup notes.

## Superseded addresses

These addresses appear in this repository's history (git log, prior docs, and `docs/AUDIT.md`'s findings) as earlier deployments. They are **not** canonical and should not be used for new work:

| Address | Context it was used for |
|---|---|
| `0xFd7160411e5812bD873089368b1BF687e644a959` | Previous numeric-binding deployment; its demo data remains valid historical evidence but it does not include the later persisted-location-evidence binding |
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
