"""Holding math, independent of HTTP and the database."""

from app.holdings.valuation import value_holding


def _holding(**overrides) -> dict:
    values = {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "asset_class": "Equity",
        "quantity": 120,
        "cost_basis_per_share": 200,
        "price": 227.5,
        "previous_close_price": 225,
        "portfolio_market_value": 48930,
    }
    values.update(overrides)
    return value_holding(**values)


def test_calculates_value_weight_and_gain_loss():
    holding = _holding()

    assert holding["marketValue"] == 120 * 227.5
    assert holding["weightPercent"] == (120 * 227.5) / 48930
    assert holding["unrealizedGainLoss"] == (227.5 - 200) * 120
    assert holding["dayChangeAmount"] == (227.5 - 225) * 120
    assert holding["dayChangePercent"] == (227.5 - 225) / 225


def test_zero_quantity_zeros_value_weight_and_gain_loss():
    holding = _holding(
        ticker="ZERO",
        quantity=0,
        cost_basis_per_share=10,
        price=12,
        previous_close_price=10,
        portfolio_market_value=48930,
    )

    assert holding["marketValue"] == 0
    assert holding["weightPercent"] == 0
    assert holding["unrealizedGainLoss"] == 0
    assert holding["dayChangeAmount"] == 0
    assert holding["dayChangePercent"] == (12 - 10) / 10


def test_zero_previous_close_returns_zero_day_change_percent():
    holding = _holding(
        ticker="NEW",
        quantity=10,
        cost_basis_per_share=40,
        price=50,
        previous_close_price=0,
        portfolio_market_value=500,
    )

    assert holding["dayChangePercent"] == 0
    assert holding["dayChangeAmount"] == 500
    assert holding["marketValue"] == 500
    assert holding["weightPercent"] == 1


def test_zero_portfolio_value_does_not_divide_by_zero():
    holding = _holding(quantity=0, price=12, portfolio_market_value=0)

    assert holding["weightPercent"] == 0


def test_weights_are_not_rescaled_to_sum_to_one():
    first = _holding(quantity=1, price=1, portfolio_market_value=3)
    second = _holding(quantity=1, price=2, portfolio_market_value=3)

    assert first["weightPercent"] == 1 / 3
    assert second["weightPercent"] == 2 / 3
