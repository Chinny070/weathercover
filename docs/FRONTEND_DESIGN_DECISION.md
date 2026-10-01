# WeatherCover — Frontend Design Decision

Source: [styles.refero.design](https://styles.refero.design/), browsed and evaluated before any frontend code was written.

---

## 1. Selected Design Inspiration

**Modern Treasury** — "Treasury ledger on graph paper."
`https://styles.refero.design/style/2e9b3dcb-f937-488d-891c-351c7366188f`

> The interface is a white financial canvas structured by faint grid lines, thin rules, and technical connector diagrams, with dark ink carrying almost all hierarchy. Large, softly weighted display headlines sit above compact operational UI; pale blue and muted plum blocks isolate product narratives, while deep forest green anchors the footer. Color is restrained to mint subscription controls, green network lines, and brown monospace labels, so the system reads as a payment infrastructure diagram rather than a colorful dashboard.

**Runner-up considered and rejected:** *Increase* ("institutional blueprint on vellum") — a close second, also a payment-infrastructure company with a technical, restrained aesthetic. Rejected in favor of Modern Treasury because Increase's blueprint linework reads as *engineering schematic* (pipes, systems), whereas Modern Treasury's explicit precedent — "money flows mapped with fine lines, labeled nodes, and exact dark controls" — is a **flow diagram of discrete, labeled steps**, which is exactly the shape of WeatherCover's core visual: `Policy Created → Weather Observed → Evidence Verified → Condition Evaluated → Coverage Decision`. Modern Treasury's system was built to diagram a *process*, not just a network; that is precisely what this product needs to communicate.

---

## 2. Why It Fits WeatherCover

Evaluated against every criterion in the brief, not just visual appeal:

| Criterion | Why Modern Treasury satisfies it |
|---|---|
| **Trust** | White canvas, dark ink, hairline rules, no gradients or glow — reads as a serious financial operating system, not a marketing site or a crypto dashboard. |
| **Insurance/financial product feel** | It *is* a real payment-infrastructure company's design language — restrained, audited-feeling, numbers-first. WeatherCover is parametric insurance infrastructure; this is a direct category match, not a borrowed aesthetic. |
| **Weather/nature connection** | Network Green (`#29735c`) as the sole accent for "connector paths and infrastructure accents" reads naturally as environmental/verification green without forcing a literal weather-app palette (sun icons, blue skies) that would undercut the "this is not a weather app" message. |
| **Data visualization quality** | The system is built around a grid canvas with labeled nodes and connector lines — this is functionally identical to what the Evidence Explorer and process-flow diagrams need: discrete steps, connected, each labeled with a status. |
| **Evidence presentation** | "Graph paper" as the base canvas is a measurement/precision metaphor. Each evidence source becomes a labeled cell on that grid — the literal design language of "here is a measured, recorded fact," which is the entire point of the Evidence Package. |
| **Premium SaaS/product quality** | Modern Treasury is a real, funded infrastructure company's production design system — proven restraint, proven typographic discipline, not a template. |
| **Explaining complex verification simply** | The guideline set explicitly favors "quiet" typography (450-weight display, never bold) and forbids decorative additions (no drop shadows on panels, no floating gradient tiles) — this keeps focus on the *content* of a verification (what was checked, what was found) rather than decorating around it. |

---

## 3. Color System

Adopted directly from the source tokens, mapped to WeatherCover's semantic roles:

| Token | Hex | WeatherCover role |
|---|---|---|
| `--color-paper` | `#ffffff` | Page canvas, cards, inputs — the dominant surface everywhere |
| `--color-ink` | `#151515` | Headings, primary body text, filled buttons, dark rules |
| `--color-graphite` | `#424242` | Secondary body copy, dense explanatory text (e.g. evidence detail strings) |
| `--color-steel` | `#706f6f` | Muted metadata: timestamps, source URLs, fine print |
| `--color-rule-gray` | `#dcdcdc` | Hairline dividers, the graph-paper grid itself, table rules |
| `--color-edge-gray` | `#cbcac8` | Stronger borders: card edges, input outlines |
| `--color-ice-panel` | `#f0f8f9` | Contained panels: the Evidence Explorer's source cards, "how it works" panels |
| `--color-forest-ledger` | `#0c221d` | Footer / closing full-width surfaces only |
| `--color-network-green` | `#29735c` | **Reserved exclusively** for connector lines between flow steps, the WeatherResolve infrastructure mark, and small "verified" accents (checkmarks, AVAILABLE badges) |
| `--color-plum-ledger` | `#543b4e` | UNRESOLVED state card treatment (a deliberate, distinct "this needs attention" tone, never used for ordinary content) |
| `--color-ledger-brown` | `#7b5953` | Monospace technical labels: retrieval status codes, hex IDs, fixed-point values |

**Status-color mapping (new, product-specific, derived from the palette's own restraint rule — one accent per meaning, never decorative):**
- `RESOLVED` / `AVAILABLE` / `TRIGGERED` → Network Green (`#29735c`), the only "good/confirmed" color in the system
- `UNRESOLVED` → Plum Ledger (`#543b4e`), a deliberately distinct tone — not red/error, because UNRESOLVED is a first-class honest outcome, not a failure
- `NOT_TRIGGERED` → Ink/Graphite (neutral) — a valid, unremarkable outcome, not styled as bad news
- Retrieval failures (`WRONG_LOCATION`, `FETCH_FAILED`, etc.) → Ledger Brown, monospace — technical detail, not alarming

No red is introduced anywhere. This is deliberate: WeatherCover's failure modes (`UNRESOLVED`, a rejected source) are honest infrastructure outcomes, not errors to be panic-colored.

---

## 4. Typography Direction

- **Display** (`mt-neue-display`, substitute **Manrope**, weight 450 only, never bolder): hero headline ("Weather conditions verified. Coverage decisions automated."), major section headings. Kept at weight 450 per the source's own rule — quiet, wide, never shouting.
- **Feature/narrative** (`mt-neue-text`, substitute **Manrope**, weight 400, 21–32px): section intros, the process-flow step labels, policy card titles ("Lagos Rain Protection").
- **Body/UI** (`mt-sans`, substitute **Inter**, weights 330–600, 14–18px): all body copy, table cells, form labels, button text, navigation.
- **Monospace accent** (system mono, e.g. `ui-monospace`/`SFMono-Regular`/`Menlo`): event IDs, transaction hashes, retrieval status codes, fixed-point values (`1230` / `12.30mm`) — signals "this is a raw, verifiable data value," reinforcing the evidence theme every time a number appears.

Rule carried over directly: never set display headlines above weight 450–500. A bold, shouting headline would undercut the "quiet, audited" trust signal this whole system is built on.

---

## 5. Spacing / Layout Rules

- 4px base spacing grid (source token), 48px section gaps, 24px card padding, 8px intra-component gaps.
- Max content width capped (source token pattern) — pages read as a single operating sheet, not a full-bleed marketing scroll.
- Border radius: **≤8px on cards, ≤4px on rectangular controls** (source "Don't" rule, adopted as-is) — this is what keeps the product feeling like infrastructure rather than a consumer app.
- No drop shadows on panels (source "Don't" rule) — depth comes from the Rule Gray grid and hairline borders, never from shadow elevation.
- The faint background grid (graph paper) is used on the landing page hero and the Evidence Explorer background specifically — anywhere the product is making a "this is measured, this is precise" claim. It is **not** used on the dashboard or create-policy form, where it would be visual noise around a task the user is trying to complete quickly.

---

## 6. Component Style

- **Cards**: Paper background, Rule Gray 1px border, 8px radius, no shadow. Status is communicated by a small colored dot/badge (Network Green / Plum Ledger / neutral Ink), never by recoloring the whole card — keeps the canvas quiet even when showing many policies at once.
- **Buttons**: Filled Ink with Paper text for primary actions (create policy, evaluate); outlined Ink for secondary; 2–4px radius, 8px×16px padding, per source guideline. No gradient buttons anywhere.
- **Flow diagrams** (the `↓` sequences in the brief): rendered as vertically-stacked labeled nodes connected by thin Network Green connector lines — a direct, literal application of the source system's own "payment flows mapped with fine lines, labeled nodes" pattern to WeatherCover's policy lifecycle instead of a payment lifecycle.
- **Evidence source rows**: table-like list, each row a hairline-bordered cell on the graph-paper canvas — Source name (Manrope), Retrieval method (monospace badge: `FETCH`/`RENDER`), Status (colored badge), Normalized value (monospace, right-aligned like a ledger figure).
- **Transaction/request state indicator**: inline state progresses `Submitted` → `Pending` → `Accepted — waiting for GenLayer finality…` (all visibly in progress) → `Finalized` (Network Green, only after actual `FINALIZED`) or `Failed` (Plum Ledger). This shares the RESOLVED/UNRESOLVED badge family while keeping acceptance distinct from finality.

---

## 7. Dashboard Style

The user dashboard is **not** a trading-terminal-style dense grid (rejected the "Fey"/"Depot" nocturnal-terminal candidates for exactly this reason — too crypto-dashboard, contradicts the brief). Instead: a clean, light, card-based list on the Paper canvas, one policy per card, generous 24px padding, sorted active-first. This matches Modern Treasury's own operational pages (quiet operating sheet, not a monitoring wall) and directly serves the brief's instruction to avoid "a generic crypto dashboard."

---

## 8. Data Visualization Approach

Two visualization needs, two different treatments, both derived from the same graph-paper motif:

1. **Process flow** (landing page, policy result timeline): vertical or horizontal node-and-connector diagram, Network Green lines, ink-colored nodes, each labeled in `mt-sans` — literally the source system's payment-flow diagram pattern repurposed for policy lifecycle.
2. **Evidence comparison** (Evidence Explorer): a simple aligned table/grid on the faint graph-paper background — no charts, no gauges. The three current sample values (12.30mm / 10.40mm / 12.30mm) sit close together; the grid makes their agreement easy to scan without a bar chart. This is deliberately restrained — the brief warns against this looking like "a weather API dashboard," and a flashy chart would push it back in that direction.

---

## 9. How the Design Communicates Trust and Verification

- **Graph paper as base canvas** = a measurement instrument's background, not a marketing surface. Every number placed on it reads as *recorded*, not decorative.
- **One accent color for "confirmed"** (Network Green) used consistently for `RESOLVED`/`AVAILABLE`/`TRIGGERED`/checkmarks means the user's eye learns a single, unambiguous "verified" signal across the entire app.
- **Monospace for raw values** (hashes, event IDs, mm-values) signals "this is the actual underlying data, not summarized," reinforcing that the user can inspect the real evidence at any time.
- **No red, no alarm colors** for `UNRESOLVED` — Plum Ledger instead — communicates that an unresolved observation is an honest, expected infrastructure state (the architecture's own "UNRESOLVED is a first-class outcome" principle), not a system failure, which is core to the product's credibility.
- **Restraint itself is the trust signal**: a system that resists decoration, gradients, and shadows reads as audited and serious — exactly the opposite impression a "weather app" or "crypto dashboard" would give, which is the explicit thing this brief asks us to avoid.

---

## Next Step

Per your instruction, implementation stops here pending your approval of this design direction. On approval, I will scaffold the frontend (contract interaction layer, typed models, and the five required pages) using this system as the single source of design truth — no separate design exploration during build.
