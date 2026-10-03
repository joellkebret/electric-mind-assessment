"""Allocation math, independent of HTTP and the database."""

from app.allocation.aggregate import aggregate_allocation


def test_groups_market_value_by_asset_class():
    rows = aggregate_allocation(
        [
            {"assetClass": "Equity", "marketValue": 27300},
            {"assetClass": "Fixed Income", "marketValue": 21630},
            {"assetClass": "Equity", "marketValue": 0},
        ]
    )

    equity, bonds = rows
    assert equity == {
        "assetClass": "Equity",
        "value": 27300,
        "percent": 27300 / 48930,
    }
    assert bonds == {
        "assetClass": "Fixed Income",
        "value": 21630,
        "percent": 21630 / 48930,
    }
    assert equity["percent"] + bonds["percent"] == 1


def test_single_asset_class_is_the_whole_portfolio():
    assert aggregate_allocation([{"assetClass": "Equity", "marketValue": 2275}]) == [
        {"assetClass": "Equity", "value": 2275, "percent": 1.0}
    ]


def test_empty_holdings_return_an_empty_array():
    assert aggregate_allocation([]) == []


def test_zero_quantity_adds_nothing_to_its_class():
    rows = aggregate_allocation(
        [
            {"assetClass": "Equity", "marketValue": 500},
            {"assetClass": "Cash", "marketValue": 0},
        ]
    )

    assert rows == [
        {"assetClass": "Equity", "value": 500, "percent": 1.0},
        {"assetClass": "Cash", "value": 0, "percent": 0.0},
    ]


def test_zero_portfolio_value_does_not_divide_by_zero():
    assert aggregate_allocation(
        [
            {"assetClass": "Equity", "marketValue": 0},
            {"assetClass": "Cash", "marketValue": 0},
        ]
    ) == [
        {"assetClass": "Equity", "value": 0, "percent": 0},
        {"assetClass": "Cash", "value": 0, "percent": 0},
    ]
