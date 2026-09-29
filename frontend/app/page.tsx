import Link from "next/link";
import { FlowDiagram } from "@/components/FlowDiagram";
import {
  RESOLVED_DEMO_EVENT_ID,
  RESOLVED_DEMO_OBSERVATION_DATE,
  KNOWN_LOCATION_ID,
  KNOWN_METRIC,
} from "@/lib/demo/knownData";

const PROCESS_STEPS = [
  { label: "Policy Created", state: "done" as const },
  { label: "Weather Observed", state: "done" as const },
  { label: "Evidence Verified", state: "done" as const },
  { label: "Condition Evaluated", state: "done" as const },
  { label: "Coverage Decision", state: "done" as const },
];

export default function LandingPage() {
  return (
    <div className="flex flex-col gap-14 sm:gap-20">
      {/* Hero */}
      <section className="wc-graph-paper wc-fade-up -mx-4 rounded-lg px-4 py-12 text-center sm:-mx-6 sm:px-6 sm:py-16">
        <p className="wc-mono mb-4 text-xs uppercase tracking-widest" style={{ color: "var(--wc-network-green)" }}>
          Parametric weather coverage · powered by WeatherResolve
        </p>
        <h1 className="wc-display mx-auto max-w-3xl text-4xl leading-tight sm:text-5xl">
          Weather conditions verified. Coverage decisions automated.
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-base" style={{ color: "var(--wc-graphite)" }}>
          WeatherCover is not a weather app. It is a parametric insurance application built on
          WeatherResolve — a reusable infrastructure layer that retrieves real-world weather evidence,
          verifies it against independent sources, and reaches GenLayer validator consensus on what
          actually happened, before any coverage decision is made.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
          <Link href="/create-policy" className="wc-btn-primary w-full text-center sm:w-auto">
            Create a Policy
          </Link>
          <Link href={`/observations/${RESOLVED_DEMO_EVENT_ID}`} className="wc-btn-secondary w-full text-center sm:w-auto">
            See a Verified Observation
          </Link>
        </div>
      </section>

      {/* Concept explanation */}
      <section className="grid gap-8 sm:grid-cols-3">
        <div className="wc-card wc-fade-up">
          <p className="wc-display text-lg" style={{ color: "var(--wc-network-green)" }}>
            WeatherResolve
          </p>
          <p className="mt-2 text-sm" style={{ color: "var(--wc-graphite)" }}>
            Reusable infrastructure. Retrieves evidence from multiple independent real-world sources,
            verifies location and date, normalizes values, and resolves one canonical observation —
            reused by any number of applications, not just WeatherCover.
          </p>
        </div>
        <div className="wc-card wc-fade-up" style={{ animationDelay: "80ms" }}>
          <p className="wc-display text-lg">WeatherCover</p>
          <p className="mt-2 text-sm" style={{ color: "var(--wc-graphite)" }}>
            The first application built on that infrastructure. A policy reads one resolved
            observation and evaluates a simple, deterministic condition — nothing more.
          </p>
        </div>
        <div className="wc-card wc-fade-up" style={{ animationDelay: "160ms" }}>
          <p className="wc-display text-lg">Example policy</p>
          <p className="mt-2 wc-mono text-sm" style={{ color: "var(--wc-graphite)" }}>
            {KNOWN_LOCATION_ID} · {KNOWN_METRIC}
            <br />
            BELOW 15.00mm on {RESOLVED_DEMO_OBSERVATION_DATE}
            <br />
            → real observation: 12.30mm
            <br />→ <span style={{ color: "var(--wc-network-green)" }}>TRIGGERED</span>
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="text-center">
        <h2 className="wc-display text-2xl">How it works</h2>
        <p className="mx-auto mt-2 max-w-md text-sm" style={{ color: "var(--wc-steel)" }}>
          Every policy follows the same verifiable path — nothing is decided until the evidence has
          been retrieved and independently confirmed.
        </p>
        <div className="mt-10">
          <FlowDiagram steps={PROCESS_STEPS} />
        </div>
      </section>

      {/* Not a dashboard */}
      <section className="wc-panel text-center">
        <p className="wc-display text-xl">This is not a weather dashboard.</p>
        <p className="mx-auto mt-2 max-w-2xl text-sm" style={{ color: "var(--wc-graphite)" }}>
          A weather dashboard shows you one provider&apos;s number and asks you to trust it. WeatherCover
          never resolves a coverage decision from a single source: every observation behind a policy
          was independently retrieved from multiple real sources, checked against a Location Resolution
          Profile and the requested date, and only resolved once GenLayer validators reached consensus.
          Open the Evidence Explorer on any policy to see exactly what was checked.
        </p>
      </section>
    </div>
  );
}
