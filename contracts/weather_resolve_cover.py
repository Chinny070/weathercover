# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

# =============================================================================
# WEATHERRESOLVE + WEATHERCOVER  (single contract: WeatherResolveCover)
#
# StudioNet MVP. One deployed contract, two internal layers (see
# docs/IMPLEMENTATION_PLAN.md sec 1 for why cross-contract calls are not
# used yet):
#
#   WeatherResolve layer (event_/policy_/resolve_/observation_ prefixes):
#     event creation, source policies, evidence retrieval, observation
#     resolution, finalized Observation Registry.
#
#   WeatherCover layer (cover_ prefix):
#     policy creation, condition evaluation, simulated payout tracking.
#
# Step 4: real GenLayer web retrieval (gl.nondet.web.get/render, wrapped
# in gl.vm.run_nondet leader/validator consensus) sits behind
# _classify_and_extract, a generic evidence-retrieval primitive -- no
# per-weather-provider parsing logic. See the "Resolution model" section
# below for the full rationale.
# =============================================================================


# --- Frozen MVP scope constants ---------------------------------------------
#
# Location is now a REGISTRY, not a hardcoded tuple (see LocationProfile /
# location_register_profile below): a location_id is only valid once an
# owner-registered profile exists for it. LOCATION_LAGOS_NG is kept as a
# convenience constant for the MVP deployment's seed data and tests, not
# as a gate in the contract's own validation logic.

LOCATION_LAGOS_NG = "LAGOS_NG"
METRIC_RAIN_24H = "RAIN_24H"

_SUPPORTED_METRICS = (METRIC_RAIN_24H,)
_SUPPORTED_UNITS = ("mm", "in")

# --- Event status ------------------------------------------------------------

EVENT_STATUS_PENDING = "PENDING"
EVENT_STATUS_RESOLVING = "RESOLVING"
EVENT_STATUS_RESOLVED = "RESOLVED"
EVENT_STATUS_UNRESOLVED = "UNRESOLVED"
_EVENT_STATUSES = (
    EVENT_STATUS_PENDING,
    EVENT_STATUS_RESOLVING,
    EVENT_STATUS_RESOLVED,
    EVENT_STATUS_UNRESOLVED,
)

# --- Per-source retrieval status (architecture sec 7) ------------------------

RETRIEVAL_AVAILABLE = "AVAILABLE"
RETRIEVAL_UNAVAILABLE = "UNAVAILABLE"
RETRIEVAL_FETCH_FAILED = "FETCH_FAILED"
RETRIEVAL_RENDER_FAILED = "RENDER_FAILED"
RETRIEVAL_TIMEOUT = "TIMEOUT"
RETRIEVAL_INVALID_RESPONSE = "INVALID_RESPONSE"
RETRIEVAL_WRONG_LOCATION = "WRONG_LOCATION"
RETRIEVAL_WRONG_DATE = "WRONG_DATE"
RETRIEVAL_UNSUPPORTED_UNIT = "UNSUPPORTED_UNIT"
RETRIEVAL_CONFLICTING = "CONFLICTING"
RETRIEVAL_PENDING = "PENDING"  # not yet retrieved (evidence slot not filled)
_RETRIEVAL_STATUSES = (
    RETRIEVAL_PENDING,
    RETRIEVAL_AVAILABLE,
    RETRIEVAL_UNAVAILABLE,
    RETRIEVAL_FETCH_FAILED,
    RETRIEVAL_RENDER_FAILED,
    RETRIEVAL_TIMEOUT,
    RETRIEVAL_INVALID_RESPONSE,
    RETRIEVAL_WRONG_LOCATION,
    RETRIEVAL_WRONG_DATE,
    RETRIEVAL_UNSUPPORTED_UNIT,
    RETRIEVAL_CONFLICTING,
)

# --- Evidence sufficiency + resolution reason --------------------------------

EVIDENCE_STATUS_SUFFICIENT = "SUFFICIENT"
EVIDENCE_STATUS_INSUFFICIENT = "INSUFFICIENT"
_EVIDENCE_STATUSES = (EVIDENCE_STATUS_SUFFICIENT, EVIDENCE_STATUS_INSUFFICIENT)

RESOLUTION_REASON_OK = "OK"
RESOLUTION_REASON_INSUFFICIENT_SOURCES = "INSUFFICIENT_SOURCES"
RESOLUTION_REASON_MISSING_REQUIRED_CLASS = "MISSING_REQUIRED_CLASS"
RESOLUTION_REASON_DISAGREEMENT = "DISAGREEMENT"
RESOLUTION_REASON_SOURCE_FAILURE_POLICY = "SOURCE_FAILURE_POLICY"
RESOLUTION_REASON_NOT_YET_RESOLVED = "NOT_YET_RESOLVED"
_RESOLUTION_REASONS = (
    RESOLUTION_REASON_OK,
    RESOLUTION_REASON_INSUFFICIENT_SOURCES,
    RESOLUTION_REASON_MISSING_REQUIRED_CLASS,
    RESOLUTION_REASON_DISAGREEMENT,
    RESOLUTION_REASON_SOURCE_FAILURE_POLICY,
    RESOLUTION_REASON_NOT_YET_RESOLVED,
)

# --- Source policy config -----------------------------------------------------

FETCH_MODE_GET = "get"
FETCH_MODE_RENDER = "render"
_ALLOWED_FETCH_MODES = (FETCH_MODE_GET, FETCH_MODE_RENDER)

SOURCE_BEHAVIOR_SKIP = "SKIP"
SOURCE_BEHAVIOR_FAIL_POLICY = "FAIL_POLICY"
_ALLOWED_SOURCE_BEHAVIORS = (SOURCE_BEHAVIOR_SKIP, SOURCE_BEHAVIOR_FAIL_POLICY)

# --- WeatherCover ------------------------------------------------------------

COVER_OPERATOR_BELOW = "BELOW"
COVER_OPERATOR_ABOVE = "ABOVE"
_COVER_OPERATORS = (COVER_OPERATOR_BELOW, COVER_OPERATOR_ABOVE)

COVER_STATUS_PENDING = "PENDING"
COVER_STATUS_TRIGGERED = "TRIGGERED"
COVER_STATUS_NOT_TRIGGERED = "NOT_TRIGGERED"
COVER_STATUS_UNRESOLVED = "UNRESOLVED"
_COVER_STATUSES = (
    COVER_STATUS_PENDING,
    COVER_STATUS_TRIGGERED,
    COVER_STATUS_NOT_TRIGGERED,
    COVER_STATUS_UNRESOLVED,
)

# --- Bounds --------------------------------------------------------------------

MAX_POLICY_ID_LEN = 64
MAX_SOURCE_ID_LEN = 64
MAX_URL_LEN = 512
MAX_SOURCE_CLASS_LEN = 64
MAX_TIMESTAMP_LEN = 32
MAX_EXCERPT_LEN = 2000
MAX_SOURCES_PER_POLICY = 3  # MVP constraint: LAGOS_NG / RAIN_24H only, max 3 sources
MAX_REQUIRED_CLASSES_PER_POLICY = 4
MAX_EVENTS = 500
MAX_COVER_POLICIES = 2000
MAX_COVER_POLICIES_PER_OWNER = 200

MAX_LOCATION_ID_LEN = 64
MAX_CANONICAL_NAME_LEN = 128
MAX_COUNTRY_LEN = 64
MAX_ALIAS_LEN = 128
MAX_ALIASES_PER_LOCATION = 6

MAX_THRESHOLD_MM100 = 100000  # 1000.00mm -- generous sanity ceiling, not a real climate limit
MIN_SIMULATED_PAYOUT = 1


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise Exception(message)


