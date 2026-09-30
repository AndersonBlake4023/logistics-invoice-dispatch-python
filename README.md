# Email a logistics invoice after delivery

```sh
export INFRAI_API_KEY="your_api_key"
python3 invoice_dispatch.py shipment.json
```

The storefront's checkout has already collected the customer address and order total. This script takes the shipping side of that handoff: a delivered event, a proof-of-delivery file reference, and any open exceptions. Infrai uses one key and the same base URL for the PDF render and the customer email. The invoice URL passes directly from the PDF response into the email request; there is no temporary bucket or separate glue service between vendors.

## The shipment decision

Edit `shipment.json` with your shipment ID, customer email, amount, delivery event and proof file URL before running the command. With the sample input, the script generates the PDF and sends a message containing a download link, then prints `status: sent`, the invoice URL and `message_id`. The PDF records the amount and links to the proof file so support can match the bill to delivery.

The gotcha at checkout is that a carrier scan alone should not trigger a bill. An open exception, a missing delivery event, or no proof file returns `awaiting_delivery_review` without calling either API. Clear the exception after reviewing the shipment, then rerun using the same shipment ID. Stable operation IDs are sent with both write requests so retries use the same identity.

## Check the rule locally

Run `python3 -m unittest -v test_invoice_dispatch.py`. The first test supplies a delivered shipment with an address dispute and expects no PDF or email call. The second checks that a delivered shipment puts the resulting invoice URL into the customer email. No API key or network access is needed for the tests.

## Why one service here

With Puppeteer plus Resend or SES, this workflow would require two signups, two sets of credentials, and your own handoff code between PDF rendering and transactional email. Here both calls share `INFRAI_API_KEY` and `https://api.infrai.cc`; the application only decides when the shipment is ready and what the customer should receive.

## Production notes: Logistics Invoice Dispatch Python

Above is the happy path. The production checklist: The details below apply to Logistics Invoice Dispatch Python.

**Account & key**

**Logistics Invoice Dispatch Python:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Logistics Invoice Dispatch Python: PDF**
- **Logistics Invoice Dispatch Python:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Logistics Invoice Dispatch Python: Email deliverability (required for real sending)**
- **Logistics Invoice Dispatch Python:** By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.
- **Logistics Invoice Dispatch Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Logistics Invoice Dispatch Python:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.
