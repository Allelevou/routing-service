# Developer Documentation

## Setup & Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)
- Git

### Local Development Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository-url>
   cd routing-service
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   
   # On macOS/Linux
   source .venv/bin/activate
   
   # On Windows
   .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Development Server**
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Verify Installation**
   - Open http://127.0.0.1:8000/docs for interactive API documentation
   - Check health endpoint: http://127.0.0.1:8000/health

### Development Dependencies
```
fastapi==0.112.2      # Web framework
uvicorn[standard]==0.30.6  # ASGI server
pydantic==2.8.2       # Data validation
pytest==8.3.2         # Testing framework
```

## Code Structure & Organization

### Project Layout
```
routing-service/
├── app/
│   ├── __init__.py       # Package initialization
│   ├── main.py           # FastAPI application and endpoints
│   ├── models.py         # Pydantic data models
│   ├── registry.py       # Provider registry management
│   ├── routing.py        # Core routing algorithm
│   └── storage.py        # Idempotency storage
├── tests/
│   └── test_routing.py   # Unit tests
├── docs/                 # Documentation
├── providers.json        # Provider configuration
├── transactions.json     # Sample transactions
├── requirements.txt      # Python dependencies
└── README.md            # Project overview
```

### Module Responsibilities

#### `app/main.py` - HTTP Layer
```python
# FastAPI application with endpoint definitions
# Handles HTTP request/response, error handling
# Coordinates between routing engine and registry

Key Functions:
- health() - Service health check
- route(tx: Tx) - Main routing endpoint
- list_providers() - Admin: view provider status
- set_status() - Admin: update provider health
- reload_registry() - Admin: hot-reload configuration
```

#### `app/models.py` - Data Models
```python
# Pydantic models for request/response validation
# Type safety and automatic API documentation

Key Models:
- Tx: Transaction request payload
- Provider: Provider configuration schema
- RouteDecision: Routing response with audit trail
- Attempt: Individual provider evaluation record
```

#### `app/registry.py` - Provider Management
```python
# In-memory provider registry with JSON persistence
# Thread-safe provider operations

Key Methods:
- reload() - Load providers from JSON file
- list() - Get all providers
- get(pid) - Get specific provider
- set_status() - Update provider health status
```

#### `app/routing.py` - Business Logic
```python
# Core routing algorithm implementation
# Provider compatibility and scoring logic

Key Functions:
- choose_provider() - Main routing algorithm
- compatible() - Provider compatibility check
- score_provider() - Provider scoring calculation
- country_to_region() - Geographic region mapping
```

#### `app/storage.py` - Persistence
```python
# Simple in-memory idempotency storage
# Production should use Redis/database

Key Interface:
- get(key) - Retrieve cached decision
- put(key, value) - Store routing decision
```

## Design Patterns & Conventions

### Code Style Guidelines

1. **Type Hints**: Use type hints for all function parameters and return values
   ```python
   def choose_provider(tx: Tx, providers: List[Provider]) -> RouteDecision:
   ```

2. **Pydantic Models**: Use Pydantic for all data validation and serialization
   ```python
   class Tx(BaseModel):
       id: str
       amountMinor: int
   ```

3. **Error Handling**: Use FastAPI HTTPException for API errors
   ```python
   if not ok:
       raise HTTPException(status_code=400, detail="Invalid provider")
   ```

4. **Logging**: Use structured logging (not implemented yet, but recommended)
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Provider selected", provider_id=selected.id)
   ```

### Architectural Patterns

#### Dependency Injection
- Registry and storage are module-level singletons
- Consider using FastAPI's dependency injection for testability

#### Repository Pattern
- `Registry` class abstracts provider data access
- Enables easy swapping of storage backends

#### Strategy Pattern
- Routing algorithm is pluggable via `choose_provider` function
- Different scoring strategies can be implemented

## Testing Guide

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_routing.py

# Run with coverage (if coverage package installed)
pytest --cov=app
```

### Test Structure

```python
# tests/test_routing.py
def test_basic_routing():
    # Arrange
    reg = Registry(path="./providers.json")
    tx = Tx(id="t_test", amountMinor=10000, ...)
    
    # Act
    decision = choose_provider(tx, reg.list())
    
    # Assert
    assert decision.providerId in {"AcqA", "AcqB"}
```

### Testing Best Practices

1. **Test Data**: Use realistic but simplified test data
2. **Isolation**: Each test should be independent
3. **Coverage**: Aim for high coverage of business logic
4. **Edge Cases**: Test error conditions and edge cases

