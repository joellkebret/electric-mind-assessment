"""Fetch portfolio metadata from the mock CRM and map it to the API schema."""

from urllib.parse import quote

import httpx


class PortfolioApiError(Exception):
    """Structured failure for a portfolio request."""

    def __init__(self, status_code: int, error: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.message = message
        super().__init__(message)


def load_portfolio(portfolio_id: str, client: httpx.Client) -> dict:
    payload = _fetch_payload(portfolio_id, client)
    return map_portfolio(portfolio_id, payload)


def map_portfolio(portfolio_id: str, payload: dict) -> dict:
    accounts = _accounts(payload)
    if accounts is None:
        raise PortfolioApiError(
            502,
            "crm_payload_invalid",
            "The CRM response did not include an account list.",
        )

    account = next(
        (
            item
            for item in accounts
            if isinstance(item, dict) and item.get("acct_ref") == portfolio_id
        ),
        None,
    )
    if account is None:
        raise PortfolioApiError(404, "not_found", "No portfolio exists for this id.")

    record = payload.get("client_record")
    client_id = record.get("client_id") if isinstance(record, dict) else None
    meta = payload.get("meta")
    retrieved_at = meta.get("retrieved_at") if isinstance(meta, dict) else None
    current = account.get("curr_val")
    change = account.get("chg_1d")
    if not isinstance(current, dict):
        current = {}
    if not isinstance(change, dict):
        change = {}

    return {
        "portfolioId": portfolio_id,
        "clientId": _text(client_id),
        "label": _text(account.get("acct_nickname")),
        "currency": _text(current.get("ccy")),
        "totalMarketValue": _number(current.get("amt")),
        "dayChangeAmount": _number(change.get("amt")),
        "dayChangePercent": _number(change.get("pct")),
        "totalReturnSinceInception": _number(account.get("since_inception_pct")),
        "asOf": _text(retrieved_at),
    }


def _fetch_payload(portfolio_id: str, client: httpx.Client) -> dict:
    path = f"/crm/portfolios/{quote(portfolio_id, safe='')}"
    try:
        response = client.get(path)
    except httpx.TimeoutException as exc:
        raise PortfolioApiError(
            504,
            "crm_timeout",
            "The CRM did not respond before the timeout.",
        ) from exc
    except httpx.HTTPError as exc:
        raise PortfolioApiError(
            502,
            "crm_unavailable",
            "The CRM could not be reached.",
        ) from exc

    if response.status_code == 404:
        raise PortfolioApiError(404, "not_found", "No portfolio exists for this id.")
    if response.status_code != 200:
        raise PortfolioApiError(502, "crm_unavailable", "The CRM returned an error.")

    try:
        payload = response.json()
    except ValueError as exc:
        raise PortfolioApiError(
            502,
            "crm_payload_invalid",
            "The CRM response was not valid JSON.",
        ) from exc
    if not isinstance(payload, dict):
        raise PortfolioApiError(
            502,
            "crm_payload_invalid",
            "The CRM response was not a JSON object.",
        )
    return payload


def _accounts(payload: dict) -> list | None:
    record = payload.get("client_record")
    if not isinstance(record, dict):
        return None
    accounts = record.get("accounts")
    if not isinstance(accounts, list):
        relationships = record.get("relationships")
        if isinstance(relationships, dict):
            accounts = relationships.get("accounts")
    if not isinstance(accounts, list):
        return None
    return accounts


def _text(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
