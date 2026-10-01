export type TxPhase = "idle" | "submitted" | "pending" | "accepted" | "finalized" | "failed";

const TERMINAL_FAILURES = new Set(["UNDETERMINED", "CANCELED", "VALIDATORS_TIMEOUT", "LEADER_TIMEOUT"]);

export function phaseForTransaction(statusName: string | null, executionResultName?: string | null): TxPhase {
  if (statusName === "FINALIZED") return executionResultName === "FINISHED_WITH_ERROR" ? "failed" : "finalized";
  if (statusName === "ACCEPTED") return "accepted";
  if (statusName && TERMINAL_FAILURES.has(statusName)) return "failed";
  return "pending";
}

export function isActuallyFinalized(statusName: string | null): boolean {
  return statusName === "FINALIZED";
}

export function shouldRunSuccessfulSettlement(statusName: string | null, executionResultName?: string | null): boolean {
  return isActuallyFinalized(statusName) && executionResultName !== "FINISHED_WITH_ERROR";
}
