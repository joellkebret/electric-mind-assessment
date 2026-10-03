"""End-to-end checks for GET /portfolios/{id} through the FastAPI app."""

import socket
import time
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_http_client
from app.main import app

SCHEMA_FIELDS = {
    "portfolioId",
    "clientId",
    "label",
    "currency",
    "totalMarketValue",
    "dayChangeAmount",
    "dayChangePercent",
    "totalReturnSinceInception",
    "asOf",
}


def _account(
    ref: str,
    nickname: str | None = "Name",
    amt: float | None = 1,
    ccy: str = "CAD",
    change: float = 0,
    pct: float = 0,
    inception: float = 0,
) -> dict:
    body: dict = {
        "acct_ref": ref,
        "curr_val": {"amt": amt, "ccy": ccy},
        "chg_1d": {"amt": change, "pct": pct},
        "since_inception_pct": inception,
    }
    if nickname is not None:
        body["acct_nickname"] = nickname
    return body


def _payload(
    accounts: list,
    client_id: str = "abc123",
    retrieved_at: str = "2026-10-03T12:00:00Z",
    nested: bool = False,
) -> dict:
    record: dict = {"client_id": client_id, "full_name": "Jane Doe"}
    if nested:
        record["relationships"] = {"accounts": accounts}
    else:
        record["accounts"] = accounts
    return {
        "client_record": record,
        "meta": {"retrieved_at": retrieved_at, "source": "legacy-crm-v2"},
    }


@pytest.fixture
def api() -> Callable[[str, httpx.BaseTransport], httpx.Response]:
    transport_box: dict[str, httpx.BaseTransport] = {}

    def override():
        with httpx.Client(transport=transport_box["transport"], base_url="http://crm.test") as crm:
            yield crm

    app.dependency_overrides[get_http_client] = override
    try:
        with TestClient(app) as client:

            def call(portfolio_id: str, transport: httpx.BaseTransport):
                transport_box["transport"] = transport
                return client.get(f"/portfolios/{portfolio_id}")

            yield call
    finally:
        app.dependency_overrides.clear()


def test_maps_the_requested_account_from_a_multi_account_client(api):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["query"] = request.url.query.decode()
        return httpx.Response(
            200,
            json=_payload(
                [
                    _account(
                        "P-9001",
                        "Taxable Brokerage",
                        amt=48930,
                        change=30,
                        pct=30 / 48900,
                        inception=0.187,
                    ),
                    _account(
                        "P-9002",
                        "Retirement Account",
                        amt=500,
                        change=500,
                        pct=0,
                        inception=0.25,
                    ),
                    _account("P-EMPTY", "Empty Account", amt=0, change=0, pct=0, inception=0),
                ]
            ),
        )

    response = api("P-9002", httpx.MockTransport(handler))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == SCHEMA_FIELDS
    assert body == {
        "portfolioId": "P-9002",
        "clientId": "abc123",
        "label": "Retirement Account",
        "currency": "CAD",
        "totalMarketValue": 500,
        "dayChangeAmount": 500,
        "dayChangePercent": 0,
        "totalReturnSinceInception": 0.25,
        "asOf": "2026-10-03T12:00:00Z",
    }
    assert "full_name" not in body
    assert "source" not in body
    assert seen["path"] == "/crm/portfolios/P-9002"
    assert "mode=" not in seen["query"]


def test_zero_values_stay_zero(api):
    response = api(
        "P-EMPTY",
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=_payload(
                    [_account("P-EMPTY", "Empty Account", amt=0, change=0, pct=0, inception=0)]
                ),
            )
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["totalMarketValue"] == 0
    assert body["dayChangeAmount"] == 0
    assert body["dayChangePercent"] == 0
    assert body["totalReturnSinceInception"] == 0


