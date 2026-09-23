from inventory_engine import (
    classify_inventory,
    compute_demand,
    days_of_cover,
    excess_inventory_estimate,
    forecast_inventory,
    projected_stockout_date,
    reorder_point,
    safety_stock,
    suggested_reorder_quantity,
    what_if_scenario,
)


def test_compute_demand_weighted_favors_recent():
    flat = [10] * 30
    stats = compute_demand(flat)
    assert stats["avg_30d"] == 10
    assert stats["weighted_avg"] == 10  # uniform data -> weighting shouldn't matter

    ramping = [2] * 14 + [10] * 7  # older days low, most recent days high
    stats2 = compute_demand(ramping)
    assert stats2["weighted_avg"] > stats2["avg_30d"]  # weighting should tilt toward recent (higher) demand


def test_days_of_cover_no_demand_returns_none():
    assert days_of_cover(100, 0) is None
    assert days_of_cover(100, -1) is None


def test_days_of_cover_basic():
    assert days_of_cover(100, 10) == 10.0


def test_safety_stock_and_reorder_point():
    assert safety_stock(10, 5) == 50
    assert reorder_point(10, 12, 5) == 170  # 10*12 + 10*5


def test_suggested_reorder_quantity_respects_moq_and_multiple():
    qty = suggested_reorder_quantity(avg_daily_demand=10, current_inventory=50, target_days_of_stock=45, moq=100, reorder_multiple=25)
    # target = 450, need 400 more, but MOQ=100 (already above), round up to nearest 25
    assert qty % 25 == 0
    assert qty >= 100

    assert suggested_reorder_quantity(avg_daily_demand=0, current_inventory=50) == 0


def test_classify_inventory_states():
    assert classify_inventory(None, 5, 100, 50) == "NO_DATA"
    assert classify_inventory(3, 5, 10, 50) == "STOCKOUT_RISK"  # under reorder point, <=5 days
    assert classify_inventory(8, 5, 10, 50) == "LOW_COVER"       # under reorder point, >5 days
    assert classify_inventory(120, 5, 600, 50) == "OVERSTOCK"
    assert classify_inventory(200, 0.3, 60, 50) == "SLOW_MOVING"
    assert classify_inventory(30, 5, 200, 50) == "HEALTHY"


def test_projected_stockout_date_none_without_demand():
    assert projected_stockout_date(100, 0) is None


def test_forecast_inventory_never_goes_negative_and_applies_inbound():
    rows = forecast_inventory(current_inventory=10, avg_daily_demand=5, days_ahead=5,
                               inbound=[{"day_offset": 2, "quantity": 100}])
    assert rows[0]["projected_inventory"] == 10  # day 0 is the starting point, unchanged
    for row in rows:
        assert row["projected_inventory"] >= 0
    # inbound on day 2 should show up in that day's balance
    assert rows[2]["inbound_qty"] == 100
    assert rows[2]["projected_inventory"] > rows[1]["projected_inventory"]


def test_what_if_scenario_is_clearly_a_simulation_not_a_fact():
    result = what_if_scenario(current_inventory=100, avg_daily_demand=10, reorder_quantity=500, lead_time_days=12)
    assert result["reorder_quantity"] == 500
    assert result["post_replenishment_inventory"] > 0
    assert "stockout_risk_before_arrival" in result


def test_excess_inventory_only_flags_true_overstock():
    assert excess_inventory_estimate(current_inventory=100, avg_daily_demand=10, days_cover=10) is None
    result = excess_inventory_estimate(current_inventory=2000, avg_daily_demand=5, days_cover=400)
    assert result is not None
    assert result["excess_units_estimate"] > 0
