import type { SourceEvidence } from "@/lib/genlayer/types";
import { mm100ToDisplay } from "@/lib/genlayer/types";
import { FetchModeBadge, RetrievalStatusBadge } from "./StatusBadge";

/**
 * One row of the Evidence Explorer's source table: Source / Retrieval
 * method / Status / Normalized value, exactly as specified in the brief's
 * example ("Open-Meteo Archive · FETCH · AVAILABLE · 12.30mm").
 */
export function EvidenceRow({
  evidence,
  revealDelayMs = 0,
}: {
  evidence: SourceEvidence;
  /** Staggers this row's reveal so the evidence table reads as being
   * checked one source at a time, reinforcing that each was independently
   * retrieved -- not a single bulk API response. */
  revealDelayMs?: number;
}) {
  const isAvailable = evidence.retrieval_status === "AVAILABLE";
  return (
    <div
      className="wc-fade-up border-b px-4 py-3 last:border-b-0"
      style={{ borderColor: "var(--wc-rule-gray)", animationDelay: `${revealDelayMs}ms` }}
    >
      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 w-full sm:w-auto sm:flex-1">
          <p className="break-words text-sm font-medium" style={{ color: "var(--wc-ink)" }}>
            {evidence.source_id}
          </p>
          <p className="wc-mono truncate text-xs" style={{ color: "var(--wc-steel)" }}>
            {evidence.url}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <FetchModeBadge mode={evidence.fetch_mode} />
          <RetrievalStatusBadge status={evidence.retrieval_status} />
          <span
            className="wc-mono min-w-[5.5ch] text-right text-sm"
            style={{ color: isAvailable ? "var(--wc-ink)" : "var(--wc-steel)" }}
          >
            {isAvailable ? `${mm100ToDisplay(evidence.normalized_value_mm100)}mm` : "—"}
          </span>
        </div>
      </div>
      {evidence.location_match ? (
        <p className="mt-1 text-xs" style={{ color: "var(--wc-network-green)" }}>
          ✓ {evidence.location_detail}
        </p>
      ) : evidence.location_detail ? (
        <p className="mt-1 text-xs" style={{ color: "var(--wc-plum-ledger)" }}>
          {evidence.location_detail}
        </p>
      ) : null}
    </div>
  );
}
