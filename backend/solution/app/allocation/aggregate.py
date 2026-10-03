"""Group valued holdings by asset class. These values are not stored."""


def aggregate_allocation(holdings: list[dict]) -> list[dict]:
    values: dict[str, float] = {}
    for holding in holdings:
        asset_class = holding["assetClass"]
        values[asset_class] = values.get(asset_class, 0.0) + holding["marketValue"]

    total = sum(values.values())
    return [
        {
            "assetClass": asset_class,
            "value": value,
            "percent": 0.0 if total == 0 else value / total,
        }
        for asset_class, value in values.items()
    ]
