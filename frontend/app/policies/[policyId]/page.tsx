"use client";

import { use } from "react";
import Link from "next/link";
import { useContractRead } from "@/hooks/useContractRead";
import { useTxAction } from "@/hooks/useTxAction";
import { useWallet } from "@/lib/wallet/WalletProvider";
import { getCoverPolicyDetail, evaluateCoverPolicy } from "@/lib/genlayer/contract";
import { mm100ToDisplay } from "@/lib/genlayer/types";
import { FlowDiagram, type FlowStep } from "@/components/FlowDiagram";
import { CoverStatusBadge } from "@/components/StatusBadge";
import { TxStatusLine } from "@/components/TxStatusLine";

const RESULT_COPY: Record<string, { headline: string; color: string; body: string }> = {
  TRIGGERED: {
    headline: "TRIGGERED",
    color: "var(--wc-network-green)",
    body: "The observed value met the policy condition. The simulated payout has been credited.",
  },
  NOT_TRIGGERED: {
    headline: "NOT TRIGGERED",
    color: "var(--wc-ink)",
    body: "The observation resolved successfully, but the condition was not met. This is an ordinary, unremarkable outcome — not a failure.",
  },
  UNRESOLVED: {
    headline: "UNRESOLVED",
    color: "var(--wc-plum-ledger)",
    body: "The underlying observation has not resolved yet, or resolved UNRESOLVED. No payout is credited or denied — this policy can be evaluated again once the observation resolves.",
  },
  PENDING: {
    headline: "AWAITING EVALUATION",
    color: "var(--wc-steel)",
    body: "This policy has not been evaluated yet.",
  },
};

export default function PolicyResultPage({ params }: { params: Promise<{ policyId: string }> }) {
  const { policyId } = use(params);
  const { client } = useWallet();

  const detailState = useContractRead(() => getCoverPolicyDetail(policyId), [policyId]);

  // useContractRead re-fetches on dependency change; bumping a local key
  // forces that without needing a second piece of state machinery.
  function refetch() {
    window.location.reload();
  }

  const { snapshot, run } = useTxAction(() => detailState.status === "ready" && refetch());

  if (detailState.status === "loading") {
    return <p style={{ color: "var(--wc-steel)" }}>Loading policy…</p>;
  }
  if (detailState.status === "error") {
    return (
      <div className="wc-card">
        <p style={{ color: "var(--wc-plum-ledger)" }}>Could not find this policy: {detailState.error}</p>
      </div>
    );
  }

  const policy = detailState.data;
  const observation = policy.linked_observation;
  const result = RESULT_COPY[policy.status];

  const steps: FlowStep[] = [
    { label: "Policy Created", state: "done", detail: policy.created_at.slice(0, 19) },
    {
      label: "Weather Observation Requested",
      state: observation ? "done" : "current",
      detail: `${policy.location_id} · ${policy.observation_date}`,
    },
    {
      label: "Evidence Retrieved",
      state: observation ? "done" : "pending",
      detail: observation ? `${observation.evidence.length} sources checked` : undefined,
    },
    {
      label: "Observation Resolved",
      state: observation ? "done" : "pending",
      detail: observation ? observation.status : undefined,
    },
    {
      label: "Condition Checked",
      state: policy.evaluated_at ? "done" : "pending",
      detail: policy.evaluated_at ? `${policy.operator} ${mm100ToDisplay(policy.threshold_mm100)}mm` : undefined,
    },
    {
      label: "Final Result",
      state: policy.evaluated_at ? "done" : "pending",
      detail: policy.evaluated_at ? policy.status : undefined,
    },
  ];

  return (
    <div className="flex flex-col gap-10">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="wc-mono text-xs" style={{ color: "var(--wc-steel)" }}>
            {policy.policy_id}
          </p>
          <h1 className="wc-display text-xl sm:text-2xl">
            {policy.location_id.replace("_", " ")} {policy.metric.replace("_", " ")} Protection
          </h1>
        </div>
        <CoverStatusBadge status={policy.status} />
      </div>

      <div className="text-center">
        <FlowDiagram steps={steps} />
      </div>

      <div className="wc-card wc-fade-up text-center" style={{ borderColor: result.color }}>
        <p className="wc-display text-4xl" style={{ color: result.color }}>
          {result.headline}
        </p>
        <p className="mx-auto mt-3 max-w-md text-sm" style={{ color: "var(--wc-graphite)" }}>
          {result.body}
        </p>
        {policy.status === "TRIGGERED" ? (
          <p className="wc-mono mt-3 text-lg" style={{ color: result.color }}>
            +{policy.credited_amount} simulated units
          </p>
        ) : null}

        {policy.status === "PENDING" || policy.status === "UNRESOLVED" ? (
          <div className="mt-4">
            <button
              className="wc-btn-primary flex items-center justify-center gap-2"
              onClick={() => run((c) => evaluateCoverPolicy(c, policyId), client)}
              disabled={snapshot.phase === "submitted" || snapshot.phase === "pending"}
            >
              {snapshot.phase === "submitted" || snapshot.phase === "pending" ? (
                <span className="wc-dot wc-pulse" style={{ background: "var(--wc-paper)", margin: 0 }} />
              ) : null}
              Evaluate Policy
            </button>
            <TxStatusLine snapshot={snapshot} />
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="wc-card">
          <p className="text-sm font-medium">Policy terms</p>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
            <dt style={{ color: "var(--wc-steel)" }}>Condition</dt>
            <dd className="wc-mono">
              {policy.metric} {policy.operator} {mm100ToDisplay(policy.threshold_mm100)}mm
            </dd>
            <dt style={{ color: "var(--wc-steel)" }}>Observation date</dt>
            <dd className="wc-mono">{policy.observation_date}</dd>
            <dt style={{ color: "var(--wc-steel)" }}>Simulated payout</dt>
            <dd className="wc-mono">{policy.simulated_payout} units</dd>
            <dt style={{ color: "var(--wc-steel)" }}>Owner</dt>
            <dd className="wc-mono truncate">{policy.owner}</dd>
          </dl>
        </div>
        <div className="wc-card">
          <p className="text-sm font-medium">Linked observation</p>
          {observation ? (
            <>
              <p className="mt-2 text-sm" style={{ color: "var(--wc-graphite)" }}>
                {observation.status === "RESOLVED"
                  ? `Resolved to ${mm100ToDisplay(observation.value_mm100)}mm from ${observation.source_count} independently retrieved sources.`
                  : `Unresolved: ${observation.resolution_reason.replace(/_/g, " ")}.`}
              </p>
              <Link href={`/observations/${policy.weather_event_id}`} className="wc-btn-secondary mt-3 inline-block text-sm">
                Open Evidence Explorer
              </Link>
            </>
          ) : (
            <p className="mt-2 text-sm" style={{ color: "var(--wc-steel)" }}>
              No observation has been resolved for this event yet.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