def test_nested_account_list_is_mapped(api):
    response = api(
        "P-SINGLE",
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=_payload(
                    [
                        _account(
                            "P-SINGLE",
                            "Single Asset Class",
                            amt=2275,
                            change=25,
                            pct=25 / 2250,
                            inception=0.1375,
                        )
                    ],
                    client_id="single-client",
                    nested=True,
                ),
            )
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["portfolioId"] == "P-SINGLE"
    assert body["clientId"] == "single-client"
    assert body["label"] == "Single Asset Class"
    assert body["currency"] == "CAD"
    assert body["totalMarketValue"] == 2275
    assert body["dayChangeAmount"] == 25
    assert body["totalReturnSinceInception"] == 0.1375


def test_missing_fields_are_null(api):
    account = _account("P-9001", nickname=None, amt=None, change=30, pct=0.0006, inception=0.187)
    payload = _payload([account])
    payload["meta"] = {}
    payload["client_record"].pop("client_id")

    response = api("P-9001", httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))

    assert response.status_code == 200
    body = response.json()
    assert body["portfolioId"] == "P-9001"
    assert body["label"] is None
    assert body["totalMarketValue"] is None
    assert body["clientId"] is None
    assert body["asOf"] is None
    assert body["currency"] == "CAD"
    assert body["dayChangeAmount"] == 30


def test_non_numeric_amounts_are_null(api):
    account = _account("P-9001")
    account["curr_val"]["amt"] = "nope"
    account["chg_1d"]["pct"] = True

    response = api(
        "P-9001",
        httpx.MockTransport(lambda request: httpx.Response(200, json=_payload([account]))),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["totalMarketValue"] is None
    assert body["dayChangePercent"] is None


def test_unknown_id_from_the_crm_is_404(api):
    response = api(
        "NOPE",
        httpx.MockTransport(
            lambda request: httpx.Response(
                404,
                json={"error": "unknown_account", "message": "No CRM account has this reference."},
            )
        ),
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "not_found",
        "message": "No portfolio exists for this id.",
    }


def test_success_payload_without_the_requested_account_is_404(api):
    response = api(
        "P-9002",
        httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=_payload([_account("P-9001", "Taxable Brokerage")]),
            )
        ),
    )

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_success_payload_without_an_account_list_is_502(api):
    response = api(
        "P-9001",
        httpx.MockTransport(
            lambda request: httpx.Response(200, json={"client_record": {"client_id": "abc123"}})
        ),
    )

    assert response.status_code == 502
    assert response.json()["error"] == "crm_payload_invalid"


def test_non_json_success_body_is_502(api):
    response = api(
        "P-9001",
        httpx.MockTransport(lambda request: httpx.Response(200, content=b"not-json")),
    )

    assert response.status_code == 502
    assert response.json()["error"] == "crm_payload_invalid"


def test_crm_outage_is_502(api):
    response = api(
        "P-9001",
        httpx.MockTransport(
            lambda request: httpx.Response(
                503,
                json={"error": "legacy_unavailable", "message": "Simulated CRM outage."},
            )
        ),
    )

    assert response.status_code == 502
    assert response.json() == {
        "error": "crm_unavailable",
        "message": "The CRM returned an error.",
    }


def test_crm_timeout_is_504(api):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    response = api("P-9001", httpx.MockTransport(handler))

    assert response.status_code == 504
    assert response.json() == {
        "error": "crm_timeout",
        "message": "The CRM did not respond before the timeout.",
    }


def test_hung_crm_is_cut_off_with_504():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def override():
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=httpx.Timeout(0.4)) as crm:
            yield crm

    app.dependency_overrides[get_http_client] = override
    try:
        with TestClient(app) as client:
            started = time.perf_counter()
            response = client.get("/portfolios/P-9001")
            elapsed = time.perf_counter() - started
    finally:
        app.dependency_overrides.clear()
        server.close()

    assert response.status_code == 504
    assert response.json()["error"] == "crm_timeout"
    assert elapsed < 2


def test_unreachable_crm_is_502(api):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    response = api("P-9001", httpx.MockTransport(handler))

    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "crm_unavailable"
    assert body["message"] == "The CRM could not be reached."
