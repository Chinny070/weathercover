"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useWallet } from "@/lib/wallet/WalletProvider";
import {
  computeEventId,
  eventExists,
  createWeatherEvent,
  resolveWeatherEvent,
  createCoverPolicy,
  listPolicyIdsByOwner,
  waitForStatus,
  getTransaction,
} from "@/lib/genlayer/contract";
import { TransactionStatus } from "genlayer-js/types";
import {
  AVAILABLE_SOURCE_POLICIES,
  KNOWN_LOCATION_ID,
  KNOWN_METRIC,
  RESOLVED_DEMO_OBSERVATION_DATE,
} from "@/lib/demo/knownData";

type Step = "idle" | "checking-event" | "creating-event" | "resolving-event" | "creating-policy" | "done" | "error";

const STEP_LABEL: Record<Step, string> = {
  idle: "",
  "checking-event": "Checking whether this observation has been requested before…",
  "creating-event": "Requesting the weather event on WeatherResolve (signature required)…",
  "resolving-event": "Resolving real-world evidence for this event (signature required)…",
  "creating-policy": "Creating your WeatherCover policy (signature required)…",
  done: "Policy created.",
  error: "Something went wrong.",
};

export default function CreatePolicyPage() {
  const { address, client, connect, hasProvider } = useWallet();
  const router = useRouter();

  const [sourcePolicyId, setSourcePolicyId] = useState<string>(AVAILABLE_SOURCE_POLICIES[0].id);
  const [observationDate, setObservationDate] = useState(RESOLVED_DEMO_OBSERVATION_DATE);
  const [operator, setOperator] = useState<"BELOW" | "ABOVE">("BELOW");
  const [thresholdMm, setThresholdMm] = useState("15.00");
  const [payout, setPayout] = useState("1000");
  const [alsoResolve, setAlsoResolve] = useState(true);

  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<string | null>(null);

  const busy = step !== "idle" && step !== "done" && step !== "error";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!client || !address) return;
    setError(null);

    const thresholdMm100 = Math.round(parseFloat(thresholdMm) * 100);
    const payoutUnits = Math.round(parseFloat(payout));
    if (!Number.isFinite(thresholdMm100) || thresholdMm100 <= 0) {
      setError("Enter a valid, positive threshold.");
      return;
    }
    if (!Number.isFinite(payoutUnits) || payoutUnits <= 0) {
      setError("Enter a valid, positive simulated payout.");
      return;
    }

    try {
      setStep("checking-event");
      const eventId = await computeEventId(KNOWN_LOCATION_ID, KNOWN_METRIC, observationDate, sourcePolicyId);
      const exists = await eventExists(eventId);

      if (!exists) {
        setStep("creating-event");
        const createHash = await createWeatherEvent(client, KNOWN_LOCATION_ID, KNOWN_METRIC, observationDate, sourcePolicyId);
        await waitForStatus(client, createHash, TransactionStatus.ACCEPTED, { retries: 120, interval: 2000 }).catch(() => {});
      }

      if (alsoResolve) {
        setStep("resolving-event");
        const resolveHash = await resolveWeatherEvent(client, eventId);
        await waitForStatus(client, resolveHash, TransactionStatus.ACCEPTED, { retries: 150, interval: 2000 }).catch(() => {});
        // Resolution can legitimately settle UNRESOLVED (e.g. a date the
        // configured sources don't cover) -- that is not an error, the
        // policy below will simply read UNRESOLVED until it resolves.
      }

      setStep("creating-policy");
      const policyHash = await createCoverPolicy(client, eventId, operator, thresholdMm100, payoutUnits);
      await waitForStatus(client, policyHash, TransactionStatus.ACCEPTED, { retries: 120, interval: 2000 }).catch(() => {});
      const tx = await getTransaction(policyHash);
      if (tx.statusName && tx.statusName !== "ACCEPTED" && tx.statusName !== "FINALIZED") {
        throw new Error(`Policy creation did not settle as accepted (${tx.statusName}). It may have reverted -- check the dedupe/threshold rules.`);
      }

      const ids = await listPolicyIdsByOwner(address);
      const newestPolicyId = ids[ids.length - 1];
      setStep("done");
      router.push(`/policies/${newestPolicyId}`);
    } catch (err) {
      setStep("error");
      setError(err instanceof Error ? err.message : "Failed to create the policy.");
    }
  }

  if (!address) {
    return (
      <div className="wc-card mx-auto max-w-md text-center">
        <p className="wc-display text-lg">Connect your wallet to create a policy</p>
        <button className="wc-btn-primary mt-4" onClick={connect} disabled={!hasProvider}>
          {hasProvider ? "Connect Wallet" : "No wallet found"}
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="wc-display text-2xl">Create a Policy</h1>
      <p className="mt-2 text-sm" style={{ color: "var(--wc-graphite)" }}>
        Choose a condition. WeatherResolve will independently verify the real-world observation before
        your policy can ever be evaluated.
      </p>

      <form onSubmit={handleSubmit} className="wc-card mt-6 flex flex-col gap-5">
        <div>
          <label className="text-sm font-medium">Location</label>
          <input className="wc-input wc-mono mt-1" value={KNOWN_LOCATION_ID} disabled />
          <p className="mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
            Only locations with a registered Location Resolution Profile are available. Adding a new
            location is an infrastructure-operator action, not an end-user one.
          </p>
        </div>

        <div>
          <label className="text-sm font-medium">Weather metric</label>
          <input className="wc-input wc-mono mt-1" value={KNOWN_METRIC} disabled />
        </div>

        <div>
          <label className="text-sm font-medium">Evidence source policy</label>
          <select className="wc-input mt-1" value={sourcePolicyId} onChange={(e) => setSourcePolicyId(e.target.value)}>
            {AVAILABLE_SOURCE_POLICIES.map((sp) => (
              <option key={sp.id} value={sp.id}>
                {sp.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-sm font-medium">Observation date</label>
          <input
            className="wc-input wc-mono mt-1"
            value={observationDate}
            onChange={(e) => setObservationDate(e.target.value)}
            placeholder="YYYY-MM-DD"
          />
          <p className="mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
            The configured evidence sources for this policy are pinned to {RESOLVED_DEMO_OBSERVATION_DATE}.
            Other dates will still be requested honestly, but real sources may return an UNRESOLVED
            observation if they don&apos;t cover that date.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium">Operator</label>
            <select className="wc-input mt-1" value={operator} onChange={(e) => setOperator(e.target.value as "BELOW" | "ABOVE")}>
              <option value="BELOW">BELOW</option>
              <option value="ABOVE">ABOVE</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Threshold (mm)</label>
            <input className="wc-input wc-mono mt-1" value={thresholdMm} onChange={(e) => setThresholdMm(e.target.value)} inputMode="decimal" />
          </div>
        </div>

        <div>
          <label className="text-sm font-medium">Simulated payout (units)</label>
          <input className="wc-input wc-mono mt-1" value={payout} onChange={(e) => setPayout(e.target.value)} inputMode="numeric" />
          <p className="mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
            Simulated only — no real funds, escrow, or tokens exist in this product.
          </p>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={alsoResolve} onChange={(e) => setAlsoResolve(e.target.checked)} />
          Request resolution immediately after creating the event (recommended for this demo)
        </label>

        <button type="submit" className="wc-btn-primary flex items-center justify-center gap-2" disabled={busy}>
          {busy ? (
            <>
              <span className="wc-dot wc-pulse" style={{ background: "var(--wc-paper)", margin: 0 }} />
              {STEP_LABEL[step]}
            </>
          ) : (
            "Create Policy"
          )}
        </button>

        {error ? (
          <p className="wc-fade-up wc-mono text-xs" style={{ color: "var(--wc-plum-ledger)" }}>
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}
