"""Delhivery B2C Express provider.

Covers the full forward-shipment lifecycle for a business shipping individual
orders to end customers (as opposed to B2B/freight, which is a different API
family entirely and the wrong fit here):

  serviceability -> rate -> create_shipment (manifest -> waybill) -> track
  -> cancel, plus schedule_pickup to have a rider collect manifested parcels.

Endpoints (cross-referenced from Delhivery's public Express API docs — see the
package README for sources and a **verification note**: the manifest/track/
cancel/pickup payload shapes below have not been exercised against a live
Delhivery account by this codebase; validate them against your own staging
token before relying on them in production, and adjust field names here if
Delhivery's response differs).

  GET  /c/api/pin-codes/json/                serviceability
  GET  /api/kinko/v1/invoice/charges/.json   rate
  POST /api/cmu/create.json                  create_shipment (manifest)
  GET  /api/v1/packages/json/                track
  POST /api/p/edit                           cancel
  POST /fm/request/new/                      schedule_pickup

Auth: ``Authorization: Token <token>`` on every call.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from .exceptions import ShipmentCreationError, ShippingError
from .models import Address, PickupResult, Serviceability, Shipment, ShipmentItem
from .provider import ShippingProvider

# Delhivery's own status vocabulary -> our courier-agnostic vocabulary.
_STATUS_MAP = {
    "manifested": "manifested",
    "not picked": "manifested",
    "pending": "manifested",
    "in transit": "in_transit",
    "dispatched": "in_transit",
    "pickup scheduled": "manifested",
    "out for delivery": "out_for_delivery",
    "delivered": "delivered",
    "rto": "failed",
    "undelivered": "failed",
    "cancelled": "cancelled",
    "returned": "cancelled",
}


def _normalize_status(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    return _STATUS_MAP.get(raw.strip().lower(), "unknown")


def _http(
    method: str, url: str, headers: dict[str, str], body: Optional[bytes] = None, timeout: float = 15.0
):
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail)
        except Exception:
            pass
        raise ShippingError(f"Delhivery {method} {url} -> HTTP {exc.code}: {detail}") from exc
    except Exception as exc:  # network, timeout, bad JSON
        raise ShippingError(f"Delhivery {method} {url} failed: {exc}") from exc


class DelhiveryProvider(ShippingProvider):
    def __init__(
        self,
        token: str,
        *,
        base: str,
        origin_pin: str,
        pickup_location: str,
        seller_name: str,
        seller_address: str,
        seller_gst_tin: str = "",
        hsn_code: str = "",
        tracking_url_template: str = "https://www.delhivery.com/track-v2/package/{waybill}",
    ) -> None:
        self.token = token
        self.base = base.rstrip("/")
        self.origin_pin = origin_pin
        # The exact, case-sensitive warehouse name registered in Delhivery's
        # client (CL) panel. There is no public API to register it — it must
        # be set up once on delhivery.com by the business, same as the token.
        self.pickup_location = pickup_location
        self.seller_name = seller_name
        self.seller_address = seller_address
        self.seller_gst_tin = seller_gst_tin
        self.hsn_code = hsn_code
        self.tracking_url_template = tracking_url_template

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.token}", "Accept": "application/json"}

    # ── serviceability + rate (unchanged from the quote-only MVP) ──────────
    def serviceability(self, pincode: str) -> Serviceability:
        q = urllib.parse.urlencode({"token": self.token, "filter_codes": pincode})
        _, data = _http("GET", f"{self.base}/c/api/pin-codes/json/?{q}", self._headers)
        codes = (data or {}).get("delivery_codes") or []
        if not codes:
            return Serviceability(serviceable=False, pincode=pincode)
        pc = (codes[0] or {}).get("postal_code") or {}
        pre = str(pc.get("pre_paid", "N")).upper() == "Y"
        cod = str(pc.get("cod", "N")).upper() == "Y"
        covered = str(pc.get("covered", "Y")).upper() != "N"
        return Serviceability(
            serviceable=covered and (pre or cod),
            pincode=pincode,
            city=pc.get("city") or pc.get("district"),
            state=pc.get("state_code") or pc.get("inc"),
            cod=cod,
            prepaid=pre,
        )

    def rate(self, dest_pin: str, *, weight_g: int, payment: str) -> tuple[float, Optional[int]]:
        pt = "COD" if payment.lower() == "cod" else "Pre-paid"
        q = urllib.parse.urlencode({
            "md": "E", "ss": "Delivered",
            "o_pin": self.origin_pin, "d_pin": dest_pin,
            "cgm": weight_g, "pt": pt,
        })
        _, data = _http(
            "GET", f"{self.base}/api/kinko/v1/invoice/charges/.json?{q}", self._headers
        )
        row = data[0] if isinstance(data, list) and data else (data or {})
        amount = row.get("total_amount") or row.get("gross_amount") or 0
        try:
            base = round(float(amount), 2)
        except (TypeError, ValueError):
            base = 0.0
        return base, None

    # ── manifest / track / cancel / pickup ──────────────────────────────────
    def create_shipment(
        self,
        *,
        order_id: str,
        origin: Address,
        destination: Address,
        items: list[ShipmentItem],
        payment_mode: str,
        amount: float,
        weight_g: int,
    ) -> Shipment:
        products_desc = ", ".join(f"{i.quantity}x {i.description}" for i in items) or "Food order"
        shipment = {
            "name": destination.name,
            "add": destination.address,
            "pin": destination.pincode,
            "city": destination.city or "",
            "state": destination.state or "",
            "country": destination.country,
            "phone": destination.phone,
            "order": order_id,
            "payment_mode": "COD" if payment_mode.lower() == "cod" else "Prepaid",
            "products_desc": products_desc,
            "hsn_code": self.hsn_code,
            "cod_amount": str(amount) if payment_mode.lower() == "cod" else "",
            "total_amount": str(amount),
            "seller_add": self.seller_address,
            "seller_name": self.seller_name,
            "seller_gst_tin": self.seller_gst_tin,
            "quantity": str(sum(i.quantity for i in items) or 1),
            "waybill": "",  # let Delhivery assign one
            "weight": str(weight_g),
            "shipping_mode": "Surface",
            "address_type": "home",
        }
        payload = {
            "shipments": [shipment],
            "pickup_location": {
                "name": self.pickup_location,
                "add": origin.address,
                "city": origin.city or "",
                "pin_code": origin.pincode,
                "country": origin.country,
                "phone": origin.phone,
            },
        }
        body = urllib.parse.urlencode({
            "format": "json", "data": json.dumps(payload)
        }).encode("utf-8")
        headers = {**self._headers, "Content-Type": "application/x-www-form-urlencoded"}
        _, data = _http("POST", f"{self.base}/api/cmu/create.json", headers, body)

        packages = (data or {}).get("packages") or []
        pkg = packages[0] if packages else {}
        ok = bool((data or {}).get("success")) or str(pkg.get("status", "")).lower() == "success"
        waybill = pkg.get("waybill")
        if not ok or not waybill:
            raise ShipmentCreationError(
                pkg.get("remarks") or (data or {}).get("rmk") or "Delhivery rejected the shipment"
            )
        return Shipment(
            waybill=waybill,
            order_id=order_id,
            status="manifested",
            raw_status="Manifested",
            tracking_url=self.tracking_url_template.format(waybill=waybill),
        )

    def track(self, waybill: str) -> Shipment:
        q = urllib.parse.urlencode({"waybill": waybill, "token": self.token})
        _, data = _http("GET", f"{self.base}/api/v1/packages/json/?{q}", self._headers)
        rows = (data or {}).get("ShipmentData") or []
        raw_status = None
        if rows:
            shipment = (rows[0] or {}).get("Shipment") or {}
            status_obj = shipment.get("Status") or {}
            raw_status = status_obj.get("Status") or shipment.get("Status")
        return Shipment(
            waybill=waybill,
            order_id="",
            status=_normalize_status(raw_status if isinstance(raw_status, str) else None),
            raw_status=raw_status if isinstance(raw_status, str) else None,
            tracking_url=self.tracking_url_template.format(waybill=waybill),
        )

    def cancel(self, waybill: str) -> bool:
        body = json.dumps({"waybill": waybill, "cancellation": "true"}).encode("utf-8")
        headers = {**self._headers, "Content-Type": "application/json"}
        _, data = _http("POST", f"{self.base}/api/p/edit", headers, body)
        return bool((data or {}).get("status", True))

    def schedule_pickup(self, *, date: str, time: str, package_count: int) -> PickupResult:
        body = urllib.parse.urlencode({
            "pickup_time": time,
            "pickup_date": date,
            "pickup_location": self.pickup_location,
            "expected_package_count": package_count,
        }).encode("utf-8")
        headers = {**self._headers, "Content-Type": "application/x-www-form-urlencoded"}
        try:
            _, data = _http("POST", f"{self.base}/fm/request/new/", headers, body)
        except ShippingError as exc:
            return PickupResult(ok=False, remarks=str(exc))
        pickup_id = (data or {}).get("pickup_id") or (data or {}).get("prepaid_pickup_id")
        return PickupResult(ok=True, pickup_id=str(pickup_id) if pickup_id else None)