def _coerce_address(value) -> Address:
    # Address-typed inputs have been observed to arrive as Address, raw
    # bytes, or a plain int depending on the calling environment (verified
    # live on StudioNet in a prior project on this same runner pin --
    # Address(some_int) allocates a zero-filled buffer of THAT MANY bytes
    # rather than encoding the int, which overflows for real addresses).
    if isinstance(value, Address):
        return value
    if isinstance(value, int):
        return Address(value.to_bytes(20, "big"))
    return Address(value)


def _address_key(address: Address) -> str:
    # Canonical string form of an Address, used both for display
    # (to_dict) and as a TreeMap key (simulated_balances, dedupe, and
    # per-owner indexes) so the same address always maps to the same key
    # regardless of how it arrived (see _coerce_address).
    return address.as_hex if hasattr(address, "as_hex") else str(address)


def _validate_bounded_text(value: str, min_len: int, max_len: int, field_name: str) -> None:
    _require(isinstance(value, str), f"EXPECTED:INVALID_TYPE:{field_name}")
    _require(len(value) >= min_len, f"EXPECTED:TOO_SHORT:{field_name}")
    _require(len(value) <= max_len, f"EXPECTED:TOO_LONG:{field_name}")


def _validate_observation_period(value: str) -> None:
    # Deterministic string-shape check only (YYYY-MM-DD). Calendar-aware
    # validation and window math belong to Step 3 resolution logic, not
    # event creation.
    _require(isinstance(value, str), "EXPECTED:INVALID_TYPE:observation_period")
    _require(len(value) == 10, "EXPECTED:MALFORMED_OBSERVATION_PERIOD")
    _require(value[4] == "-" and value[7] == "-", "EXPECTED:MALFORMED_OBSERVATION_PERIOD")
    year, month, day = value[0:4], value[5:7], value[8:10]
    _require(year.isdigit() and month.isdigit() and day.isdigit(), "EXPECTED:MALFORMED_OBSERVATION_PERIOD")
    _require(1 <= int(month) <= 12, "EXPECTED:MALFORMED_OBSERVATION_PERIOD")
    _require(1 <= int(day) <= 31, "EXPECTED:MALFORMED_OBSERVATION_PERIOD")


def _fnv1a(text: str) -> int:
    # Pure-Python FNV-1a, no hashlib import: stdlib import availability
    # under the pinned GenVM runner is not something to gamble with inside
    # a contract module (see workspace memory on Studio schema-load
    # failures from unverified imports). Pure arithmetic only.
    h = 0xCBF29CE484222325
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


# =============================================================================
# Storage dataclasses
# =============================================================================


@allow_storage
class LocationProfile:
    """
    A Location Resolution Profile: what evidence must actually say to
    count as "about this location_id". Generic infrastructure -- nothing
    here is Lagos-specific; a future location is just another registered
    profile, with no change to retrieval/validation code.
    """

    location_id: str
    canonical_name: str
    country: str
    aliases: DynArray[str]
    has_coordinates: bool
    lat_hundredths: u256  # magnitude only (degrees * 100); sign in lat_is_south
    lat_is_south: bool
    lon_hundredths: u256  # magnitude only (degrees * 100); sign in lon_is_west
    lon_is_west: bool
    radius_km: u256

    def __init__(
        self,
        location_id: str,
        canonical_name: str,
        country: str,
        has_coordinates: bool,
        lat_hundredths: u256,
        lat_is_south: bool,
        lon_hundredths: u256,
        lon_is_west: bool,
        radius_km: u256,
    ):
        self.location_id = location_id
        self.canonical_name = canonical_name
        self.country = country
        self.has_coordinates = has_coordinates
        self.lat_hundredths = lat_hundredths
        self.lat_is_south = lat_is_south
        self.lon_hundredths = lon_hundredths
        self.lon_is_west = lon_is_west
        self.radius_km = radius_km

    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "canonical_name": self.canonical_name,
            "country": self.country,
            "aliases": [a for a in self.aliases],
            "has_coordinates": self.has_coordinates,
            "lat_hundredths": int(self.lat_hundredths),
            "lat_is_south": self.lat_is_south,
            "lon_hundredths": int(self.lon_hundredths),
            "lon_is_west": self.lon_is_west,
            "radius_km": int(self.radius_km),
        }


@allow_storage
class SourceSpec:
    """One configured evidence source inside a SourcePolicy."""

    source_id: str
    url: str
    fetch_mode: str  # "get" (FETCH: structured/static) | "render" (RENDER: dynamic pages)
    source_class: str  # e.g. "authoritative_met", "aggregator"
    reported_unit: str  # "mm" | "in" -- declared at config time, not scraped from the page

    def __init__(self, source_id: str, url: str, fetch_mode: str, source_class: str, reported_unit: str):
        self.source_id = source_id
        self.url = url
        self.fetch_mode = fetch_mode
        self.source_class = source_class
        self.reported_unit = reported_unit

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "fetch_mode": self.fetch_mode,
            "source_class": self.source_class,
            "reported_unit": self.reported_unit,
        }


@allow_storage
class SourcePolicy:
    """
    Configurable, versioned source-trust profile (change #5/#6: owner
    configures these at setup time; not hardcoded profiles).
    """

    policy_id: str
    min_source_count: u256
    required_source_classes: DynArray[str]
    disagreement_tolerance_mm100: u256  # fixed-point, x100 (2 decimal mm)
    unavailable_source_behavior: str  # SKIP | FAIL_POLICY
    timeout_behavior: str  # SKIP | FAIL_POLICY
    sources: DynArray[SourceSpec]
    version_locked: bool  # true once any event references this policy

    def __init__(
        self,
        policy_id: str,
        min_source_count: u256,
        disagreement_tolerance_mm100: u256,
        unavailable_source_behavior: str,
        timeout_behavior: str,
    ):
        self.policy_id = policy_id
        self.min_source_count = min_source_count
        self.disagreement_tolerance_mm100 = disagreement_tolerance_mm100
        self.unavailable_source_behavior = unavailable_source_behavior
        self.timeout_behavior = timeout_behavior
        self.version_locked = False
        # required_source_classes / sources (DynArray fields) are never
        # manually assigned: the storage framework auto-initializes them
        # to empty, and DynArray[...]() cannot be constructed directly
        # (verified against this runtime -- raises TypeError).

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "min_source_count": int(self.min_source_count),
            "required_source_classes": [c for c in self.required_source_classes],
            "disagreement_tolerance_mm100": int(self.disagreement_tolerance_mm100),
            "unavailable_source_behavior": self.unavailable_source_behavior,
            "timeout_behavior": self.timeout_behavior,
            "sources": [s.to_dict() for s in self.sources],
            "version_locked": self.version_locked,
        }


@allow_storage
class WeatherEvent:
    """A canonical observation REQUEST (architecture sec 3), not a result."""

    event_id: str
    location: str  # CITY_COUNTRY, frozen format (change #3)
    metric: str  # RAIN_24H only (change #4)
    observation_period: str  # "YYYY-MM-DD", UTC calendar day
    source_policy_id: str
    created_at: str
    status: str  # PENDING | RESOLVED | UNRESOLVED
    consumer_count: u256

    def __init__(
        self,
        event_id: str,
        location: str,
        metric: str,
        observation_period: str,
        source_policy_id: str,
        created_at: str,
    ):
        self.event_id = event_id
        self.location = location
        self.metric = metric
        self.observation_period = observation_period
        self.source_policy_id = source_policy_id
        self.created_at = created_at
        self.status = EVENT_STATUS_PENDING
        self.consumer_count = u256(0)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "location": self.location,
            "metric": self.metric,
            "observation_period": self.observation_period,
            "source_policy_id": self.source_policy_id,
            "created_at": self.created_at,
            "status": self.status,
            "consumer_count": int(self.consumer_count),
        }


