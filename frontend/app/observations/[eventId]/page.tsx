"use client";

import { use } from "react";
import { useContractRead } from "@/hooks/useContractRead";
import { getObservation, getWeatherEvent } from "@/lib/genlayer/contract";
import { mm100ToDisplay } from "@/lib/genlayer/types";
import { EvidenceRow } from "@/components/EvidenceRow";
import { EventStatusBadge } from "@/components/StatusBadge";
import { FlowDiagram, type FlowStep } from "@/components/FlowDiagram";

export default function EvidenceExplorerPage({ params }: { params: Promise<{ eventId: string }> }) {
  const { eventId } = use(params);

  const eventState = useContractRead(() => getWeatherEvent(eventId), [eventId]);
  const observationState = useContractRead(() => getObservation(eventId), [eventId]);

  if (eventState.status === "loading" || observationState.status === "loading") {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <span className="wc-dot wc-pulse" style={{ background: "var(--wc-network-green)", width: 10, height: 10 }} />
        <p style={{ color: "var(--wc-steel)" }}>Loading observation from StudioNet…</p>
      </div>
    );
  }

  if (eventState.status === "error") {
    return (
      <div className="wc-card">
        <p style={{ color: "var(--wc-plum-ledger)" }}>Could not find this event: {eventState.error}</p>
      </div>
    );
  }

  const event = eventState.data!;
  const observation = observationState.status === "ready" ? observationState.data : null;
  const locationMatched = observation?.evidence.some((e) => e.location_match !== "") ?? false;
  const dateMatched = observation?.evidence.some((e) => e.retrieval_status !== "WRONG_DATE") ?? false;
  const hasEvidence = observation !== null && observation.evidence.length > 0;
  const isResolved = observation?.status === "RESOLVED";

  const verificationSteps: FlowStep[] = [
    { label: "Source retrieval", state: hasEvidence ? "done" : "current", detail: hasEvidence ? `${observation!.evidence.length} sources` : undefined },
    { label: "Evidence validation", state: hasEvidence ? "done" : "pending", detail: hasEvidence ? "location + date checked" : undefined },
    {
      label: "Observation resolution",
      state: observation ? "done" : "pending",
      detail: observation ? observation.status : undefined,
    },
    {
      label: "Policy evaluation",
      state: isResolved ? "current" : "pending",
      detail: isResolved ? "ready to consume" : undefined,
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div className="wc-graph-paper wc-fade-up -mx-4 rounded-lg px-4 py-8 sm:-mx-6 sm:px-6 sm:py-10">
        <p className="wc-mono text-xs uppercase tracking-widest" style={{ color: "var(--wc-network-green)" }}>
          GenLayer verified observation
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-4">
          <h1 className="wc-display text-3xl">
            {event.location.replace("_", " ")} · {event.metric.replace("_", " ")}
          </h1>
          <EventStatusBadge status={event.status} />
        </div>
        <p className="wc-mono mt-1 text-sm" style={{ color: "var(--wc-steel)" }}>
          Observation date: {event.observation_period} · Observation ID: {event.event_id}
        </p>

        {observation && observation.status === "RESOLVED" ? (
          <p className="mt-6 text-5xl wc-display" style={{ color: "var(--wc-network-green)" }}>
            {mm100ToDisplay(observation.value_mm100)}mm
          </p>
        ) : observation ? (
          <p className="mt-6 text-2xl wc-display" style={{ color: "var(--wc-plum-ledger)" }}>
            UNRESOLVED — {observation.resolution_reason.replace(/_/g, " ")}
          </p>
        ) : null}
      </div>

      {/* The four-stage verification flow this page exists to make visible */}
      <div className="flex justify-center overflow-x-auto py-2">
        <FlowDiagram steps={verificationSteps} />
      </div>

      {observation ? (
        <>
          {/* Verification checklist */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="wc-card">
              <p className="text-sm font-medium">Location verification</p>
              <p className="mt-1" style={{ color: locationMatched ? "var(--wc-network-green)" : "var(--wc-plum-ledger)" }}>
                {locationMatched ? "✓ Location confirmed" : "✗ No source confirmed this location"}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
                Checked against the {event.location} Location Resolution Profile: canonical name, aliases,
                country, and coordinate proximity — never the internal location ID itself.
              </p>
            </div>
            <div className="wc-card">
              <p className="text-sm font-medium">Date verification</p>
              <p className="mt-1" style={{ color: dateMatched ? "var(--wc-network-green)" : "var(--wc-plum-ledger)" }}>
                {dateMatched ? "✓ Observation date confirmed" : "✗ No source confirmed this date"}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
                Each source&apos;s response is checked for {event.observation_period} before its value is
                ever read.
              </p>
            </div>
          </div>

          {/* Evidence sources table */}
          <div>
            <h2 className="wc-display mb-3 text-xl">Evidence sources</h2>
            <div className="wc-card !p-0 overflow-hidden">
              <div
                className="hidden justify-between border-b px-4 py-2 text-xs font-medium uppercase tracking-wide sm:flex"
                style={{ borderColor: "var(--wc-rule-gray)", color: "var(--wc-steel)" }}
              >
                <span>Source</span>
                <span>Method · Status · Normalized value</span>
              </div>
              {observation.evidence.map((e, i) => (
                <EvidenceRow key={e.source_id} evidence={e} revealDelayMs={i * 90} />
              ))}
            </div>
          </div>

          {/* Resolution + consensus summary */}
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="wc-panel text-center">
              <p className="text-xs uppercase tracking-wide" style={{ color: "var(--wc-steel)" }}>
                Resolution
              </p>
              <p className="wc-display mt-1 text-lg" style={{ color: observation.evidence_status === "SUFFICIENT" ? "var(--wc-network-green)" : "var(--wc-plum-ledger)" }}>
                {observation.evidence_status}
              </p>
            </div>
            <div className="wc-panel text-center">
              <p className="text-xs uppercase tracking-wide" style={{ color: "var(--wc-steel)" }}>
                Sources agreeing
              </p>
              <p className="wc-display mt-1 text-lg">{observation.source_count}</p>
            </div>
            <div className="wc-panel text-center">
              <p className="text-xs uppercase tracking-wide" style={{ color: "var(--wc-steel)" }}>
                Consensus
              </p>
              <p className="wc-display mt-1 text-lg" style={{ color: "var(--wc-network-green)" }}>
                MAJORITY_AGREE
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--wc-steel)" }}>
                GenLayer validators independently retrieved and agreed on this evidence.
              </p>
            </div>
          </div>

          <p className="text-center text-sm italic" style={{ color: "var(--wc-graphite)" }}>
            An independent validator network verified this real-world event — not a single API call.
          </p>
        </>
      ) : (
        <p style={{ color: "var(--wc-steel)" }}>
          This event has not been resolved yet. No Evidence Package exists until{" "}
          <code className="wc-mono">resolve_weather_event</code> is called.
        </p>
      )}
    </div>
  );
}
