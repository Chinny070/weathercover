"""
Weather Event Registry + Source Policy Registry (Step 2).

Direct-mode tests only, mirroring protocolcourt's gltest harness usage.
No retrieval/resolution logic is exercised here -- that's Step 3.
"""

CONTRACT_PATH = "contracts/weather_resolve_cover.py"

LOCATION = "LAGOS_NG"
METRIC = "RAIN_24H"
PERIOD = "2026-08-30"


def _deploy(direct_deploy, direct_owner):
    # direct_owner == the VM's default sender ("default_sender"); writes
    # issued without changing direct_vm.sender come from this address, so
    # deploying with it as the owner arg is what makes owner-only calls
    # succeed by default in these tests.
    contract = direct_deploy(CONTRACT_PATH, direct_owner)
    # A location must be a registered profile before any event can
    # reference it (Location Resolution Profile registry) -- LAGOS_NG is
    # seed data for this MVP deployment, not a hardcoded contract rule.
    contract.location_register_profile("LAGOS_NG", "Lagos", "Nigeria", False, 0, False, 0, False, 0)
    return contract, direct_owner


def _register_policy(contract, policy_id="STRICT_V1", min_source_count=2):
    contract.policy_register_source_policy(
        policy_id,
        min_source_count,
        500,  # disagreement_tolerance_mm100 = 5.00mm
        "FAIL_POLICY",
        "SKIP",
    )
    return policy_id


# ---------------------------------------------------------------------
# Weather Event Registry
# ---------------------------------------------------------------------


def test_create_weather_event_valid(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    event_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)

    assert isinstance(event_id, str) and len(event_id) > 0
    event = contract.event_get_weather_event(event_id)
    assert event["location"] == LOCATION
    assert event["metric"] == METRIC
    assert event["observation_period"] == PERIOD
    assert event["source_policy_id"] == policy_id
    assert event["status"] == "PENDING"
    assert event["consumer_count"] == 1


def test_create_weather_event_deterministic_id(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    predicted_id = contract.event_compute_id(LOCATION, METRIC, PERIOD, policy_id)
    actual_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)

    assert predicted_id == actual_id


def test_duplicate_event_reuses_id_and_increments_consumer_count(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    first_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)
    second_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)

    assert first_id == second_id
    event = contract.event_get_weather_event(first_id)
    assert event["consumer_count"] == 2


def test_different_source_policy_produces_different_event(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_a = _register_policy(contract, "STRICT_V1")
    policy_b = _register_policy(contract, "STANDARD_V1")

    id_a = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_a)
    id_b = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_b)

    assert id_a != id_b


