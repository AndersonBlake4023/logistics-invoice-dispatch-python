import unittest
from unittest.mock import patch

from invoice_dispatch import InvoiceRequest, ProofOfDelivery, ShipmentEvent, dispatch_invoice


class InvoiceDispatchTests(unittest.TestCase):
    def shipment(self, exceptions=None):
        return InvoiceRequest(
            shipment_id="SHIP-1042",
            customer_email="buyer@example.com",
            customer_name="Taylor",
            amount="42.00",
            currency="USD",
            events=[ShipmentEvent("delivered", "2026-09-19T12:00:00Z")],
            proof_of_delivery=[ProofOfDelivery("Signed receipt", "https://example.com/pod/1042")],
            exceptions=exceptions or [],
        )

    @patch("invoice_dispatch.post")
    def test_exception_holds_invoice(self, post):
        self.assertEqual(dispatch_invoice(self.shipment(["address disputed"]))["status"], "awaiting_delivery_review")
        post.assert_not_called()

    @patch("invoice_dispatch.post")
    def test_delivered_invoice_goes_to_customer(self, post):
        post.side_effect = [{"url": "https://example.com/invoice.pdf"}, {"message_id": "msg-1042"}]
        result = dispatch_invoice(self.shipment())
        self.assertEqual(result["message_id"], "msg-1042")
        self.assertEqual(post.call_args_list[0].args[0], "/v1/pdf/generate")
        self.assertEqual(post.call_args_list[1].args[0], "/v1/email/send")
        self.assertIn("invoice.pdf", post.call_args_list[1].args[1]["html"])


if __name__ == "__main__":
    unittest.main()
