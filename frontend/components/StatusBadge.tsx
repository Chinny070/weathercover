import type { CoverStatus, EventStatus, RetrievalStatus } from "@/lib/genlayer/types";

type Kind = "confirmed" | "unresolved" | "neutral";

const EVENT_STATUS_KIND: Record<EventStatus, Kind> = {
  PENDING: "neutral",
  RESOLVING: "neutral",
  RESOLVED: "confirmed",
  UNRESOLVED: "unresolved",
};

const COVER_STATUS_KIND: Record<CoverStatus, Kind> = {
  PENDING: "neutral",
  TRIGGERED: "confirmed",
  NOT_TRIGGERED: "neutral",
  UNRESOLVED: "unresolved",
};

const RETRIEVAL_STATUS_KIND: Record<RetrievalStatus, Kind> = {
  PENDING: "neutral",
  AVAILABLE: "confirmed",
  UNAVAILABLE: "unresolved",
  FETCH_FAILED: "unresolved",
  RENDER_FAILED: "unresolved",
  TIMEOUT: "unresolved",
  INVALID_RESPONSE: "unresolved",
  WRONG_LOCATION: "unresolved",
  WRONG_DATE: "unresolved",
  UNSUPPORTED_UNIT: "unresolved",
  CONFLICTING: "unresolved",
};

const DOT_CLASS: Record<Kind, string> = {
  confirmed: "wc-dot-confirmed",
  unresolved: "wc-dot-unresolved",
  neutral: "wc-dot-neutral",
};

function Pill({ label, kind }: { label: string; kind: Kind }) {
  return (
    <span className="wc-badge">
      <span className={`wc-dot ${DOT_CLASS[kind]}`} />
      {label.replace(/_/g, " ")}
    </span>
  );
}

export function EventStatusBadge({ status }: { status: EventStatus }) {
  return <Pill label={status} kind={EVENT_STATUS_KIND[status]} />;
}

export function CoverStatusBadge({ status }: { status: CoverStatus }) {
  return <Pill label={status} kind={COVER_STATUS_KIND[status]} />;
}

export function RetrievalStatusBadge({ status }: { status: RetrievalStatus }) {
  return <Pill label={status} kind={RETRIEVAL_STATUS_KIND[status]} />;
}

export function FetchModeBadge({ mode }: { mode: "get" | "render" }) {
  return <span className="wc-badge">{mode === "get" ? "FETCH" : "RENDER"}</span>;
}