def test_create_weather_event_rejects_unsupported_location(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    try:
        contract.event_create_weather_event("NEW_YORK_US", METRIC, PERIOD, policy_id)
        assert False, "expected rejection of unsupported location"
    except Exception as exc:
        assert "UNSUPPORTED_LOCATION" in str(exc)


def test_create_weather_event_rejects_unsupported_metric(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    try:
        contract.event_create_weather_event(LOCATION, "TEMP_MAX", PERIOD, policy_id)
        assert False, "expected rejection of unsupported metric"
    except Exception as exc:
        assert "UNSUPPORTED_METRIC" in str(exc)


def test_create_weather_event_rejects_malformed_observation_period(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    try:
        contract.event_create_weather_event(LOCATION, METRIC, "08-30-2026", policy_id)
        assert False, "expected rejection of malformed observation_period"
    except Exception as exc:
        assert "MALFORMED_OBSERVATION_PERIOD" in str(exc)


def test_create_weather_event_rejects_unknown_source_policy(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)

    try:
        contract.event_create_weather_event(LOCATION, METRIC, PERIOD, "NO_SUCH_POLICY")
        assert False, "expected rejection of unknown source policy"
    except Exception as exc:
        assert "SOURCE_POLICY_NOT_FOUND" in str(exc)


def test_event_exists(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)

    predicted_id = contract.event_compute_id(LOCATION, METRIC, PERIOD, policy_id)
    assert contract.event_exists(predicted_id) is False

    contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)
    assert contract.event_exists(predicted_id) is True


# ---------------------------------------------------------------------
# Source Policy Registry
# ---------------------------------------------------------------------


def test_register_source_policy(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)

    contract.policy_register_source_policy("STRICT_V1", 3, 500, "FAIL_POLICY", "FAIL_POLICY")

    policy = contract.policy_get_source_policy("STRICT_V1")
    assert policy["policy_id"] == "STRICT_V1"
    assert policy["min_source_count"] == 3
    assert policy["disagreement_tolerance_mm100"] == 500
    assert policy["unavailable_source_behavior"] == "FAIL_POLICY"
    assert policy["timeout_behavior"] == "FAIL_POLICY"
    assert policy["version_locked"] is False
    assert policy["sources"] == []
    assert policy["required_source_classes"] == []


def test_register_duplicate_policy_id_rejected(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    _register_policy(contract, "STRICT_V1")

    try:
        contract.policy_register_source_policy("STRICT_V1", 2, 300, "SKIP", "SKIP")
        assert False, "expected rejection of duplicate policy_id"
    except Exception as exc:
        assert "SOURCE_POLICY_ALREADY_EXISTS" in str(exc)


def test_register_source_policy_rejects_invalid_min_source_count(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)

    try:
        contract.policy_register_source_policy("BAD_V1", 0, 500, "SKIP", "SKIP")
        assert False, "expected rejection of zero min_source_count"
    except Exception as exc:
        assert "INVALID_MIN_SOURCE_COUNT" in str(exc)


def test_unauthorized_policy_creation_rejected(direct_deploy, direct_owner, direct_alice, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)

    direct_vm.sender = direct_alice
    try:
        contract.policy_register_source_policy("STRICT_V1", 2, 500, "SKIP", "SKIP")
        assert False, "expected rejection of non-owner policy registration"
    except Exception as exc:
        assert "NOT_OWNER" in str(exc)
    finally:
        direct_vm.sender = owner


def test_any_caller_can_register_a_location(direct_deploy, direct_owner, direct_alice, direct_vm):
    # Product decision: location registration is intentionally open to any
    # caller (unlike source policies, which stay owner-gated since they
    # govern which evidence sources are trusted).
    contract, owner = _deploy(direct_deploy, direct_owner)

    direct_vm.sender = direct_alice
    try:
        contract.location_register_profile("ACCRA_GH", "Accra", "Ghana", False, 0, False, 0, False, 0)
    finally:
        direct_vm.sender = owner

    profile = contract.location_get_profile("ACCRA_GH")
    assert profile["canonical_name"] == "Accra"
    assert profile["country"] == "Ghana"


def test_cannot_overwrite_an_existing_location(direct_deploy, direct_owner, direct_alice, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)  # registers LAGOS_NG as "Lagos"/"Nigeria"

    direct_vm.sender = direct_alice
    try:
        contract.location_register_profile("LAGOS_NG", "Hijacked", "Nowhere", False, 0, False, 0, False, 0)
        assert False, "expected rejection of re-registering an existing location_id"
    except Exception as exc:
        assert "LOCATION_PROFILE_ALREADY_EXISTS" in str(exc)
    finally:
        direct_vm.sender = owner


def test_policy_add_source_and_required_class(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    contract.policy_register_source_policy("STRICT_V1", 2, 500, "FAIL_POLICY", "SKIP")

    contract.policy_add_source(
        "STRICT_V1", "met_ng_lagos", "https://example.org/lagos-rain", "get", "authoritative_met", "mm"
    )
    contract.policy_add_required_source_class("STRICT_V1", "authoritative_met")

    policy = contract.policy_get_source_policy("STRICT_V1")
    assert len(policy["sources"]) == 1
    assert policy["sources"][0]["source_id"] == "met_ng_lagos"
    assert policy["sources"][0]["source_class"] == "authoritative_met"
    assert policy["required_source_classes"] == ["authoritative_met"]


def test_policy_locks_after_first_event_reference(direct_deploy, direct_owner):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id = _register_policy(contract)
    contract.policy_add_source(policy_id, "src_a", "https://example.org/a", "get", "authoritative_met", "mm")

    contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)

    try:
        contract.policy_add_source(policy_id, "src_b", "https://example.org/b", "get", "aggregator", "mm")
        assert False, "expected rejection of adding a source to a locked policy"
    except Exception as exc:
        assert "SOURCE_POLICY_LOCKED" in str(exc)

    policy = contract.policy_get_source_policy(policy_id)
    assert policy["version_locked"] is True
