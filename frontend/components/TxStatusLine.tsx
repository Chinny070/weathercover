import type { TxSnapshot } from "@/hooks/useTxAction";
import { isActuallyFinalized } from "@/lib/genlayer/txLifecycle";

const PHASE_COPY: Record<string, { label: string; color: string; pulse: boolean }> = {
  submitted: { label: "Submitted — waiting for wallet signature…", color: "var(--wc-steel)", pulse: true },
  pending: { label: "Pending — awaiting GenLayer consensus…", color: "var(--wc-graphite)", pulse: true },
  accepted: { label: "Accepted — waiting for GenLayer finality…", color: "var(--wc-graphite)", pulse: true },
  finalized: { label: "Finalized", color: "var(--wc-network-green)", pulse: false },
  failed: { label: "Failed", color: "var(--wc-plum-ledger)", pulse: false },
};

/**
 * The four transaction states the product brief requires to be visually
 * distinguishable: Submitted / Pending / Finalized / Failed. A pulsing dot
 * marks the two in-flight states so a visitor can tell "still working" from
 * "done" at a glance, without reading the text.
 */
export function TxStatusLine({ snapshot }: { snapshot: TxSnapshot }) {
  if (snapshot.phase === "idle") return null;

  const copy = PHASE_COPY[snapshot.phase];
  const isFinalized = snapshot.phase === "finalized" && isActuallyFinalized(snapshot.statusName);

  return (
    <div className="wc-fade-up mt-3 flex items-start gap-2">
      <span
        className={`wc-dot mt-1 shrink-0 ${copy.pulse ? "wc-pulse" : ""}`}
        style={{
          background: copy.color,
          margin: 0,
        }}
      />
      <div className="wc-mono text-xs">
        {snapshot.phase === "pending" || snapshot.phase === "accepted" ? (
          <>
            <p style={{ color: copy.color }}>
              {copy.label} ({snapshot.hash?.slice(0, 10)}…)
            </p>
            {snapshot.error ? <p className="mt-1" style={{ color: "var(--wc-steel)" }}>{snapshot.error}</p> : null}
          </>
        ) : snapshot.phase === "failed" ? (
          <p style={{ color: copy.color }}>{snapshot.error ?? "Unknown error."}</p>
        ) : snapshot.phase === "finalized" && isFinalized ? (
          <>
            <p style={{ color: "var(--wc-network-green)" }}>
              Finalized — {snapshot.statusName}
              {snapshot.resultName ? ` · ${snapshot.resultName}` : ""}
            </p>
            <p style={{ color: "var(--wc-steel)" }}>state re-read below reflects the real result.</p>
          </>
        ) : snapshot.phase === "finalized" ? (
          <p style={{ color: "var(--wc-plum-ledger)" }}>Finality was not confirmed; this transaction is not shown as successful.</p>
        ) : (
          <p style={{ color: copy.color }}>{copy.label}</p>
        )}
      </div>
    </div>
  );
}
