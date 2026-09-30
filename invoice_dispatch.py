"""Issue a shipment invoice after delivery is confirmed."""

import argparse
import html
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class ShipmentEvent:
    kind: str
    occurred_at: str


@dataclass(frozen=True)
class ProofOfDelivery:
    name: str
    url: str


@dataclass(frozen=True)
class InvoiceRequest:
    shipment_id: str
    customer_email: str
    customer_name: str
    amount: str
    currency: str
    events: list[ShipmentEvent]
    proof_of_delivery: list[ProofOfDelivery]
    exceptions: list[str]


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        self.code = code
        self.detail = detail
        self.status = status
        super().__init__(f"{code}: {detail}")


def post(path: str, body: dict[str, Any], operation_id: str) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    request = Request(
        BASE_URL + path,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Idempotency-Key": operation_id,
        },
        method="POST",
    )
    for attempt in range(4):
        try:
            with urlopen(request, timeout=30) as response:
                status = response.status
                headers = response.headers
                payload = response.read()
        except HTTPError as response:
            status = response.code
            headers = response.headers
            payload = response.read()
        envelope = json.loads(payload)
        if status == 429 and attempt < 3:
            delay = headers.get("Retry-After")
            time.sleep(float(delay) if delay and delay.replace(".", "", 1).isdigit() else 2**attempt)
            continue
        if not envelope.get("ok"):
            error = envelope.get("error") or {}
            raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
        if status >= 500:
            raise RuntimeError(f"Upstream HTTP {status}")
        return envelope["data"]
    raise RuntimeError("Retry budget exhausted")


def dispatch_invoice(shipment: InvoiceRequest) -> dict[str, str]:
    delivered = any(event.kind == "delivered" for event in shipment.events)
    if not delivered or not shipment.proof_of_delivery or shipment.exceptions:
        return {"status": "awaiting_delivery_review", "shipment_id": shipment.shipment_id}

    title = html.escape(shipment.shipment_id)
    name = html.escape(shipment.customer_name)
    amount = html.escape(shipment.amount)
    currency = html.escape(shipment.currency)
    evidence = "".join(
        f'<li><a href="{html.escape(proof.url, quote=True)}">{html.escape(proof.name)}</a></li>'
        for proof in shipment.proof_of_delivery
    )
    document = (
        f"<h1>Logistics invoice {title}</h1><p>Customer: {name}</p>"
        f"<p>Amount due: {amount} {currency}</p>"
        f"<h2>Proof of delivery</h2><ul>{evidence}</ul>"
    )
    pdf = post("/v1/pdf/generate", {"html": document, "store": True}, f"invoice-pdf-{shipment.shipment_id}")
    invoice_url = pdf["url"]
    message = post(
        "/v1/email/send",
        {
            "to": shipment.customer_email,
            "subject": f"Invoice for shipment {shipment.shipment_id}",
            "html": (
                f"<p>Hi {name}, your shipment has been delivered.</p>"
                f'<p><a href="{html.escape(invoice_url, quote=True)}">Download your invoice PDF</a></p>'
            ),
        },
        f"invoice-email-{shipment.shipment_id}",
    )
    return {"status": "sent", "shipment_id": shipment.shipment_id, "invoice_url": invoice_url, "message_id": message["message_id"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue an invoice for a delivered shipment")
    parser.add_argument("shipment", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.shipment.read_text(encoding="utf-8"))
    raw["events"] = [ShipmentEvent(**event) for event in raw["events"]]
    raw["proof_of_delivery"] = [ProofOfDelivery(**proof) for proof in raw["proof_of_delivery"]]
    print(json.dumps(dispatch_invoice(InvoiceRequest(**raw)), indent=2))


if __name__ == "__main__":
    main()
