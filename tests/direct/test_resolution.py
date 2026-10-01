"""
Resolution model: Evidence Package -> Normalization -> Validate -> Resolve,
wired to REAL GenLayer web retrieval (gl.nondet.web.get / .render, wrapped
in gl.vm.run_nondet leader/validator consensus), with a Location
Resolution Profile replacing exact internal-token location matching.

Direct-mode tests exercise the actual gl.nondet.web call path via the
gltest VM's mock_web cheatcode (verified against
protocolcourt/tests/direct/test_evidence.py's usage) -- these are the
real retrieval functions running against a faked HTTP layer, not a
contract-side "mock://" shortcut.
"""

import json

CONTRACT_PATH = "contracts/weather_resolve_cover.py"

LOCATION = "LAGOS_NG"  # internal location_id -- never expected in evidence text
CANONICAL_NAME = "Lagos"
COUNTRY = "Nigeria"
ALIAS = "Lagos, Nigeria"
METRIC = "RAIN_24H"
PERIOD = "2026-08-30"  # in the past relative to the sandbox clock

# Real-world-style page text: mentions the canonical name AND country
# together (how most real weather sources disambiguate "Lagos"), never
# the internal location_id -- exactly the gap the Location Resolution
# Profile exists to close.
PAGE_PREFIX = f"Observation for {CANONICAL_NAME}, {COUNTRY} on {PERIOD}: "


def _deploy(direct_deploy, direct_owner, has_coordinates=False, radius_km=0):
    contract = direct_deploy(CONTRACT_PATH, direct_owner)
    # Lat/lon for Lagos, Nigeria (~6.52N, 3.38E), stored as
    # magnitude+direction (see LocationProfile). Only used by the
    # coordinate-matching tests.
    contract.location_register_profile(
        LOCATION, CANONICAL_NAME, COUNTRY, has_coordinates, 652, False, 338, False, radius_km
    )
    return contract, direct_owner


def _register_policy(
    contract,
    policy_id="STRICT_V1",
    min_source_count=2,
    tolerance_mm100=200,
    unavailable_behavior="SKIP",
    timeout_behavior="SKIP",
):
    contract.policy_register_source_policy(
        policy_id, min_source_count, tolerance_mm100, unavailable_behavior, timeout_behavior
    )
    return policy_id


def _add_source(contract, policy_id, source_id, url, source_class="authoritative_met", reported_unit="mm"):
    contract.policy_add_source(policy_id, source_id, url, "get", source_class, reported_unit)


def _create_event(contract, policy_id):
    return contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)


def _mock_available(direct_vm, url, value_text, status=200):
    direct_vm.mock_web(url, {"method": "GET", "status": status, "body": PAGE_PREFIX + value_text})


# ---------------------------------------------------------------------
# Successful resolution
# ---------------------------------------------------------------------


def test_successful_resolution(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, tolerance_mm100=200)
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-rain-b"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    _mock_available(direct_vm, url_b, "8.40mm")

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    assert observation["requested_location_id"] == LOCATION
    assert observation["resolution_reason"] == "OK"
    assert observation["evidence_status"] == "SUFFICIENT"
    assert observation["source_count"] == 2
    # median of 860 and 840 hundredths-mm -> 850 (8.50mm)
    assert observation["value_mm100"] == 850
    assert observation["unit"] == "mm"
    assert len(observation["evidence"]) == 2
    for row in observation["evidence"]:
        assert row["fetch_mode"] == "get"
        assert row["retrieval_status"] == "AVAILABLE"
        assert row["location_match"] == "CANONICAL_NAME"
    assert contract.observation_get_resolution_status(event_id) == "RESOLVED"

    event = contract.event_get_weather_event(event_id)
    assert event["status"] == "RESOLVED"


def test_successful_resolution_normalizes_mixed_units(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, tolerance_mm100=50)
    url_a = "https://example.org/lagos-rain-mm"
    url_b = "https://example.org/lagos-rain-in"
    _add_source(contract, policy_id, "src_a", url_a, reported_unit="mm")
    _add_source(contract, policy_id, "src_b", url_b, reported_unit="in")
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60")
    _mock_available(direct_vm, url_b, "0.34")  # 0.34in == 8.636mm

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    evidence_by_id = {e["source_id"]: e for e in observation["evidence"]}
    assert evidence_by_id["src_b"]["normalized_value_mm100"] == 863  # 34 * 254 // 10