@allow_storage
class SourceEvidence:
    """
    Per-source Evidence Explorer row (change #4 in the latest instructions):
    what the frontend needs to show sources checked, retrieval status,
    normalized values, and agreement/disagreement -- for one source, for
    one resolution attempt.
    """

    source_id: str
    url: str
    fetch_mode: str  # retrieval method: "get" | "render"
    retrieval_status: str
    reported_value_raw: str  # raw text extracted before normalization
    reported_unit: str
    normalized_value_mm100: u256  # 0 if not AVAILABLE/valid
    observation_timestamp: str
    excerpt_fingerprint: str  # FNV-1a hex digest of the retrieved excerpt
    location_match: str  # "" if not matched/not applicable; else how it matched
    location_detail: str  # human-readable match or rejection detail

    def __init__(self, source_id: str, url: str, fetch_mode: str):
        self.source_id = source_id
        self.url = url
        self.fetch_mode = fetch_mode
        self.retrieval_status = RETRIEVAL_PENDING
        self.reported_value_raw = ""
        self.reported_unit = ""
        self.normalized_value_mm100 = u256(0)
        self.observation_timestamp = ""
        self.excerpt_fingerprint = ""
        self.location_match = ""
        self.location_detail = ""

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "fetch_mode": self.fetch_mode,
            "retrieval_status": self.retrieval_status,
            "reported_value_raw": self.reported_value_raw,
            "reported_unit": self.reported_unit,
            "normalized_value_mm100": int(self.normalized_value_mm100),
            "observation_timestamp": self.observation_timestamp,
            "excerpt_fingerprint": self.excerpt_fingerprint,
            "location_match": self.location_match,
            "location_detail": self.location_detail,
        }


@allow_storage
class Observation:
    """
    Finalized Observation Registry entry AND Evidence Explorer view model
    for one event's resolution attempt (architecture sec 12/13, latest
    instructions change #4). Written on both RESOLVED and UNRESOLVED
    outcomes so an UNRESOLVED reason stays inspectable.
    """

    event_id: str
    requested_location_id: str  # the event's location_id, for the Explorer
    status: str  # RESOLVED | UNRESOLVED
    value_mm100: u256  # resolved value, fixed-point x100 mm; 0 if UNRESOLVED
    unit: str
    source_count: u256  # count of valid AVAILABLE sources used
    evidence_status: str  # SUFFICIENT | INSUFFICIENT
    resolution_reason: str
    resolved_at: str
    evidence: DynArray[SourceEvidence]  # per-source breakdown, all sources checked

    def __init__(self, event_id: str, requested_location_id: str):
        self.event_id = event_id
        self.requested_location_id = requested_location_id
        self.status = EVENT_STATUS_UNRESOLVED
        self.value_mm100 = u256(0)
        self.unit = "mm"
        self.source_count = u256(0)
        self.evidence_status = EVIDENCE_STATUS_INSUFFICIENT
        self.resolution_reason = RESOLUTION_REASON_NOT_YET_RESOLVED
        self.resolved_at = ""
        # evidence (DynArray field): auto-initialized empty, see note in
        # SourcePolicy.__init__.

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "requested_location_id": self.requested_location_id,
            "status": self.status,
            "value_mm100": int(self.value_mm100),
            "unit": self.unit,
            "source_count": int(self.source_count),
            "evidence_status": self.evidence_status,
            "resolution_reason": self.resolution_reason,
            "resolved_at": self.resolved_at,
            "evidence": [e.to_dict() for e in self.evidence],
        }


@allow_storage
class CoverPolicy:
    """
    WeatherCover: the first consumer application built on the
    WeatherResolve Observation Registry. A policy is pure condition
    evaluation + simulated bookkeeping -- it holds no retrieval,
    normalization, or resolution logic of its own; `location_id`,
    `metric`, and `observation_date` are denormalized (read once, at
    creation, from the referenced WeatherEvent) purely so a policy is
    self-describing for the history/detail views, not because
    WeatherCover re-derives or re-checks anything WeatherResolve already
    decided.
    """

    policy_id: str
    owner: Address
    weather_event_id: str  # the WeatherResolve event this policy reads
    location_id: str  # denormalized from the event, for display
    metric: str  # denormalized from the event, for display
    observation_date: str  # denormalized from the event, for display
    operator: str  # BELOW | ABOVE
    threshold_mm100: u256
    simulated_payout: u256
    credited_amount: u256  # 0 unless/until TRIGGERED; then == simulated_payout
    created_at: str
    evaluated_at: str  # "" until first evaluation
    status: str  # PENDING | TRIGGERED | NOT_TRIGGERED | UNRESOLVED

    def __init__(
        self,
        policy_id: str,
        owner: Address,
        weather_event_id: str,
        location_id: str,
        metric: str,
        observation_date: str,
        operator: str,
        threshold_mm100: u256,
        simulated_payout: u256,
        created_at: str,
    ):
        self.policy_id = policy_id
        self.owner = owner
        self.weather_event_id = weather_event_id
        self.location_id = location_id
        self.metric = metric
        self.observation_date = observation_date
        self.operator = operator
        self.threshold_mm100 = threshold_mm100
        self.simulated_payout = simulated_payout
        self.credited_amount = u256(0)
        self.created_at = created_at
        self.evaluated_at = ""
        self.status = COVER_STATUS_PENDING

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "owner": _address_key(self.owner),
            "weather_event_id": self.weather_event_id,
            "location_id": self.location_id,
            "metric": self.metric,
            "observation_date": self.observation_date,
            "operator": self.operator,
            "threshold_mm100": int(self.threshold_mm100),
            "simulated_payout": int(self.simulated_payout),
            "credited_amount": int(self.credited_amount),
            "created_at": self.created_at,
            "evaluated_at": self.evaluated_at,
            "status": self.status,
        }


# =============================================================================
# Resolution model: Evidence Package -> Normalization -> Validation ->
# Resolution. Retrieval (this section) is generic evidence infrastructure,
# not a weather-provider scraper: it fetches a URL, checks the retrieved
# text actually mentions the expected subject (location) and time
# (observation period), and pulls out the first decimal number in it. It
# has no per-provider parsing rules -- any structured/semi-structured
# source that states its number in text works the same way.
#
# GenLayer judgment (gl.nondet.exec_prompt) is used ONLY for semantic
# verification of retrieval fidelity: when leader and validator retrieve
# byte-different text for the same URL, an LLM judges whether it is
# substantively the same source (ignoring incidental noise) -- the same
# Tier-1 pattern verified working in protocolcourt/contracts/
# protocol_court.py's _fetch_evidence/submit_evidence. It never touches
# numeric extraction, unit conversion, tolerance, or aggregation -- those
# stay deterministic, per product direction.
# =============================================================================

MAX_RAW_FETCH_LEN = 20000


def _bound_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len]


def _extract_last_decimal_token(text: str):
    # Generic numeric-token scan, no regex (avoids depending on an
    # unverified stdlib module inside the contract) and no unit/provider
    # awareness: finds every "<digits>[.<digits>]" run and returns the
    # LAST one. Deliberately last, not first: real structured API
    # responses conventionally echo request metadata (coordinates,
    # generation time, elevation, UTC offset) before the actual
    # requested reading, so the last number in the text is a more
    # reliable generic signal than the first once the location/date
    # markers themselves are masked out (see _classify_and_extract).
    n = len(text)
    i = 0
    last_token = None
    while i < n:
        if text[i].isdigit():
            j = i
            seen_dot = False
            while j < n and (text[j].isdigit() or (text[j] == "." and not seen_dot)):
                if text[j] == ".":
                    seen_dot = True
                j += 1
            token = text[i:j]
            if token != "." and token != "":
                last_token = token
            i = j
        else:
            i += 1
    return last_token


