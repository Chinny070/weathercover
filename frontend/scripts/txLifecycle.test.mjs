import test from "node:test";
import assert from "node:assert/strict";
import { isActuallyFinalized, phaseForTransaction, shouldRunSuccessfulSettlement } from "../lib/genlayer/txLifecycle.ts";

test("PENDING then ACCEPTED remains accepted, never finalized", () => {
  assert.equal(phaseForTransaction("PENDING"), "pending");
  assert.equal(phaseForTransaction("ACCEPTED"), "accepted");
  assert.equal(isActuallyFinalized("ACCEPTED"), false);
});

test("only FINALIZED is actually final, then final state maps to finalized", () => {
  assert.equal(isActuallyFinalized("ACCEPTED"), false);
  assert.equal(isActuallyFinalized("FINALIZED"), true);
  assert.equal(phaseForTransaction("FINALIZED", "FINISHED_WITH_RETURN"), "finalized");
});

test("successful settlement refresh is forbidden for ACCEPTED and allowed only on successful FINALIZED", () => {
  assert.equal(shouldRunSuccessfulSettlement("ACCEPTED", "FINISHED_WITH_RETURN"), false);
  assert.equal(shouldRunSuccessfulSettlement("FINALIZED", "FINISHED_WITH_RETURN"), true);
  assert.equal(shouldRunSuccessfulSettlement("FINALIZED", "FINISHED_WITH_ERROR"), false);
});

test("a finalized transaction execution error is failed, not successful", () => {
  assert.equal(phaseForTransaction("FINALIZED", "FINISHED_WITH_ERROR"), "failed");
});

test("terminal GenLayer rejection and timeout states are failed", () => {
  for (const status of ["CANCELED", "UNDETERMINED", "LEADER_TIMEOUT", "VALIDATORS_TIMEOUT"]) {
    assert.equal(phaseForTransaction(status), "failed", status);
  }
});

test("an unresolved wait stays pending instead of being promoted to final", () => {
  assert.equal(phaseForTransaction("COMMITTING"), "pending");
  assert.equal(isActuallyFinalized("COMMITTING"), false);
});
