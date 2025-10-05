# Architecture & Design Documentation

## System Architecture

### High-Level Overview

The Payment Routing Service is a FastAPI-based microservice that intelligently routes payment transactions to optimal payment providers (acquirers) based on configurable rules and real-time provider health status.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │───▶│  Routing Service │───▶│   Providers     │
│                 │    │                  │    │  (AcqA, AcqB..) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Provider     │
                       │ Registry     │
                       │ (JSON)       │
                       └──────────────┘
```

### Core Components

#### 1. FastAPI Application (`app/main.py`)
- **Purpose**: HTTP API layer with endpoint definitions
- **Key Endpoints**:
  - `POST /route` - Core routing logic
  - `GET /health` - Service health check
  - `GET /admin/providers` - Provider status view
  - `POST /admin/providers/{pid}/status/{state}` - Provider management
  - `POST /admin/reload` - Hot-reload provider configuration

#### 2. Provider Registry (`app/registry.py`)
- **Purpose**: In-memory provider management and configuration loading
- **Features**:
  - JSON-based provider configuration
  - Hot-reload capability
  - Runtime status management
  - Provider lookup and filtering

#### 3. Routing Engine (`app/routing.py`)
- **Purpose**: Core business logic for provider selection
- **Algorithm**: Weighted random selection with cost optimization
- **Compatibility Filtering**: Currency, region, scheme, funding type, health status

#### 4. Data Models (`app/models.py`)
- **Purpose**: Pydantic models for request/response validation
- **Key Models**: `Tx`, `Provider`, `RouteDecision`, `Attempt`

#### 5. Idempotency Storage (`app/storage.py`)
- **Purpose**: Prevents duplicate processing of identical requests
- **Implementation**: In-memory dictionary (production should use persistent storage)

## Routing Algorithm Deep Dive

### Decision Flow

```
Transaction Request
        │
        ▼
┌───────────────────┐
│ Load Providers    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Apply Filters     │
│ - Health Status   │
│ - Currency        │
│ - Region          │
│ - Scheme          │
│ - Funding Type    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Score Candidates  │
│ weight × cost     │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Weighted Random   │
│ Selection         │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ Return Decision   │
│ + Audit Trail     │
└───────────────────┘
```

### Compatibility Filtering

Each provider must pass all compatibility checks:

1. **Health Status**: `provider.status == "healthy"`
2. **Currency Support**: `transaction.currency in provider.currencies`
3. **Regional Coverage**: `derive_region(transaction.destinationCountry) in provider.regions`
4. **Scheme Support**: `transaction.scheme in provider.schemes` (if specified)
5. **Funding Type**: `transaction.fundingType in provider.funding` (if specified)

### Scoring Algorithm

```python
def score_provider(provider, all_candidates):
    max_cost = max(p.costBps for p in all_candidates)
    cost_factor = max_cost / provider.costBps  # Lower cost = higher score
    return provider.baseWeight * cost_factor
```

**Key Principles**:
- Higher `baseWeight` = more likely to be selected
- Lower `costBps` = more likely to be selected
- Weighted random ensures traffic distribution while favoring optimal providers

### Regional Mapping

```python
def country_to_region(country: str) -> str:
    if country == "ZA": return "ZA"
    if country == "US": return "US"
    if country in EU_COUNTRIES: return "EU"
    return country  # Fallback to country code
```

## Data Models Reference

### Transaction (`Tx`)
```python
class Tx(BaseModel):
    id: str                    # Unique transaction identifier
    amountMinor: int          # Amount in minor currency units (cents)
    currency: str             # ISO 4217 currency code
    originCountry: str        # ISO 3166-1 alpha-2 country code
    destinationCountry: str   # ISO 3166-1 alpha-2 country code
    scheme: Optional[str]     # "visa", "mastercard", "amex"
    fundingType: Optional[str] # "debit", "credit"
    mcc: Optional[str]        # Merchant Category Code
    idempotencyKey: Optional[str] # For duplicate request prevention
```

### Provider (`Provider`)
```python
class Provider(BaseModel):
    id: str                   # Unique provider identifier
    regions: List[str]        # Supported regions ["ZA", "US", "EU"]
    currencies: List[str]     # Supported currencies ["USD", "EUR", "ZAR"]
    schemes: List[str]        # Supported card schemes ["visa", "mastercard"]
    funding: List[str]        # Supported funding types ["debit", "credit"]
    baseWeight: int          # Base routing weight (higher = more traffic)
    costBps: int            # Cost in basis points (lower = cheaper)
    status: str             # "healthy" or "down"
```

### Route Decision (`RouteDecision`)
```python
class RouteDecision(BaseModel):
    paymentId: str           # Copy of transaction.id
    providerId: Optional[str] # Selected provider ID (None if no provider found)
    ruleId: Optional[str]    # Routing rule version identifier
    attempts: List[Attempt]  # Audit trail of all provider evaluations
```

### Attempt (`Attempt`)
```python
class Attempt(BaseModel):
    providerId: str          # Provider that was evaluated
    ts: str                 # ISO timestamp of evaluation
    outcome: str            # "selected", "considered", "incompatible", etc.
    latencyMs: int          # Simulated processing latency
```

## Provider Registry Configuration

### File Format (`providers.json`)
```json
{
  "providers": [
    {
      "id": "AcqA",
      "regions": ["ZA"],
      "currencies": ["ZAR", "USD"],
      "schemes": ["visa", "mastercard"],
      "funding": ["debit", "credit"],
      "baseWeight": 70,
      "costBps": 180,
      "status": "healthy"
    }
  ]
}
```

### Configuration Guidelines

**Provider ID**: Must be unique across all providers
**Regions**: Use standard codes: "ZA", "US", "EU", or specific country codes
**Currencies**: ISO 4217 three-letter codes
**Schemes**: Lowercase: "visa", "mastercard", "amex"
**Funding**: "debit", "credit"
**Base Weight**: Integer 1-100 (higher = more traffic preference)
**Cost BPS**: Basis points (e.g., 180 = 1.8%)
**Status**: "healthy" or "down"

## Idempotency Design

### Purpose
Prevents duplicate transaction processing when clients retry requests with the same `idempotencyKey`.

### Implementation
```python
if tx.idempotencyKey:
    prev = IDEMPOTENCY.get(tx.idempotencyKey)
    if prev:
        return prev  # Return cached decision
```

### Considerations
- Current implementation uses in-memory storage
- Production environments should use Redis or database storage
- Consider TTL for idempotency keys (e.g., 24 hours)

## Error Handling Strategy

### HTTP Status Codes
- `200`: Successful routing
- `400`: Invalid provider ID or status in admin endpoints
- `422`: Invalid request payload (Pydantic validation)
- `503`: No providers available for transaction

### Graceful Degradation
- If no providers are healthy, return 503 with empty `providerId`
- Malformed provider registry logs error but doesn't crash service
- Individual provider compatibility failures are logged in `attempts`

## Performance Characteristics

### Time Complexity
- Provider filtering: O(n) where n = number of providers
- Scoring: O(n)
- Selection: O(n)
- Overall: O(n) per routing request

### Memory Usage
- Provider registry: O(n) providers in memory
- Idempotency cache: O(m) recent transactions
- No persistent state beyond configuration file

### Scalability Considerations
- Stateless design enables horizontal scaling
- Provider registry shared across instances (file-based)
- Consider external configuration service for large deployments