# ---------------------------------------------------------------------
# Location Resolution Profile matching
# ---------------------------------------------------------------------


def test_lagos_api_response_accepted(direct_deploy, direct_owner, direct_vm):
    # A realistic structured API response shape (styled after the kind
    # of JSON a public weather API returns), naming the city and country
    # the way a real provider would -- never the internal location_id.
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/api/weather"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    body = (
        f'{{"resolvedAddress": "{CANONICAL_NAME}, {COUNTRY}", '
        f'"date": "{PERIOD}", "precip": 8.60, "precipUnit": "mm"}}'
    )
    direct_vm.mock_web(url_a, {"method": "GET", "status": 200, "body": body})

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    assert observation["value_mm100"] == 860
    row = observation["evidence"][0]
    assert row["location_match"] == "CANONICAL_NAME"


def test_alias_matching_accepted(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    contract.location_add_alias(LOCATION, ALIAS)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/lagos-rain-alias"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    # Real-world phrasing that uses the alias, not the bare canonical
    # name -- e.g. an API that reports "Lagos, Nigeria" as one string.
    direct_vm.mock_web(
        url_a, {"method": "GET", "status": 200, "body": f"Rain report for {ALIAS} on {PERIOD}: 8.60mm"}
    )

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    row = observation["evidence"][0]
    assert row["location_match"] == "ALIAS"
    assert ALIAS in row["location_detail"]


def test_coordinate_proximity_accepted_with_realistic_api_metadata(direct_deploy, direct_owner, direct_vm):
    # Shaped after a real historical-weather API's JSON response: query
    # metadata (coordinates, elevation, generation time, UTC offset) is
    # echoed BEFORE the actual requested reading, and the location is
    # only present as coordinates -- no city/country string at all. This
    # is exactly the shape that broke a naive "first number in text"
    # extractor; masking the date/coordinates and reading the LAST
    # remaining number is what makes this resolve correctly.
    contract, owner = _deploy(direct_deploy, direct_owner, has_coordinates=True, radius_km=50)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/archive-api"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    body = (
        '{"latitude":6.5,"longitude":3.375,"generationtime_ms":0.123,'
        '"utc_offset_seconds":3600,"elevation":38.0,'
        f'"daily":{{"time":["{PERIOD}"],"precipitation_sum":[8.6]}}}}'
    )
    direct_vm.mock_web(url_a, {"method": "GET", "status": 200, "body": body})

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    assert observation["value_mm100"] == 860
    row = observation["evidence"][0]
    assert row["location_match"] == "COORDINATES"


def test_coordinate_proximity_accepted(direct_deploy, direct_owner, direct_vm):
    # has_coordinates=True, radius_km=50: a source that never names Lagos
    # or Nigeria at all, but reports coordinates within range, still
    # counts as evidence about the right location.
    contract, owner = _deploy(direct_deploy, direct_owner, has_coordinates=True, radius_km=50)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/coords-only"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    body = f'{{"latitude": 6.52, "longitude": 3.38}} observed on {PERIOD}: 8.60mm'
    direct_vm.mock_web(url_a, {"method": "GET", "status": 200, "body": body})

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    row = observation["evidence"][0]
    assert row["location_match"] == "COORDINATES"