def _match_location_by_name(raw_text: str, location_ctx: dict):
    # Generic name-based match -- no location_id (internal token) is ever
    # compared against evidence text, since real sources never contain
    # it. Returns (matched_via, matched_text) or None.
    #
    # Disambiguation rule: a bare canonical-name substring is not, on its
    # own, treated as sufficient -- many city names are reused across
    # countries (Lagos, Nigeria vs. Lagos, Portugal is the canonical
    # example). If the profile has a country configured, a canonical-name
    # match only counts when the country is ALSO present in the same
    # text; a country string is a disambiguator, not by itself proof of
    # a specific city, so it is never accepted alone. An alias is
    # exempt from this: the registrant chose its exact text, so it is
    # presumed already disambiguated (e.g. "Lagos, Nigeria" registered as
    # one alias) and matches on its own.
    lower_text = raw_text.lower()

    for alias in location_ctx["aliases"]:
        if alias and alias.lower() in lower_text:
            return ("ALIAS", alias)

    canonical_name = location_ctx["canonical_name"]
    if canonical_name and canonical_name.lower() in lower_text:
        country = location_ctx["country"]
        if not country or country.lower() in lower_text:
            return ("CANONICAL_NAME", canonical_name)

    return None


def _find_labeled_number(raw_text: str, lower_text: str, labels: tuple):
    # Generic: find the first occurrence of any of `labels` (e.g. "lat",
    # "latitude") and read the first signed decimal number that follows
    # it within a short window. Works across many APIs that use these
    # conventional field names -- not tied to any one provider's schema.
    # Returns (value: float, matched_token: str) so the caller can also
    # mask the token out of the text before extracting the actual
    # reading, or None.
    best_idx = None
    best_label_len = 0
    for label in labels:
        idx = lower_text.find(label)
        if idx != -1 and (best_idx is None or idx < best_idx):
            best_idx = idx
            best_label_len = len(label)
    if best_idx is None:
        return None

    window = raw_text[best_idx + best_label_len : best_idx + best_label_len + 30]
    n = len(window)
    i = 0
    while i < n:
        ch = window[i]
        if ch.isdigit() or (ch in "+-" and i + 1 < n and window[i + 1].isdigit()):
            j = i + 1 if ch in "+-" else i
            seen_dot = False
            while j < n and (window[j].isdigit() or (window[j] == "." and not seen_dot)):
                if window[j] == ".":
                    seen_dot = True
                j += 1
            token = window[i:j]
            hundredths = _parse_decimal_to_hundredths(token)
            return None if hundredths is None else (hundredths / 100.0, token)
        i += 1
    return None


def _match_location_by_coordinates(raw_text: str, location_ctx: dict):
    # Generic coordinate-proximity match, used only when a source has no
    # name/alias/country mention but the profile has coordinates
    # configured. Distance is a flat-earth approximation (adequate at the
    # city/radius scale this is used for) using only +,-,*,**0.5 -- no
    # `math` import, consistent with this module's no-unverified-stdlib
    # rule.
    if not location_ctx["has_coordinates"]:
        return None
    lower_text = raw_text.lower()
    lat_found = _find_labeled_number(raw_text, lower_text, ("latitude", "lat"))
    lon_found = _find_labeled_number(raw_text, lower_text, ("longitude", "lng", "lon"))
    if lat_found is None or lon_found is None:
        return None
    lat_val, lon_val = lat_found[0], lon_found[0]
    lat_diff = lat_val - location_ctx["lat"]
    lon_diff = lon_val - location_ctx["lon"]
    distance_km = ((lat_diff**2 + lon_diff**2) ** 0.5) * 111.0
    if distance_km <= location_ctx["radius_km"]:
        return ("COORDINATES", f"lat={lat_val},lon={lon_val}")
    return None


def _classify_and_extract(url: str, fetch_mode: str, location_ctx: dict, expected_period: str) -> dict:
    # Module-level, plain-data only: this is leader_fn's (and
    # validator_fn's) body, so it must hold no `self` reference to stay
    # cloudpickle-serializable for gl.vm.run_nondet (verified requirement,
    # protocol_court.py sec on _fetch_evidence). `location_ctx` is a
    # plain dict extracted from a LocationProfile storage object before
    # this closure is built, for the same reason.
    #
    # FETCH ("get") vs RENDER ("render"): FETCH is for structured/static
    # sources (gl.nondet.web.get, verified to return an object with
    # `.body` (bytes | None) and `.status` (int)); RENDER is for dynamic
    # pages needing JS execution (gl.nondet.web.render(url, mode="text"),
    # verified to return `str` or raise). Status code 408 is this
    # contract's OWN convention for a source signaling "timed out" --
    # gl.nondet.web.get does not expose a distinct timeout signal in the
    # verified API, so a raised exception is always classified as a hard
    # fetch/render failure, never as TIMEOUT.
    try:
        if fetch_mode == FETCH_MODE_GET:
            resp = gl.nondet.web.get(url)
            if resp.status == 408:
                return {"status": RETRIEVAL_TIMEOUT, "raw_text": ""}
            if resp.body is None or resp.status >= 400:
                return {"status": RETRIEVAL_UNAVAILABLE, "raw_text": ""}
            raw_text = resp.body.decode("utf-8", errors="replace")
        else:
            raw_text = gl.nondet.web.render(url, mode="text")
            if not isinstance(raw_text, str):
                return {"status": RETRIEVAL_RENDER_FAILED, "raw_text": ""}
    except Exception:
        failure_status = RETRIEVAL_FETCH_FAILED if fetch_mode == FETCH_MODE_GET else RETRIEVAL_RENDER_FAILED
        return {"status": failure_status, "raw_text": ""}

    raw_text = _bound_text(raw_text, MAX_RAW_FETCH_LEN)

    # Generic relevance check (Location Resolution Profile): does the
    # retrieved evidence reference the requested location by canonical
    # name, alias, country, or coordinate proximity -- never by the
    # internal location_id, which real-world sources never contain.
    name_match = _match_location_by_name(raw_text, location_ctx)
    mask_text = name_match[1] if name_match is not None else None
    if name_match is not None:
        location_match, location_detail = name_match[0], f"matched {name_match[0].lower()}: {name_match[1]}"
    else:
        coord_match = _match_location_by_coordinates(raw_text, location_ctx)
        if coord_match is not None:
            location_match, location_detail = coord_match
            location_detail = f"matched coordinates within {location_ctx['radius_km']}km: {coord_match[1]}"
        else:
            checked = ["canonical name", "aliases", "country"]
            if location_ctx["has_coordinates"]:
                checked.append("coordinates")
            return {
                "status": RETRIEVAL_WRONG_LOCATION,
                "raw_text": raw_text,
                "location_match": "",
                "location_detail": f"no match found (checked: {', '.join(checked)})",
            }

    if expected_period not in raw_text:
        return {
            "status": RETRIEVAL_WRONG_DATE,
            "raw_text": raw_text,
            "location_match": location_match,
            "location_detail": location_detail,
        }

    # Mask out the date, the matched location text, and any labeled
    # coordinate numbers before scanning for a value: a date like
    # "2026-08-30", and a query-echoed "latitude"/"longitude" pair, are
    # themselves runs of digits that would otherwise be picked up ahead
    # of the actual reading. Combined with reading the LAST remaining
    # number rather than the first (structured APIs conventionally list
    # request/metadata fields before the requested value), this reliably
    # lands on the real reading across differently-shaped real responses
    # without any provider-specific field-name parsing.
    search_text = raw_text.replace(expected_period, " " * len(expected_period))
    if mask_text:
        search_text = search_text.replace(mask_text, " " * len(mask_text))
    lower_search_text = search_text.lower()
    lat_found = _find_labeled_number(search_text, lower_search_text, ("latitude", "lat"))
    if lat_found is not None:
        search_text = search_text.replace(lat_found[1], " " * len(lat_found[1]), 1)
    lon_found = _find_labeled_number(search_text, search_text.lower(), ("longitude", "lng", "lon"))
    if lon_found is not None:
        search_text = search_text.replace(lon_found[1], " " * len(lon_found[1]), 1)
    numeric_token = _extract_last_decimal_token(search_text)
    if numeric_token is None:
        return {
            "status": RETRIEVAL_INVALID_RESPONSE,
            "raw_text": raw_text,
            "location_match": location_match,
            "location_detail": location_detail,
        }

    return {
        "status": RETRIEVAL_AVAILABLE,
        "raw_text": raw_text,
        "raw_value": numeric_token,
        "location_match": location_match,
        "location_detail": location_detail,
    }


