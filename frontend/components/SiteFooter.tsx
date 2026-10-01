export function SiteFooter() {
  return (
    <footer style={{ background: "var(--wc-forest-ledger)", color: "var(--wc-paper)" }}>
      <div className="mx-auto max-w-6xl px-4 py-8 text-sm sm:px-6 sm:py-10">
        <p className="wc-display text-base">WeatherResolve + WeatherCover</p>
        <p className="mt-2 max-w-2xl" style={{ color: "rgba(255,255,255,0.6)" }}>
          WeatherResolve is reusable real-world observation infrastructure on GenLayer: it retrieves
          evidence from multiple independently retrieved weather sources, verifies location and date, normalizes values, and
          reaches validator consensus on what actually happened. WeatherCover is the first application
          built on top of it — a parametric coverage policy that reads a resolved observation and
          evaluates a deterministic condition. Neither layer trusts a single weather provider.
        </p>
        <p className="wc-mono mt-6 text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
          GenLayer StudioNet · frontend only, no funds, no escrow, simulated payouts only.
        </p>
      </div>
    </footer>
  );
}
