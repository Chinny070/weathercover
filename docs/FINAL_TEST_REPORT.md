# Final Test Report

Produced as part of the final audit remediation pass. Every command below was actually run (not summarized from memory) on this exact codebase, after the numeric-consensus binding fix, the Evidence Package location-field binding follow-up, open location registration, canonical address cleanup, and wording fixes.

---

## Contract tests

**Command:**
```bash
python -m pytest tests/ -q
```

**Result:** `53 passed in 20.66s` — zero failures, zero skips. Pytest emitted one non-failing warning because the local `.pytest_cache` directory is not writable.

| File | Tests | New in this pass |
|---|---|---|
| `tests/direct/test_event_registry.py` | 17 | 2 (`test_any_caller_can_register_a_location`, `test_cannot_overwrite_an_existing_location`) |
| `tests/direct/test_resolution.py` | 25 | 4 (`test_malicious_leader_raw_value_rejected_by_validator`, `test_malicious_leader_location_evidence_rejected_by_validator`, `test_leader_and_validator_extract_different_values_rejected`, `test_matching_leader_and_validator_values_accepted`) |
| `tests/direct/test_weathercover.py` | 12 | 0 |
| **Total** | **53** (was 47 before this pass) | **6 new** |

### Adversarial consensus tests (Issue 1), individually

| Test | Scenario | Expected | Actual |
|---|---|---|---|
| `test_malicious_leader_raw_value_rejected_by_validator` | Leader returns genuine `raw_text` but a fabricated `raw_value` ("999") that doesn't match what that text actually extracts to | Consensus rejects (`validator_fn` → `False`) | ✅ `False` |
| `test_malicious_leader_location_evidence_rejected_by_validator` | Leader returns genuine text/value but fabricated `location_match` / `location_detail` Evidence Package fields | Consensus rejects; persisted location-verification evidence is validator-bound | ✅ `False` |
| `test_leader_and_validator_extract_different_values_rejected` | Leader and validator genuinely retrieve different values from the same source (simulating drift between fetches); LLM fidelity judgment mocked to approve the text itself | Consensus rejects even though text-fidelity alone would have approved | ✅ `False` |
| `test_matching_leader_and_validator_values_accepted` | Control case: leader's claimed result genuinely matches the validator's own independent recomputation | Consensus accepts; event resolves `RESOLVED` at the correct value | ✅ `True`, `RESOLVED`, `value_mm100: 860` |

### Contract syntax / lint

```bash
python -m py_compile contracts/weather_resolve_cover.py
```
→ `PASS`. (No `ruff`/`flake8` available in this environment — documented as a known tooling limitation in `docs/RELEASE_FREEZE.md`, not a skipped check.)

---

## Frontend build/typecheck/lint

**Commands:**
```bash
npm run typecheck
npm run lint
npm run build
```

**Results:**
```
npm run typecheck   → 0 errors
npm run lint        → 0 errors, 2 non-blocking `react-hooks/exhaustive-deps` warnings in `app/dashboard/page.tsx`
npm run build         → Compiled successfully; 5/5 routes generated
                         (/, /create-policy, /dashboard static;
                          /observations/[eventId], /policies/[policyId] dynamic)
                         0 errors
```

The lint command is now backed by the repository's ESLint 9 flat configuration (`frontend/eslint.config.mjs`). The final typecheck, lint, and build were run after the location-evidence binding follow-up; all commands exited successfully.

---

## Live StudioNet re-verification (not just unit tests)

Beyond the test suite, the active StudioNet contract (`0xFd7160411e5812bD873089368b1BF687e644a959`, see `docs/CANONICAL_DEPLOYMENT.md`) was directly re-queried to confirm every demo ID referenced in the frontend and docs actually exists and resolves as claimed. It was redeployed on 2026-10-01 to carry the numeric-consensus-binding fix. The newer location-evidence-field binding covered by this report is tested locally but requires a manual redeployment before it can be claimed as live.

| Check | Result |
|---|---|
| `location_exists("LAGOS_NG")` | `true` |
| `policy_exists("AUDIT_V1")` | `true` |
| `policy_exists("AUDIT_UNRES_V1")` | `true` |
| `event_exists` for the RESOLVED demo event (`3d603813dbd7ae98`) | `RESOLVED`, `value_mm100: 1230` |
| `event_exists` for the UNRESOLVED demo event (`f96bbf7bf2a964ae`) | `UNRESOLVED`, `resolution_reason: INSUFFICIENT_SOURCES` |
| `cover_get_policy("cover-1")` | `TRIGGERED`, `credited_amount: 1000` |
| `cover_get_policy("cover-2")` | `NOT_TRIGGERED`, `credited_amount: 0` |
| `cover_get_policy("cover-3")` | `UNRESOLVED`, `credited_amount: 0` |

(`cover-2` and `cover-3` did not exist on the canonical contract before this remediation pass — see Issue 2 in the final summary. They were created and evaluated live as part of fixing that gap, not fabricated.)

---

## Summary

- **53/53 contract tests pass**, including 6 new adversarial/regression tests added in this pass.
- **Frontend typecheck, lint, and build all exit successfully.** Lint reports two existing non-blocking dependency warnings.
- **Every demo ID referenced anywhere in the repo exists and resolves as described** on the active StudioNet deployment. The new location-evidence-field binding remains a locally verified release candidate until manual redeployment.