def test_wrong_city_rejected(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/wrong-city"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    # Nairobi, still Africa, no relation to Lagos or Nigeria at all.
    direct_vm.mock_web(
        url_b, {"method": "GET", "status": 200, "body": f"Observation for Nairobi on {PERIOD}: 5.0mm"}
    )

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    bad_row = next(e for e in observation["evidence"] if e["source_id"] == "src_b")
    assert bad_row["retrieval_status"] == "WRONG_LOCATION"
    assert bad_row["location_match"] == ""


def test_wrong_country_rejected(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/wrong-country"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    # There is a Lagos, Portugal too -- a bare canonical-name match is
    # not accepted on its own (see _match_location_by_name); the
    # configured country ("Nigeria") must also be present, and here it
    # explicitly is not.
    direct_vm.mock_web(
        url_b, {"method": "GET", "status": 200, "body": f"Observation for Lagos, Portugal on {PERIOD}: 5.0mm"}
    )

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    bad_row = next(e for e in observation["evidence"] if e["source_id"] == "src_b")
    assert bad_row["retrieval_status"] == "WRONG_LOCATION"
    assert bad_row["location_match"] == ""


def test_missing_location_evidence_rejected(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/no-location-at-all"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    # No canonical name, no alias, no country, no coordinates -- nothing
    # in this profile's Location Resolution Profile is present at all.
    direct_vm.mock_web(
        url_b, {"method": "GET", "status": 200, "body": f"Rainfall reading on {PERIOD}: 5.0mm"}
    )

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    bad_row = next(e for e in observation["evidence"] if e["source_id"] == "src_b")
    assert bad_row["retrieval_status"] == "WRONG_LOCATION"
    assert bad_row["location_match"] == ""
    assert "no match found" in bad_row["location_detail"]


def test_wrong_date_rejected(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-wrong-day"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    direct_vm.mock_web(
        url_b,
        {
            "method": "GET",
            "status": 200,
            "body": f"Observation for {CANONICAL_NAME}, {COUNTRY} on 2026-08-29: 5.0mm",
        },
    )

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    bad_row = next(e for e in observation["evidence"] if e["source_id"] == "src_b")
    assert bad_row["retrieval_status"] == "WRONG_DATE"
    # Location is checked before date, so a matched location is still
    # recorded even though the overall row is rejected for the date.
    assert bad_row["location_match"] == "CANONICAL_NAME"


# ---------------------------------------------------------------------
# Insufficient sources -> UNRESOLVED
# ---------------------------------------------------------------------


def test_insufficient_sources_unresolved(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-rain-down"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    direct_vm.mock_web(url_b, {"method": "GET", "status": 503, "body": ""})  # UNAVAILABLE

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "UNRESOLVED"
    assert observation["resolution_reason"] == "INSUFFICIENT_SOURCES"
    assert observation["evidence_status"] == "INSUFFICIENT"
    assert observation["source_count"] == 1
    assert observation["value_mm100"] == 0
    # the failed source's row is still present for the Evidence Explorer
    assert len(observation["evidence"]) == 2
    failed_row = next(e for e in observation["evidence"] if e["source_id"] == "src_b")
    assert failed_row["retrieval_status"] == "UNAVAILABLE"

    event = contract.event_get_weather_event(event_id)
    assert event["status"] == "UNRESOLVED"


# ---------------------------------------------------------------------
# Conflicting values -> UNRESOLVED
# ---------------------------------------------------------------------


def test_conflicting_values_unresolved(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, tolerance_mm100=200)
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-rain-conflict"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    _mock_available(direct_vm, url_b, "20.00mm")

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "UNRESOLVED"
    assert observation["resolution_reason"] == "DISAGREEMENT"
    assert observation["source_count"] == 2  # both were individually valid
    assert observation["value_mm100"] == 0


# ---------------------------------------------------------------------
# Source timeout/failure handling
# ---------------------------------------------------------------------


def test_timeout_with_skip_behavior_still_resolves(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, timeout_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-rain-b"
    url_c = "https://example.org/lagos-rain-slow"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    _add_source(contract, policy_id, "src_c", url_c)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    _mock_available(direct_vm, url_b, "8.40mm")
    # status 408 is this contract's own convention for a source timing out
    direct_vm.mock_web(url_c, {"method": "GET", "status": 408, "body": ""})

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    assert observation["source_count"] == 2
    timeout_row = next(e for e in observation["evidence"] if e["source_id"] == "src_c")
    assert timeout_row["retrieval_status"] == "TIMEOUT"


def test_timeout_with_fail_policy_behavior_aborts_resolution(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1, timeout_behavior="FAIL_POLICY")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-rain-slow"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    direct_vm.mock_web(url_b, {"method": "GET", "status": 408, "body": ""})

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "UNRESOLVED"
    assert observation["resolution_reason"] == "SOURCE_FAILURE_POLICY"


def test_fetch_failed_with_fail_policy_behavior_aborts_resolution(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1, unavailable_behavior="FAIL_POLICY")
    url_a = "https://example.org/lagos-rain-unmocked"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    # No mock registered for url_a at all: the real gl.nondet.web.get call
    # path raises (MockNotFoundError under gltest direct mode; a real
    # network failure on StudioNet), caught and classified FETCH_FAILED.
    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "UNRESOLVED"
    assert observation["resolution_reason"] == "SOURCE_FAILURE_POLICY"
    failed_row = next(e for e in observation["evidence"] if e["source_id"] == "src_a")
    assert failed_row["retrieval_status"] == "FETCH_FAILED"


def test_render_failed_with_fail_policy_behavior_aborts_resolution(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1, unavailable_behavior="FAIL_POLICY")
    url_a = "https://example.org/lagos-rain-dynamic"
    contract.policy_add_source(policy_id, "src_a", url_a, "render", "authoritative_met", "mm")
    event_id = _create_event(contract, policy_id)

    # No mock registered: gl.nondet.web.render's call path raises the same
    # way, classified RENDER_FAILED (not FETCH_FAILED) because fetch_mode
    # is "render". Render remains optional -- this policy has exactly one
    # source and it happens to use render, not because render is required.
    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "UNRESOLVED"
    failed_row = next(e for e in observation["evidence"] if e["source_id"] == "src_a")
    assert failed_row["retrieval_status"] == "RENDER_FAILED"


# ---------------------------------------------------------------------
# Invalid evidence rejection
# ---------------------------------------------------------------------


def test_invalid_number_rejected_and_excluded(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=2, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-a"
    url_b = "https://example.org/lagos-rain-nan"
    _add_source(contract, policy_id, "src_a", url_a)
    _add_source(contract, policy_id, "src_b", url_b)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    # body mentions location+period but has no numeric token at all
    direct_vm.mock_web(
        url_b, {"method": "GET", "status": 200, "body": PAGE_PREFIX + "no reading available"}
    )

    contract.resolve_weather_event(event_id)

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "UNRESOLVED"
    assert observation["resolution_reason"] == "INSUFFICIENT_SOURCES"
    bad_row = next(e for e in observation["evidence"] if e["source_id"] == "src_b")
    assert bad_row["retrieval_status"] == "INVALID_RESPONSE"
    assert bad_row["normalized_value_mm100"] == 0
    assert bad_row["location_match"] == "CANONICAL_NAME"  # location was fine; the value wasn't


def test_unsupported_unit_never_reaches_retrieval_layer(direct_deploy, direct_owner):
    # Unit is a source-config-time declaration, not something scraped
    # from the page, so an invalid unit is rejected at policy_add_source,
    # before any retrieval is attempted.
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    try:
        contract.policy_add_source(
            policy_id, "src_a", "https://example.org/lagos-rain", "get", "authoritative_met", "furlongs"
        )
        assert False, "expected rejection of an unsupported reported_unit"
    except Exception as exc:
        assert "INVALID_REPORTED_UNIT" in str(exc)


# ---------------------------------------------------------------------
# GenLayer judgment: retrieval fidelity (semantic verification)
# ---------------------------------------------------------------------


def test_validator_agrees_on_identical_retrieval(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/lagos-rain-a"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    contract.resolve_weather_event(event_id)

    # Direct mode auto-runs leader_fn only; validator_fn is captured and
    # must be invoked manually to exercise its agreement logic (verified
    # pattern, protocolcourt/tests/direct/test_evidence.py). Same mock is
    # still in effect, so the validator retrieves byte-identical text and
    # agrees without needing the LLM fidelity judgment.
    assert direct_vm.run_validator() is True


def test_validator_disagrees_on_conflicting_status(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1, unavailable_behavior="SKIP")
    url_a = "https://example.org/lagos-rain-flaky"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    contract.resolve_weather_event(event_id)

    # Swap the mock before re-running the validator, simulating the
    # validator seeing the source go down after the leader already saw it
    # succeed -- statuses disagree, so validator_fn must reject. The
    # first-registered mock wins ties on URL match, so the old one is
    # cleared before registering the replacement.
    direct_vm.clear_mocks()
    direct_vm.mock_web(url_a, {"method": "GET", "status": 503, "body": ""})
    assert direct_vm.run_validator() is False


# ---------------------------------------------------------------------
# Numeric consensus binding (adversarial): text agreement/fidelity alone
# must NOT be sufficient to approve a resolution -- the validator must
# independently recompute raw_value/normalized_value and reject if its
# own recomputation does not match what the leader claims, even when the
# leader's claimed raw_text is genuine. See contracts/weather_resolve_
# cover.py resolve_weather_event's validator_fn for the fix this proves.
# ---------------------------------------------------------------------


def test_malicious_leader_raw_value_rejected_by_validator(direct_deploy, direct_owner, direct_vm):
    # Test 1: leader returns genuine, matching raw_text (so the text-level
    # check alone would approve it) but a fabricated raw_value that does
    # not match what that text actually extracts to. Expected: FAIL
    # consensus -- validator_fn must return False.
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/lagos-rain-a"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    contract.resolve_weather_event(event_id)

    # The real leader result for this mock is {"status": "AVAILABLE",
    # "raw_text": "...8.60mm", "raw_value": "8.60", ...}. Override it with
    # a malicious claim that reuses the SAME genuine raw_text (so a
    # text-only check would wrongly approve) but a fabricated raw_value
    # ("999") that does not match what that text actually extracts to.
    malicious_leader_result = {
        "status": "AVAILABLE",
        "raw_text": PAGE_PREFIX + "8.60mm",
        "raw_value": "999",
    }
    assert direct_vm.run_validator(leader_result=malicious_leader_result) is False


def test_leader_and_validator_extract_different_values_rejected(direct_deploy, direct_owner, direct_vm):
    # Test 2: leader and validator retrieve the SAME source but it
    # genuinely reports a different value at each retrieval (simulating a
    # source that changed between the leader's and the validator's
    # independent fetches). Expected: validator_fn rejects (FAIL
    # consensus). Direct mode auto-runs only leader_fn and does not gate
    # resolve_weather_event's own RESOLVED/UNRESOLVED outcome on
    # validator_fn's result (consensus enforcement is real-network
    # behavior, not reproducible in this harness -- same documented
    # limitation as test_validator_disagrees_on_conflicting_status
    # above); on real GenLayer consensus, a validator rejection like this
    # is exactly what prevents a resolution from finalizing, which is why
    # asserting the rejection itself is the correct, honest thing to test
    # here.
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/lagos-rain-drifting"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    contract.resolve_weather_event(event_id)

    # Validator independently retrieves a genuinely different value, with
    # different raw_text -- so the text-fidelity LLM judgment path is
    # reached first. Mock it to judge the two excerpts "faithful" (a
    # plausible real verdict: same source, just an updated reading),
    # specifically to prove the NEW raw_value check still rejects even
    # when text-fidelity alone would have approved.
    direct_vm.clear_mocks()
    _mock_available(direct_vm, url_a, "20.00mm")
    direct_vm.mock_llm(
        r"checking whether two independently retrieved excerpts",
        json.dumps({"faithful": True, "reason": "Same source, reading updated between fetches."}),
    )
    assert direct_vm.run_validator() is False


def test_matching_leader_and_validator_values_accepted(direct_deploy, direct_owner, direct_vm):
    # Test 3 (control case): normal valid evidence, leader's claimed
    # result genuinely matches the validator's own independent
    # recomputation (raw_text, raw_value, and therefore normalized
    # value). Expected: consensus succeeds and the event resolves
    # RESOLVED, exactly as the existing resolution tests already prove --
    # this test additionally exercises the new raw_value/normalized-value
    # comparison explicitly via an overridden-but-matching leader_result,
    # to prove the new check does not reject honest agreement.
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract, min_source_count=1)
    url_a = "https://example.org/lagos-rain-honest"
    _add_source(contract, policy_id, "src_a", url_a)
    event_id = _create_event(contract, policy_id)

    _mock_available(direct_vm, url_a, "8.60mm")
    contract.resolve_weather_event(event_id)

    honest_leader_result = {
        "status": "AVAILABLE",
        "raw_text": PAGE_PREFIX + "8.60mm",
        "raw_value": "8.60",
    }
    assert direct_vm.run_validator(leader_result=honest_leader_result) is True

    observation = contract.observation_get_observation(event_id)
    assert observation["status"] == "RESOLVED"
    assert observation["value_mm100"] == 860
