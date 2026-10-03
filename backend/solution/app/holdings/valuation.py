"""Request-time holding math. These values are not stored."""


def value_holding(
    *,
    ticker: str,
    name: str,
    asset_class: str,
    quantity: float,
    cost_basis_per_share: float,
    price: float,
    previous_close_price: float,
    portfolio_market_value: float,
) -> dict:
    market_value = quantity * price
    if portfolio_market_value == 0:
        weight_percent = 0.0
    else:
        weight_percent = market_value / portfolio_market_value
    if previous_close_price == 0:
        day_change_percent = 0.0
    else:
        day_change_percent = (price - previous_close_price) / previous_close_price

    return {
        "ticker": ticker,
        "name": name,
        "assetClass": asset_class,
        "quantity": quantity,
        "costBasisPerShare": cost_basis_per_share,
        "price": price,
        "previousClosePrice": previous_close_price,
        "marketValue": market_value,
        "weightPercent": weight_percent,
        "unrealizedGainLoss": (price - cost_basis_per_share) * quantity,
        "dayChangeAmount": (price - previous_close_price) * quantity,
        "dayChangePercent": day_change_percent,
    }