def _fidelity_prompt(url: str, excerpt_a: str, excerpt_b: str) -> str:
    return (
        "You are checking whether two independently retrieved excerpts of "
        "the same web source represent the same substantive content.\n\n"
        f"Source URL: {url}\n\n"
        f"Excerpt A:\n{excerpt_a}\n\n"
        f"Excerpt B:\n{excerpt_b}\n\n"
        "Ignore incidental differences: timestamps, view counters, "
        "advertisement content, session tokens, cosmetic formatting, or "
        "boilerplate navigation text. Focus only on whether the "
        "substantive reported values and claims are the same.\n\n"
        'Respond with ONLY a JSON object of the exact shape '
        '{"faithful": true|false, "reason": "<short reason, one sentence>"} '
        "and nothing else."
    )


def _judged_faithful(judgment) -> bool:
    if not isinstance(judgment, dict):
        return False
    if set(judgment.keys()) != {"faithful", "reason"}:
        return False
    if not isinstance(judgment["faithful"], bool):
        return False
    if not isinstance(judgment["reason"], str) or len(judgment["reason"]) > 400:
        return False
    return judgment["faithful"]


def _parse_decimal_to_hundredths(value_str: str):
    # Deterministic decimal-string parser -> integer hundredths. No float
    # arithmetic: floats are avoided everywhere in this pipeline so that
    # independent retrievals/validators never disagree over rounding.
    # Returns None (not an exception) on malformed input so the caller can
    # classify it as INVALID_RESPONSE rather than aborting resolution.
    if not isinstance(value_str, str) or len(value_str) == 0:
        return None
    text = value_str.strip()
    if len(text) == 0:
        return None
    sign = 1
    if text[0] in "+-":
        sign = -1 if text[0] == "-" else 1
        text = text[1:]
    if "." in text:
        whole, frac = text.split(".", 1)
    else:
        whole, frac = text, ""
    if whole == "":
        whole = "0"
    if not whole.isdigit():
        return None
    if len(frac) > 0 and not frac.isdigit():
        return None
    frac = (frac + "00")[:2]  # pad/truncate to exactly 2 decimal digits
    hundredths = int(whole) * 100 + int(frac)
    return sign * hundredths


