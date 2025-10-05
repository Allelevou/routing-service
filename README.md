# Payment Routing Service (FastAPI)

A minimal payment routing service that selects an acquirer/provider for an incoming transaction.
It loads a provider registry from `providers.json`, applies compatibility filters (currency,
region, scheme, funding, health), and then chooses among candidates using a weight-and-cost
scoring strategy.

## Quickstart

```bash
# Python 3.10+
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run
uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs
```

## Endpoints

- `GET /health` – basic liveness + count of providers
- `GET /admin/providers` – list providers (in-memory state)
- `POST /admin/providers/{pid}/status/{state}` – set status to `healthy` or `down`
- `POST /admin/reload` – reload `providers.json` from disk
- `POST /route` – body is a `Tx`, returns `RouteDecision`

### Example `Tx`

```json
{
  "id": "pay_123",
  "amountMinor": 125000,
  "currency": "ZAR",
  "originCountry": "ZA",
  "destinationCountry": "ZA",
  "scheme": "visa",
  "fundingType": "debit",
  "mcc": "4722",
  "idempotencyKey": "idem_pay_123"
}
```

## Routing Logic (v1)

1. Load healthy providers.
2. Filter by: currency, destination region, optional scheme, optional funding.
3. Score candidates by `baseWeight * (max_cost / costBps)`.
4. Weighted random pick among candidates to allow traffic shaping.
5. Record attempts and return `RouteDecision`.
6. If `idempotencyKey` is provided, return the same decision on retries.

### Regions

The sample registry uses region tags: `ZA`, `US`, `EU`. We derive a simple region for
`destinationCountry`:
- ZA → ZA
- US → US
- EU members → EU
- Otherwise use the country code as-is (strict match).

You can customize this in `app/routing.py`.

## Testing

```bash
pytest -q
```

## Try it

```bash
# Example decision
curl -s -X POST http://127.0.0.1:8000/route \\
  -H "Content-Type: application/json" \\
  -d @transactions.json | jq
```

## Notes

- This demo keeps all state in memory. For production, back the registry and idempotency store
  with a proper database or config service.
- Extend the scoring logic with SLA, latency histograms, failure rates, MCC-based rules,
  or time-of-day caps as needed.
# routing-service
# routing-service
