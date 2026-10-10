"""Razorpay payment gateway client.

Implemented with `httpx` and `hmac` from the standard library so the project
needs no extra dependency. Two trust boundaries matter here:

* Order creation authenticates to Razorpay with the key id/secret over HTTP
  Basic auth. The amount is always supplied by the caller (which computes it
  server-side from the appointment), never by the browser.
* Capture and webhooks are trusted only after an HMAC-SHA256 signature check,
  which is what stops a caller from simply claiming "I paid".

When the gateway is not configured the client raises
`PaymentGatewayNotConfigured` so the router can degrade gracefully with a clear
message instead of crashing.
"""

import hashlib
import hmac
from typing import Any, Optional

import httpx

from app.config import settings

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


class PaymentGatewayError(Exception):
    """Raised when Razorpay rejects a request or is unreachable."""


class PaymentGatewayNotConfigured(PaymentGatewayError):
    """Raised when the key id/secret have not been provided."""


class RazorpayGateway:
    @property
    def is_configured(self) -> bool:
        return settings.is_razorpay_configured

    async def create_order(
        self,
        *,
        amount_paise: int,
        receipt: str,
        notes: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Create a Razorpay order and return its JSON payload.

        `amount_paise` is the amount in the smallest currency unit (paise for
        INR); Razorpay expects an integer.
        """
        if not self.is_configured:
            raise PaymentGatewayNotConfigured(
                "Payment gateway is not configured. Set RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET."
            )
        payload: dict[str, Any] = {
            "amount": int(amount_paise),
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        }
        if notes:
            payload["notes"] = notes
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{RAZORPAY_API_BASE}/orders",
                    json=payload,
                    auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                )
        except httpx.HTTPError as exc:  # network/timeout
            raise PaymentGatewayError("Could not reach the payment gateway") from exc
        if response.status_code >= 400:
            raise PaymentGatewayError(
                f"Payment gateway rejected the order (HTTP {response.status_code})"
            )
        return response.json()

    def verify_payment_signature(
        self,
        *,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """Verify the checkout `razorpay_signature` for a captured payment."""
        if not (order_id and payment_id and signature):
            return False
        expected = hmac.new(
            settings.razorpay_key_secret.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_webhook_signature(self, *, body: bytes, signature: str) -> bool:
        """Verify the `X-Razorpay-Signature` header against the raw body."""
        if not (settings.razorpay_webhook_secret and signature):
            return False
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


payment_gateway = RazorpayGateway()
