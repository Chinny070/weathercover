"""
WeatherCover: the first consumer application on top of the WeatherResolve
Observation Registry. These tests never touch retrieval/resolution logic
directly -- they drive resolve_weather_event exactly as test_resolution.py
does, then exercise cover_* on top, proving WeatherCover only reads the
registry and never mutates it.
"""

CONTRACT_PATH = "contracts/weather_resolve_cover.py"

LOCATION = "LAGOS_NG"
CANONICAL_NAME = "Lagos"
COUNTRY = "Nigeria"
METRIC = "RAIN_24H"
PERIOD = "2026-08-30"

PAGE_PREFIX = f"Observation for {CANONICAL_NAME}, {COUNTRY} on {PERIOD}: "


def _deploy(direct_deploy, direct_owner):
    contract = direct_deploy(CONTRACT_PATH, direct_owner)
    contract.location_register_profile(LOCATION, CANONICAL_NAME, COUNTRY, False, 0, False, 0, False, 0)
    return contract, direct_owner


def _resolve_event_with_value(contract, direct_vm, value_text, min_source_count=1, policy_id="P1"):
    contract.policy_register_source_policy(policy_id, min_source_count, 200, "SKIP", "SKIP")
    url = f"https://example.org/{policy_id}"
    contract.policy_add_source(policy_id, "src_a", url, "get", "authoritative_met", "mm")
    event_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)
    direct_vm.mock_web(url, {"method": "GET", "status": 200, "body": PAGE_PREFIX + value_text})
    contract.resolve_weather_event(event_id)
    return event_id


def _leave_event_unresolved(contract, direct_vm, policy_id="P2"):
    contract.policy_register_source_policy(policy_id, 1, 200, "SKIP", "SKIP")
    url = f"https://example.org/{policy_id}"
    contract.policy_add_source(policy_id, "src_a", url, "get", "authoritative_met", "mm")
    event_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id)
    direct_vm.mock_web(url, {"method": "GET", "status": 503, "body": ""})
    contract.resolve_weather_event(event_id)
    return event_id


# ---------------------------------------------------------------------
# Policy creation
# ---------------------------------------------------------------------


def test_create_policy(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")

    policy_id = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)

    policy = contract.cover_get_policy(policy_id)
    assert policy["weather_event_id"] == event_id
    assert policy["location_id"] == LOCATION
    assert policy["metric"] == METRIC
    assert policy["observation_date"] == PERIOD
    assert policy["operator"] == "BELOW"
    assert policy["threshold_mm100"] == 1500
    assert policy["simulated_payout"] == 1000
    assert policy["credited_amount"] == 0
    assert policy["status"] == "PENDING"
    assert policy["evaluated_at"] == ""


