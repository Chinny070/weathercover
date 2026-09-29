import Link from "next/link";
import type { CoverPolicy } from "@/lib/genlayer/types";
import { mm100ToDisplay } from "@/lib/genlayer/types";
import { CoverStatusBadge } from "./StatusBadge";

/**
 * Matches the brief's exact example card:
 *   Lagos Rain Protection / Location: LAGOS_NG / Condition: RAIN_24H BELOW
 *   10mm / Observation: 12.30mm / Status: NOT_TRIGGERED
 * The observation value is passed in separately (from the linked
 * Observation, fetched via cover_get_policy_detail) since CoverPolicy
 * alone does not carry the resolved value.
 */
export function PolicyCard({
  policy,
  observedValueMm100,
  revealDelayMs = 0,
}: {
  policy: CoverPolicy;
  observedValueMm100: number | null;
  revealDelayMs?: number;
}) {
  return (
    <Link
      href={`/policies/${policy.policy_id}`}
      className="wc-card wc-fade-up block transition-colors hover:border-[var(--wc-network-green)]"
      style={{ animationDelay: `${revealDelayMs}ms` }}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="wc-display text-lg">
            {policy.location_id.replace("_", " ")} {policy.metric.replace("_", " ")} Protection
          </p>
          <p className="wc-mono mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
            {policy.policy_id}
          </p>
        </div>
        <CoverStatusBadge status={policy.status} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt style={{ color: "var(--wc-steel)" }}>Location</dt>
          <dd className="wc-mono">{policy.location_id}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--wc-steel)" }}>Condition</dt>
          <dd className="wc-mono">
            {policy.metric} {policy.operator} {mm100ToDisplay(policy.threshold_mm100)}mm
          </dd>
        </div>
        <div>
          <dt style={{ color: "var(--wc-steel)" }}>Observation date</dt>
          <dd className="wc-mono">{policy.observation_date}</dd>
        </div>
        <div>
          <dt style={{ color: "var(--wc-steel)" }}>Observed value</dt>
          <dd className="wc-mono">
            {observedValueMm100 === null ? "not yet resolved" : `${mm100ToDisplay(observedValueMm100)}mm`}
          </dd>
        </div>
      </dl>

      {policy.status === "TRIGGERED" ? (
        <p className="mt-4 text-sm" style={{ color: "var(--wc-network-green)" }}>
          Payout credited: {policy.credited_amount} simulated units
        </p>
      ) : null}
    </Link>
  );
}