def _normalize_to_mm100(raw_value: str, raw_unit: str):
    # Deterministic unit conversion (architecture sec 10/12): returns
    # (normalized_value_mm100, classification) where classification is
    # None on success or a RETRIEVAL_* status explaining the rejection.
    parsed = _parse_decimal_to_hundredths(raw_value)
    if parsed is None:
        return (0, RETRIEVAL_INVALID_RESPONSE)
    if parsed < 0:
        return (0, RETRIEVAL_INVALID_RESPONSE)  # rainfall cannot be negative
    if raw_unit == "mm":
        return (parsed, None)
    if raw_unit == "in":
        # hundredths_of_inch * 25.4 == mm100, exact integer arithmetic.
        return ((parsed * 254) // 10, None)
    return (0, RETRIEVAL_UNSUPPORTED_UNIT)


def _median_mm100(values: list) -> int:
    # Deterministic aggregation (architecture sec 14/change #7): plain
    # integer median, no floating point.
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def _signed_degrees(hundredths: u256, is_negative: bool) -> float:
    # LocationProfile stores lat/lon as an unsigned magnitude + a
    # direction flag (see LocationProfile docstring) rather than a signed
    # storage field, since no verified GenLayer storage field type for a
    # signed int was found in protocol_court.py. This converts back to a
    # plain signed degree value for the coordinate-proximity match.
    magnitude = int(hundredths) / 100.0
    return -magnitude if is_negative else magnitude


# =============================================================================
# Contract skeleton
#
# Demo objective (release/demo path this contract exists to support):
#
#   create_weather_event -> resolve_weather_event -> Observation Registry
#   result -> cover_create_policy -> cover_evaluate_policy ->
#   TRIGGERED | NOT_TRIGGERED | UNRESOLVED
#
# resolve_weather_event now performs real GenLayer web retrieval on top
# of Step 1/2's storage and registries. cover_* methods (WeatherCover
# layer) remain a later step's job.
# =============================================================================


class WeatherResolveCover(gl.Contract):
    # Deploy-time owner: only address allowed to register/update source
    # policies (config authority, not funds custody -- no funds exist).
    owner: Address

    # --- WeatherResolve layer storage ---
    events: TreeMap[str, WeatherEvent]
    observations: TreeMap[str, Observation]
    source_policies: TreeMap[str, SourcePolicy]
    location_profiles: TreeMap[str, LocationProfile]
    next_event_seq: u256

    # --- WeatherCover layer storage ---
    cover_policies: TreeMap[str, CoverPolicy]
    cover_policy_ids_by_owner: TreeMap[str, DynArray[str]]
    cover_policy_dedupe: TreeMap[str, str]  # dedupe key -> policy_id
    simulated_balances: TreeMap[str, u256]
    next_cover_policy_seq: u256

    def __init__(self, owner: Address):
        self.owner = _coerce_address(owner)

        self.next_event_seq = u256(0)
        self.next_cover_policy_seq = u256(0)

    # -- internal helpers -----------------------------------------------------

    def _now(self) -> str:
        import datetime

        return datetime.datetime.now().isoformat()

    def _require_owner(self) -> None:
        _require(gl.message.sender_address == self.owner, "EXPECTED:NOT_OWNER")

    def _get_event(self, event_id: str) -> WeatherEvent:
        event = self.events.get(event_id)
        _require(event is not None, "EXPECTED:EVENT_NOT_FOUND")
        return event

    def _get_source_policy(self, policy_id: str) -> SourcePolicy:
        policy = self.source_policies.get(policy_id)
        _require(policy is not None, "EXPECTED:SOURCE_POLICY_NOT_FOUND")
        return policy

    def _get_location_profile(self, location_id: str) -> LocationProfile:
        profile = self.location_profiles.get(location_id)
        _require(profile is not None, "EXPECTED:LOCATION_PROFILE_NOT_FOUND")
        return profile

    # -- writes: Location Resolution Profile Registry -------------------------

    @gl.public.write
    def location_register_profile(
        self,
        location_id: str,
        canonical_name: str,
        country: str,
        has_coordinates: bool,
        lat_hundredths: u256,
        lat_is_south: bool,
        lon_hundredths: u256,
        lon_is_west: bool,
        radius_km: u256,
    ) -> None:
        self._require_owner()
        _validate_bounded_text(location_id, 1, MAX_LOCATION_ID_LEN, "location_id")
        _require(self.location_profiles.get(location_id) is None, "EXPECTED:LOCATION_PROFILE_ALREADY_EXISTS")
        _validate_bounded_text(canonical_name, 1, MAX_CANONICAL_NAME_LEN, "canonical_name")
        _validate_bounded_text(country, 1, MAX_COUNTRY_LEN, "country")

        self.location_profiles[location_id] = LocationProfile(
            location_id=location_id,
            canonical_name=canonical_name,
            country=country,
            has_coordinates=has_coordinates,
            lat_hundredths=lat_hundredths,
            lat_is_south=lat_is_south,
            lon_hundredths=lon_hundredths,
            lon_is_west=lon_is_west,
            radius_km=radius_km,
        )

    @gl.public.write
    def location_add_alias(self, location_id: str, alias: str) -> None:
        self._require_owner()
        profile = self._get_location_profile(location_id)
        _validate_bounded_text(alias, 1, MAX_ALIAS_LEN, "alias")
        _require(len(profile.aliases) < MAX_ALIASES_PER_LOCATION, "EXPECTED:MAX_ALIASES_REACHED")
        for existing_alias in profile.aliases:
            _require(existing_alias.lower() != alias.lower(), "EXPECTED:DUPLICATE_ALIAS")

        profile.aliases.append(alias)

    @gl.public.view
    def location_get_profile(self, location_id: str) -> dict:
        return self._get_location_profile(location_id).to_dict()

    @gl.public.view
    def location_exists(self, location_id: str) -> bool:
        return self.location_profiles.get(location_id) is not None

    @staticmethod
    def _compute_event_id(location: str, metric: str, observation_period: str, source_policy_id: str) -> str:
        # Deterministic hash over exactly the fields that define "what
        # observation is being asked for" (architecture sec 4). Any two
        # callers submitting the same canonical tuple land on the same id,
        # which is what makes duplicate-event reuse automatic rather than
        # requiring an off-chain lookup first.
        key = f"{location}|{metric}|{observation_period}|{source_policy_id}"
        return format(_fnv1a(key), "016x")

    # -- writes: Weather Event Registry ---------------------------------------

    @gl.public.write
    def event_create_weather_event(
        self,
        location: str,
        metric: str,
        observation_period: str,
        source_policy_id: str,
    ) -> str:
        _require(self.location_profiles.get(location) is not None, "EXPECTED:UNSUPPORTED_LOCATION")
        _require(metric in _SUPPORTED_METRICS, "EXPECTED:UNSUPPORTED_METRIC")
        _validate_observation_period(observation_period)
        policy = self._get_source_policy(source_policy_id)

        event_id = self._compute_event_id(location, metric, observation_period, source_policy_id)

        existing = self.events.get(event_id)
        if existing is not None:
            # Duplicate-event reuse (architecture sec 16): the same
            # canonical tuple never creates a second event. Each reuse
            # bumps consumer_count so the Explorer can show fan-out.
            existing.consumer_count = u256(int(existing.consumer_count) + 1)
            return event_id

        _require(int(self.next_event_seq) < MAX_EVENTS, "EXPECTED:MAX_EVENTS_REACHED")

        event = WeatherEvent(
            event_id=event_id,
            location=location,
            metric=metric,
            observation_period=observation_period,
            source_policy_id=source_policy_id,
            created_at=self._now(),
        )
        event.consumer_count = u256(1)
        self.events[event_id] = event
        self.next_event_seq = u256(int(self.next_event_seq) + 1)

        # First reference to this policy locks it against further
        # configuration changes (architecture sec 6: policies are
        # immutable once any event depends on them).
        policy.version_locked = True

        return event_id

    @gl.public.view
    def event_get_weather_event(self, event_id: str) -> dict:
        return self._get_event(event_id).to_dict()

    @gl.public.view
    def event_exists(self, event_id: str) -> bool:
        return self.events.get(event_id) is not None

    @gl.public.view
    def event_compute_id(
        self, location: str, metric: str, observation_period: str, source_policy_id: str
    ) -> str:
        # Lets a caller compute the canonical id up front (e.g. to check
        # event_exists before deciding whether to call create at all).
        return self._compute_event_id(location, metric, observation_period, source_policy_id)

    # -- writes: Source Policy Registry ---------------------------------------

    @gl.public.write
    def policy_register_source_policy(
        self,
        policy_id: str,
        min_source_count: u256,
        disagreement_tolerance_mm100: u256,
        unavailable_source_behavior: str,
        timeout_behavior: str,
    ) -> None:
        self._require_owner()
        _validate_bounded_text(policy_id, 1, MAX_POLICY_ID_LEN, "policy_id")
        _require(self.source_policies.get(policy_id) is None, "EXPECTED:SOURCE_POLICY_ALREADY_EXISTS")
        _require(int(min_source_count) >= 1, "EXPECTED:INVALID_MIN_SOURCE_COUNT")
        _require(
            unavailable_source_behavior in _ALLOWED_SOURCE_BEHAVIORS,
            "EXPECTED:INVALID_UNAVAILABLE_SOURCE_BEHAVIOR",
        )
        _require(timeout_behavior in _ALLOWED_SOURCE_BEHAVIORS, "EXPECTED:INVALID_TIMEOUT_BEHAVIOR")

        self.source_policies[policy_id] = SourcePolicy(
            policy_id=policy_id,
            min_source_count=min_source_count,
            disagreement_tolerance_mm100=disagreement_tolerance_mm100,
            unavailable_source_behavior=unavailable_source_behavior,
            timeout_behavior=timeout_behavior,
        )

    @gl.public.write
    def policy_add_source(
        self,
        policy_id: str,
        source_id: str,
        url: str,
        fetch_mode: str,
        source_class: str,
        reported_unit: str,
    ) -> None:
        self._require_owner()
        policy = self._get_source_policy(policy_id)
        _require(not policy.version_locked, "EXPECTED:SOURCE_POLICY_LOCKED")
        _validate_bounded_text(source_id, 1, MAX_SOURCE_ID_LEN, "source_id")
        _validate_bounded_text(url, 1, MAX_URL_LEN, "url")
        _require(fetch_mode in _ALLOWED_FETCH_MODES, "EXPECTED:INVALID_FETCH_MODE")
        _validate_bounded_text(source_class, 1, MAX_SOURCE_CLASS_LEN, "source_class")
        _require(reported_unit in _SUPPORTED_UNITS, "EXPECTED:INVALID_REPORTED_UNIT")
        _require(len(policy.sources) < MAX_SOURCES_PER_POLICY, "EXPECTED:MAX_SOURCES_PER_POLICY_REACHED")
        for existing_source in policy.sources:
            _require(existing_source.source_id != source_id, "EXPECTED:DUPLICATE_SOURCE_ID")

        policy.sources.append(SourceSpec(source_id, url, fetch_mode, source_class, reported_unit))

    @gl.public.write
    def policy_add_required_source_class(self, policy_id: str, source_class: str) -> None:
        self._require_owner()
        policy = self._get_source_policy(policy_id)
        _require(not policy.version_locked, "EXPECTED:SOURCE_POLICY_LOCKED")
        _validate_bounded_text(source_class, 1, MAX_SOURCE_CLASS_LEN, "source_class")
        _require(
            len(policy.required_source_classes) < MAX_REQUIRED_CLASSES_PER_POLICY,
            "EXPECTED:MAX_REQUIRED_CLASSES_REACHED",
        )
        for existing_class in policy.required_source_classes:
            _require(existing_class != source_class, "EXPECTED:DUPLICATE_REQUIRED_CLASS")

        policy.required_source_classes.append(source_class)

    @gl.public.view
    def policy_get_source_policy(self, policy_id: str) -> dict:
        return self._get_source_policy(policy_id).to_dict()

    @gl.public.view
    def policy_exists(self, policy_id: str) -> bool:
        return self.source_policies.get(policy_id) is not None

    # -- writes: Resolution --------------------------------------------------

    def _require_observation_window_passed(self, observation_period: str) -> None:
        import datetime

        period_date = datetime.date.fromisoformat(observation_period)
        window_end = period_date + datetime.timedelta(days=1)
        _require(datetime.datetime.now().date() >= window_end, "EXPECTED:OBSERVATION_WINDOW_NOT_ENDED")

    @gl.public.write
    def resolve_weather_event(self, event_id: str) -> None:
        event = self._get_event(event_id)
        _require(
            event.status in (EVENT_STATUS_PENDING, EVENT_STATUS_UNRESOLVED),
            "EXPECTED:EVENT_ALREADY_RESOLVED",
        )
        self._require_observation_window_passed(event.observation_period)
        policy = self._get_source_policy(event.source_policy_id)
        _require(len(policy.sources) > 0, "EXPECTED:SOURCE_POLICY_HAS_NO_SOURCES")
        location_profile = self._get_location_profile(event.location)

        # Lifecycle: PENDING -> RESOLVING -> RESOLVED | UNRESOLVED. Within
        # one synchronous contract call RESOLVING is not separately
        # observable by an external caller (a revert rolls the whole
        # transaction back), but it is the real intermediate state while
        # the leader/validator retrieval below runs, so it is modeled
        # explicitly rather than skipped.
        event.status = EVENT_STATUS_RESOLVING

        observation = Observation(event_id, event.location)
        expected_period = event.observation_period

        # Plain dict, not the storage-backed LocationProfile itself --
        # same cloudpickle-safety reason as `url`/`fetch_mode` below.
        location_ctx = {
            "canonical_name": location_profile.canonical_name,
            "country": location_profile.country,
            "aliases": [a for a in location_profile.aliases],
            "has_coordinates": location_profile.has_coordinates,
            "lat": _signed_degrees(location_profile.lat_hundredths, location_profile.lat_is_south),
            "lon": _signed_degrees(location_profile.lon_hundredths, location_profile.lon_is_west),
            "radius_km": int(location_profile.radius_km),
        }

        for source in policy.sources:
            evidence = SourceEvidence(source.source_id, source.url, source.fetch_mode)

            # Plain locals only, no `self` capture -- required for
            # gl.vm.run_nondet's cloudpickle serialization (verified
            # requirement, protocol_court.py sec on _fetch_evidence).
            url = source.url
            fetch_mode = source.fetch_mode

            def leader_fn():
                return _classify_and_extract(url, fetch_mode, location_ctx, expected_period)

            def validator_fn(leaders_result):
                if not isinstance(leaders_result, gl.vm.Return):
                    return False
                leader_data = leaders_result.calldata
                if not isinstance(leader_data, dict) or "status" not in leader_data:
                    return False
                my_data = _classify_and_extract(url, fetch_mode, location_ctx, expected_period)
                if my_data["status"] != leader_data["status"]:
                    return False
                if my_data["status"] != RETRIEVAL_AVAILABLE:
                    return True
                leader_text = leader_data.get("raw_text", "")
                my_text = my_data.get("raw_text", "")
                if leader_text == my_text:
                    return True
                # Semantic verification (GenLayer judgment): only reached
                # when leader and validator retrieved byte-different text
                # for the same URL. Never used for numeric extraction.
                judgment = gl.nondet.exec_prompt(
                    _fidelity_prompt(url, leader_text, my_text),
                    response_format="json",
                )
                return _judged_faithful(judgment)

            data = gl.vm.run_nondet(leader_fn, validator_fn)
            _require(isinstance(data, dict), "EXPECTED:MALFORMED_FETCH_RESULT")
            status = data.get("status")
            _require(status in _RETRIEVAL_STATUSES, "EXPECTED:INVALID_RETRIEVAL_STATUS")
            raw_text = data.get("raw_text", "")

            evidence.observation_timestamp = self._now()
            evidence.excerpt_fingerprint = format(_fnv1a(raw_text), "016x")
            evidence.location_match = data.get("location_match", "")
            evidence.location_detail = data.get("location_detail", "")

            if status == RETRIEVAL_AVAILABLE:
                raw_value = data.get("raw_value", "")
                normalized_mm100, rejection = _normalize_to_mm100(raw_value, source.reported_unit)
                evidence.reported_value_raw = raw_value
                evidence.reported_unit = source.reported_unit
                if rejection is None:
                    evidence.retrieval_status = RETRIEVAL_AVAILABLE
                    evidence.normalized_value_mm100 = u256(normalized_mm100)
                else:
                    evidence.retrieval_status = rejection
            else:
                evidence.retrieval_status = status

            observation.evidence.append(evidence)

            # Fail-fast source-failure policy: a single non-AVAILABLE
            # source can abort the whole resolution immediately when the
            # policy demands it, rather than silently proceeding on
            # whatever sources happened to work (architecture sec 8/11).
            is_timeout = evidence.retrieval_status == RETRIEVAL_TIMEOUT
            is_other_failure = evidence.retrieval_status in (
                RETRIEVAL_UNAVAILABLE,
                RETRIEVAL_FETCH_FAILED,
                RETRIEVAL_RENDER_FAILED,
            )
            behavior = policy.timeout_behavior if is_timeout else policy.unavailable_source_behavior
            if (is_timeout or is_other_failure) and behavior == SOURCE_BEHAVIOR_FAIL_POLICY:
                self._finalize_unresolved(event, observation, RESOLUTION_REASON_SOURCE_FAILURE_POLICY)
                return

        valid_evidence = [e for e in observation.evidence if e.retrieval_status == RETRIEVAL_AVAILABLE]

        if len(valid_evidence) < int(policy.min_source_count):
            self._finalize_unresolved(event, observation, RESOLUTION_REASON_INSUFFICIENT_SOURCES)
            return

        if len(policy.required_source_classes) > 0:
            valid_source_classes = {
                source.source_class
                for source in policy.sources
                if source.source_id in {e.source_id for e in valid_evidence}
            }
            for required_class in policy.required_source_classes:
                if required_class not in valid_source_classes:
                    self._finalize_unresolved(event, observation, RESOLUTION_REASON_MISSING_REQUIRED_CLASS)
                    return

        normalized_values = [int(e.normalized_value_mm100) for e in valid_evidence]
        spread = max(normalized_values) - min(normalized_values)
        if spread > int(policy.disagreement_tolerance_mm100):
            self._finalize_unresolved(event, observation, RESOLUTION_REASON_DISAGREEMENT)
            return

        observation.status = EVENT_STATUS_RESOLVED
        observation.value_mm100 = u256(_median_mm100(normalized_values))
        observation.unit = "mm"
        observation.source_count = u256(len(valid_evidence))
        observation.evidence_status = EVIDENCE_STATUS_SUFFICIENT
        observation.resolution_reason = RESOLUTION_REASON_OK
        observation.resolved_at = self._now()

        self.observations[event.event_id] = observation
        event.status = EVENT_STATUS_RESOLVED

    def _finalize_unresolved(self, event: WeatherEvent, observation: Observation, reason: str) -> None:
        valid_count = len([e for e in observation.evidence if e.retrieval_status == RETRIEVAL_AVAILABLE])
        observation.status = EVENT_STATUS_UNRESOLVED
        observation.value_mm100 = u256(0)
        observation.source_count = u256(valid_count)
        observation.evidence_status = EVIDENCE_STATUS_INSUFFICIENT
        observation.resolution_reason = reason
        observation.resolved_at = self._now()

        self.observations[event.event_id] = observation
        event.status = EVENT_STATUS_UNRESOLVED

    @gl.public.view
    def observation_get_observation(self, event_id: str) -> dict:
        observation = self.observations.get(event_id)
        _require(observation is not None, "EXPECTED:OBSERVATION_NOT_FOUND")
        return observation.to_dict()

    @gl.public.view
    def observation_get_resolution_status(self, event_id: str) -> str:
        return self._get_event(event_id).status

    # =========================================================================
    # WeatherCover layer -- the first consumer application, not infrastructure.
    #
    # Everything below reads the Observation Registry (self.events /
    # self.observations) and never writes to it: WeatherResolve's
    # resolution logic is not touched by any cover_* method. WeatherCover
    # holds no retrieval, normalization, or resolution logic of its own --
    # it only evaluates a deterministic BELOW/ABOVE condition against
    # whatever WeatherResolve already decided, and tracks a simulated
    # balance. No real funds, escrow, or tokens exist anywhere here.
    # =========================================================================

    def _get_cover_policy(self, policy_id: str) -> CoverPolicy:
        policy = self.cover_policies.get(policy_id)
        _require(policy is not None, "EXPECTED:COVER_POLICY_NOT_FOUND")
        return policy

    @staticmethod
    def _cover_policy_dedupe_key(owner_key: str, weather_event_id: str, operator: str, threshold_mm100: u256) -> str:
        # Prevents the same owner from accidentally creating two
        # functionally-identical policies (same event, same condition) --
        # analogous in spirit to the event_id dedup in the WeatherResolve
        # layer, but scoped per-owner since two different owners taking
        # out the "same" policy is legitimate (each has their own
        # simulated balance), unlike WeatherResolve's single shared
        # Observation Registry.
        key = f"{owner_key}|{weather_event_id}|{operator}|{int(threshold_mm100)}"
        return format(_fnv1a(key), "016x")

    @gl.public.write
    def cover_create_policy(
        self,
        weather_event_id: str,
        operator: str,
        threshold_mm100: u256,
        simulated_payout: u256,
    ) -> str:
        event = self._get_event(weather_event_id)  # read-only lookup
        _require(operator in _COVER_OPERATORS, "EXPECTED:INVALID_OPERATOR")
        _require(
            0 < int(threshold_mm100) <= MAX_THRESHOLD_MM100,
            "EXPECTED:INVALID_THRESHOLD",
        )
        _require(int(simulated_payout) >= MIN_SIMULATED_PAYOUT, "EXPECTED:INVALID_SIMULATED_PAYOUT")
        _require(int(self.next_cover_policy_seq) < MAX_COVER_POLICIES, "EXPECTED:MAX_COVER_POLICIES_REACHED")

        owner = gl.message.sender_address
        owner_key = _address_key(owner)
        dedupe_key = self._cover_policy_dedupe_key(owner_key, weather_event_id, operator, threshold_mm100)
        _require(self.cover_policy_dedupe.get(dedupe_key) is None, "EXPECTED:DUPLICATE_POLICY")

        owner_policy_ids = self.cover_policy_ids_by_owner.get(owner_key)
        existing_count = 0 if owner_policy_ids is None else len(owner_policy_ids)
        _require(existing_count < MAX_COVER_POLICIES_PER_OWNER, "EXPECTED:MAX_COVER_POLICIES_PER_OWNER_REACHED")

        self.next_cover_policy_seq = u256(int(self.next_cover_policy_seq) + 1)
        policy_id = f"cover-{int(self.next_cover_policy_seq)}"

        policy = CoverPolicy(
            policy_id=policy_id,
            owner=owner,
            weather_event_id=weather_event_id,
            location_id=event.location,
            metric=event.metric,
            observation_date=event.observation_period,
            operator=operator,
            threshold_mm100=threshold_mm100,
            simulated_payout=simulated_payout,
            created_at=self._now(),
        )
        self.cover_policies[policy_id] = policy
        self.cover_policy_dedupe[dedupe_key] = policy_id

        if owner_policy_ids is None:
            self.cover_policy_ids_by_owner[owner_key] = []
        self.cover_policy_ids_by_owner[owner_key].append(policy_id)

        return policy_id

    @gl.public.write
    def cover_evaluate_policy(self, policy_id: str) -> None:
        policy = self._get_cover_policy(policy_id)
        _require(
            policy.status in (COVER_STATUS_PENDING, COVER_STATUS_UNRESOLVED),
            "EXPECTED:POLICY_ALREADY_EVALUATED",
        )

        observation = self.observations.get(policy.weather_event_id)
        policy.evaluated_at = self._now()

        if observation is None or observation.status != EVENT_STATUS_RESOLVED:
            # First-class outcome, not an error: the underlying event has
            # not resolved (or resolved UNRESOLVED) yet. The policy stays
            # explicitly UNRESOLVED -- no credit, no denial -- and can be
            # evaluated again later once/if WeatherResolve resolves it.
            policy.status = COVER_STATUS_UNRESOLVED
            return

        value = int(observation.value_mm100)
        threshold = int(policy.threshold_mm100)
        if policy.operator == COVER_OPERATOR_BELOW:
            triggered = value < threshold
        else:  # COVER_OPERATOR_ABOVE
            triggered = value > threshold

        if triggered:
            policy.status = COVER_STATUS_TRIGGERED
            policy.credited_amount = policy.simulated_payout
            owner_key = _address_key(policy.owner)
            current = self.simulated_balances.get(owner_key)
            current_amount = u256(0) if current is None else current
            self.simulated_balances[owner_key] = u256(int(current_amount) + int(policy.simulated_payout))
        else:
            policy.status = COVER_STATUS_NOT_TRIGGERED

    @gl.public.view
    def cover_get_policy(self, policy_id: str) -> dict:
        return self._get_cover_policy(policy_id).to_dict()

    @gl.public.view
    def cover_get_policy_detail(self, policy_id: str) -> dict:
        # History/detail view for a future frontend (scope item 5): policy
        # fields plus its linked Observation Registry entry, so evidence
        # status, resolution reason, and the resolved value are all
        # visible alongside the policy's own evaluation/payout result
        # without a second round-trip.
        policy = self._get_cover_policy(policy_id)
        detail = policy.to_dict()
        observation = self.observations.get(policy.weather_event_id)
        detail["linked_observation"] = None if observation is None else observation.to_dict()
        return detail

    @gl.public.view
    def cover_list_policy_ids_by_owner(self, owner: Address) -> list:
        owner_key = _address_key(_coerce_address(owner))
        ids = self.cover_policy_ids_by_owner.get(owner_key)
        return [] if ids is None else [i for i in ids]

    @gl.public.view
    def cover_get_simulated_balance(self, owner: Address) -> u256:
        owner_key = _address_key(_coerce_address(owner))
        balance = self.simulated_balances.get(owner_key)
        return u256(0) if balance is None else balance

    @gl.public.view
    def cover_policy_exists(self, policy_id: str) -> bool:
        return self.cover_policies.get(policy_id) is not None
