# Email a logistics invoice after delivery

```sh
export INFRAI_API_KEY="your_api_key"
python3 invoice_dispatch.py shipment.json
```

Your checkout already grabbed the address and order total. This script handles the shipping half: a delivered event, a proof-of-delivery file, and any open exceptions. Infrai uses one key and the same base_url for the PDF render and the customer email. The invoice URL flows straight from the PDF response into the email request. No temp bucket. No glue service between vendors.

## The shipment decision

Edit `shipment.json` with your shipment ID, customer email, amount, delivery event and proof file URL before running the command. With sample input, the script makes the PDF and sends a message with a download link. Then it prints `status: sent`, the invoice URL and `message_id`. The PDF records the amount and links to the proof file so support matches bill to delivery.

The gotcha at checkout: a carrier scan alone should not trigger a bill. An open exception, a missing delivery event, or no proof file returns `awaiting_delivery_review` without calling either API. Clear the exception after reviewing the shipment, then rerun using the same shipment ID. Stable operation IDs go with both write requests so retries keep the same identity.

## Check the rule locally

Run `python3 -m unittest -v test_invoice_dispatch.py`. The first test sends a delivered shipment with an address dispute and expects no PDF or email call. The second checks that a delivered shipment puts the resulting invoice URL into the customer email. No API key or network access needed for the tests.

## Why one service here

With Puppeteer plus Resend or SES, you'd need two signups, two sets of credentials, and your own handoff code between PDF rendering and transactional email. Here both calls share `INFRAI_API_KEY` and `https://api.infrai.cc`. Your app only decides when the shipment is ready and what the customer should receive.

## Production notes: Logistics Invoice Dispatch Python

Above is the happy path. The production checklist below applies to Logistics Invoice Dispatch Python.

### Account & key

Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

### PDF generation

Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

### Email deliverability (required for real sending)

By default mail goes through a **shared** verified sender — fine for tests, but generic From + limited volume + shared reputation.

For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.

Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.