def test_create_policy_rejects_invalid_threshold(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")

    try:
        contract.cover_create_policy(event_id, "BELOW", 0, 1000)
        assert False, "expected rejection of a zero threshold"
    except Exception as exc:
        assert "INVALID_THRESHOLD" in str(exc)

    try:
        contract.cover_create_policy(event_id, "BELOW", 999999, 1000)
        assert False, "expected rejection of an absurdly large threshold"
    except Exception as exc:
        assert "INVALID_THRESHOLD" in str(exc)


def test_create_policy_rejects_invalid_operator(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")

    try:
        contract.cover_create_policy(event_id, "EQUALS", 1500, 1000)
        assert False, "expected rejection of an unsupported operator"
    except Exception as exc:
        assert "INVALID_OPERATOR" in str(exc)


def test_duplicate_policy_prevention(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")

    contract.cover_create_policy(event_id, "BELOW", 1500, 1000)
    try:
        contract.cover_create_policy(event_id, "BELOW", 1500, 1000)
        assert False, "expected rejection of a duplicate policy (same owner/event/operator/threshold)"
    except Exception as exc:
        assert "DUPLICATE_POLICY" in str(exc)

    # A different threshold is not a duplicate -- creation must succeed.
    second_policy_id = contract.cover_create_policy(event_id, "BELOW", 2000, 1000)
    assert second_policy_id != ""


# ---------------------------------------------------------------------
# Deterministic evaluation
# ---------------------------------------------------------------------


def test_evaluate_triggered_condition(direct_deploy, direct_owner, direct_vm):
    # Observation: RAIN_24H = 12.30mm. Policy: BELOW 15mm -> TRIGGERED.
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")
    policy_id = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)

    contract.cover_evaluate_policy(policy_id)

    policy = contract.cover_get_policy(policy_id)
    assert policy["status"] == "TRIGGERED"
    assert policy["credited_amount"] == 1000
    assert policy["evaluated_at"] != ""
    assert contract.cover_get_simulated_balance(owner) == 1000


def test_evaluate_not_triggered_condition(direct_deploy, direct_owner, direct_vm):
    # Observation: RAIN_24H = 12.30mm. Policy: BELOW 10mm -> NOT_TRIGGERED.
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")
    policy_id = contract.cover_create_policy(event_id, "BELOW", 1000, 1000)

    contract.cover_evaluate_policy(policy_id)

    policy = contract.cover_get_policy(policy_id)
    assert policy["status"] == "NOT_TRIGGERED"
    assert policy["credited_amount"] == 0
    assert contract.cover_get_simulated_balance(owner) == 0


def test_evaluate_above_operator(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")
    policy_id = contract.cover_create_policy(event_id, "ABOVE", 1000, 500)

    contract.cover_evaluate_policy(policy_id)

    assert contract.cover_get_policy(policy_id)["status"] == "TRIGGERED"
    assert contract.cover_get_simulated_balance(owner) == 500


def test_cannot_reevaluate_already_decided_policy(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")
    policy_id = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)
    contract.cover_evaluate_policy(policy_id)

    try:
        contract.cover_evaluate_policy(policy_id)
        assert False, "expected rejection of re-evaluating an already-TRIGGERED policy"
    except Exception as exc:
        assert "POLICY_ALREADY_EVALUATED" in str(exc)

    # Balance must not have been double-credited by the rejected retry.
    assert contract.cover_get_simulated_balance(owner) == 1000


# ---------------------------------------------------------------------
# UNRESOLVED observation handling
# ---------------------------------------------------------------------


def test_unresolved_observation_handling(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _leave_event_unresolved(contract, direct_vm)
    policy_id = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)

    contract.cover_evaluate_policy(policy_id)

    policy = contract.cover_get_policy(policy_id)
    assert policy["status"] == "UNRESOLVED"
    assert policy["credited_amount"] == 0
    assert contract.cover_get_simulated_balance(owner) == 0


def test_unresolved_policy_can_be_retried_after_event_resolves(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    policy_id_src = "RETRY_V1"
    contract.policy_register_source_policy(policy_id_src, 1, 200, "SKIP", "SKIP")
    url = "https://example.org/retry"
    contract.policy_add_source(policy_id_src, "src_a", url, "get", "authoritative_met", "mm")
    event_id = contract.event_create_weather_event(LOCATION, METRIC, PERIOD, policy_id_src)

    direct_vm.mock_web(url, {"method": "GET", "status": 503, "body": ""})
    contract.resolve_weather_event(event_id)

    cover_id = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)
    contract.cover_evaluate_policy(cover_id)
    assert contract.cover_get_policy(cover_id)["status"] == "UNRESOLVED"

    # Source recovers; the underlying event resolves on retry. The
    # first-registered mock wins ties on URL match, so it must be
    # cleared before registering the replacement (see test_resolution.py).
    direct_vm.clear_mocks()
    direct_vm.mock_web(url, {"method": "GET", "status": 200, "body": PAGE_PREFIX + "12.30mm"})
    contract.resolve_weather_event(event_id)

    contract.cover_evaluate_policy(cover_id)
    policy = contract.cover_get_policy(cover_id)
    assert policy["status"] == "TRIGGERED"
    assert contract.cover_get_simulated_balance(owner) == 1000


# ---------------------------------------------------------------------
# History / detail views
# ---------------------------------------------------------------------


def test_policy_detail_includes_linked_observation(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")
    policy_id = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)
    contract.cover_evaluate_policy(policy_id)

    detail = contract.cover_get_policy_detail(policy_id)
    assert detail["status"] == "TRIGGERED"
    assert detail["linked_observation"]["status"] == "RESOLVED"
    assert detail["linked_observation"]["evidence_status"] == "SUFFICIENT"
    assert detail["linked_observation"]["resolution_reason"] == "OK"
    assert detail["linked_observation"]["value_mm100"] == 1230


def test_list_policy_ids_by_owner(direct_deploy, direct_owner, direct_vm):
    contract, owner = _deploy(direct_deploy, direct_owner)
    event_id = _resolve_event_with_value(contract, direct_vm, "12.30mm")

    policy_a = contract.cover_create_policy(event_id, "BELOW", 1500, 1000)
    policy_b = contract.cover_create_policy(event_id, "ABOVE", 500, 200)

    ids = contract.cover_list_policy_ids_by_owner(owner)
    assert set(ids) == {policy_a, policy_b}
