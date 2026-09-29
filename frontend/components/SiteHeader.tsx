import Link from "next/link";
import { ConnectWalletButton } from "./ConnectWalletButton";
import { RESOLVED_DEMO_EVENT_ID } from "@/lib/demo/knownData";

const NAV_LINK_CLASS =
  "whitespace-nowrap transition-colors hover:text-[var(--wc-ink)]";

export function SiteHeader() {
  return (
    <header className="border-b" style={{ borderColor: "var(--wc-rule-gray)" }}>
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-4 sm:px-6">
        <Link href="/" className="flex min-w-0 items-baseline gap-2">
          <span className="wc-display text-base sm:text-lg">WeatherCover</span>
          <span className="wc-mono hidden text-xs sm:inline" style={{ color: "var(--wc-steel)" }}>
            on WeatherResolve
          </span>
        </Link>
        <nav className="hidden gap-6 text-sm md:flex" style={{ color: "var(--wc-graphite)" }}>
          <Link href="/dashboard" className={NAV_LINK_CLASS}>
            Dashboard
          </Link>
          <Link href="/create-policy" className={NAV_LINK_CLASS}>
            Create Policy
          </Link>
          <Link href={`/observations/${RESOLVED_DEMO_EVENT_ID}`} className={NAV_LINK_CLASS}>
            Evidence Explorer
          </Link>
        </nav>
        <ConnectWalletButton />
      </div>
      {/* Compact nav row on small screens -- horizontally scrollable rather
          than a hamburger, since there are only three destinations. */}
      <div
        className="flex gap-5 overflow-x-auto border-t px-4 py-2 text-xs md:hidden"
        style={{ borderColor: "var(--wc-rule-gray)", color: "var(--wc-graphite)" }}
      >
        <Link href="/dashboard" className={NAV_LINK_CLASS}>
          Dashboard
        </Link>
        <Link href="/create-policy" className={NAV_LINK_CLASS}>
          Create Policy
        </Link>
        <Link href={`/observations/${RESOLVED_DEMO_EVENT_ID}`} className={NAV_LINK_CLASS}>
          Evidence Explorer
        </Link>
      </div>
    </header>
  );
}