### Adding New Tests

```python
def test_no_compatible_providers():
    """Test routing when no providers support the transaction"""
    providers = [create_usd_only_provider()]
    tx = create_eur_transaction()
    
    decision = choose_provider(tx, providers)
    
    assert decision.providerId is None
    assert len(decision.attempts) == 1
    assert decision.attempts[0].outcome == "incompatible"
```

## Development Workflows

### Adding a New Provider
1. Update `providers.json` with new provider configuration
2. Test with `POST /admin/reload` endpoint
3. Verify with `GET /admin/providers`
4. Add integration test if needed

### Modifying Routing Logic
1. Update logic in `app/routing.py`
2. Add/update unit tests in `tests/test_routing.py`
3. Test with sample transactions via `/route` endpoint
4. Verify backward compatibility

### Adding New Endpoints
1. Add endpoint function to `app/main.py`
2. Define request/response models in `app/models.py`
3. Add endpoint documentation
4. Write integration tests

### Environment Configuration
```bash
# Environment variables (not currently used but recommended)
export PROVIDERS_FILE=./providers.json
export LOG_LEVEL=INFO
export IDEMPOTENCY_TTL=86400  # 24 hours in seconds
```

## Debugging Guide

### Common Issues

#### 1. "No provider available" (503 Error)
**Symptoms**: `/route` returns 503 with empty `providerId`
**Causes**:
- All providers marked as "down"
- No providers support the transaction currency/region/scheme
- Provider registry file is empty or malformed

**Debug Steps**:
```bash
# Check provider status
curl http://localhost:8000/admin/providers

# Check provider health
curl -X POST http://localhost:8000/admin/providers/AcqA/status/healthy

# Reload configuration
curl -X POST http://localhost:8000/admin/reload
```

#### 2. Validation Errors (422)
**Symptoms**: Request returns validation error details
**Causes**: Invalid transaction payload format

**Debug Steps**:
```bash
# Check required fields in transaction
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_123",
    "amountMinor": 10000,
    "currency": "USD",
    "originCountry": "US",
    "destinationCountry": "US"
  }'
```

#### 3. Provider Registry Issues
**Symptoms**: Registry reload fails or providers not found
**Causes**: Malformed JSON, file permissions, missing file

**Debug Steps**:
```bash
# Validate JSON format
python -m json.tool providers.json

# Check file permissions
ls -la providers.json

# Test registry loading
python -c "from app.registry import Registry; r = Registry('./providers.json'); print(len(r.list()))"
```

### Logging and Monitoring

#### Application Logs
```python
# Add to app/main.py for request logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/route")
def route(tx: Tx):
    logger.info(f"Routing transaction {tx.id} for {tx.currency}")
    # ... existing logic
```

#### Health Check Monitoring
```bash
# Basic health check
curl http://localhost:8000/health

# Provider count monitoring
curl http://localhost:8000/health | jq '.providers'
```

### Development Tools

#### Interactive API Testing
- FastAPI auto-generates interactive docs at `/docs`
- Use for testing endpoints during development
- Built-in request/response validation

#### Database Inspection (Future)
```python
# When adding persistent storage
from app.storage import get_db_connection
conn = get_db_connection()
# Inspect idempotency records, routing history, etc.
```

## Performance Optimization

### Current Performance Characteristics
- **Request Processing**: O(n) where n = number of providers
- **Memory Usage**: Constant per request (registry cached)
- **Concurrency**: Thread-safe provider registry

### Optimization Strategies

1. **Provider Filtering**: Add indexes for common filter combinations
2. **Caching**: Cache routing decisions for identical transactions
3. **Async Processing**: Convert to async/await for better concurrency
4. **Database**: Replace in-memory storage with proper database

### Load Testing
```bash
# Using Apache Bench (if installed)
ab -n 1000 -c 10 -T 'application/json' \
   -p transaction.json \
   http://localhost:8000/route
```

## Contributing Guidelines

### Code Review Checklist
- [ ] Type hints on all functions
- [ ] Unit tests for new functionality
- [ ] Documentation updates
- [ ] No hardcoded configuration values
- [ ] Error handling for edge cases
- [ ] Backward compatibility maintained

### Commit Message Format
```
feat: add support for new payment scheme
fix: handle edge case in region mapping
docs: update API documentation
test: add coverage for provider scoring
```

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Individual feature development
- `hotfix/*`: Critical production fixes