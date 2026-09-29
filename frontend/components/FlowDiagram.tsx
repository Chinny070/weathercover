export interface FlowStep {
  label: string;
  detail?: string;
  /** "done" = Network Green node (completed), "current" = ink node with a
   * ring (in progress / the step the viewer should focus on), "pending" =
   * steel/faint node (not reached yet). */
  state: "done" | "current" | "pending";
}

/**
 * The literal "payment flows mapped with fine lines, labeled nodes" motif
 * from the Modern Treasury design system (docs/FRONTEND_DESIGN_DECISION.md
 * sec 6), repurposed for the WeatherCover policy lifecycle instead of a
 * payment lifecycle. Used on the landing page (generic process) and the
 * Policy Result page (this specific policy's real timeline).
 *
 * Nodes fade/slide in with a short stagger and connectors grow downward --
 * a restrained, one-time reveal (not a looping animation) so re-reading the
 * page after a state change reads as "this just updated," per the brief's
 * "subtle premium interactions" / "timeline animations" request.
 */
export function FlowDiagram({ steps }: { steps: FlowStep[] }) {
  return (
    <div className="flex flex-col items-center">
      {steps.map((step, i) => (
        <div key={step.label} className="flex flex-col items-center">
          <div
            className="wc-fade-up flex w-full flex-col items-center gap-1 rounded-lg border px-5 py-3 text-center sm:w-auto"
            style={{
              borderColor: step.state === "pending" ? "var(--wc-rule-gray)" : "var(--wc-edge-gray)",
              background: step.state === "current" ? "var(--wc-ice-panel)" : "var(--wc-paper)",
              minWidth: "220px",
              animationDelay: `${i * 70}ms`,
            }}
          >
            <span
              className={`wc-dot ${step.state === "current" ? "wc-pulse" : ""}`}
              style={{
                background:
                  step.state === "done"
                    ? "var(--wc-network-green)"
                    : step.state === "current"
                      ? "var(--wc-ink)"
                      : "var(--wc-rule-gray)",
              }}
            />
            <span
              className="text-sm font-medium"
              style={{ color: step.state === "pending" ? "var(--wc-steel)" : "var(--wc-ink)" }}
            >
              {step.label}
            </span>
            {step.detail ? (
              <span className="wc-mono text-xs" style={{ color: "var(--wc-steel)" }}>
                {step.detail}
              </span>
            ) : null}
          </div>
          {i < steps.length - 1 ? (
            <div
              className="wc-connector wc-connector-animated"
              style={{
                background: step.state === "pending" ? "var(--wc-rule-gray)" : "var(--wc-network-green)",
                animationDelay: `${i * 70 + 120}ms`,
              }}
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}
