from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional

from .models import Tx, RouteDecision
from .registry import Registry
from .routing import choose_provider
from .storage import IDEMPOTENCY

app = FastAPI(title="Payment Routing Service", version="1.0.0")

REGISTRY = Registry(path="./providers.json")

@app.get("/health")
def health():
    return {"ok": True, "providers": len(REGISTRY.list())}

@app.get("/admin/providers")
def list_providers():
    return {"providers": [p.model_dump() for p in REGISTRY.list()]}

@app.post("/admin/providers/{pid}/status/{state}")
def set_status(pid: str, state: str):
    ok = REGISTRY.set_status(pid, state)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid provider or state")
    return {"ok": True, "provider": pid, "status": state}

@app.post("/admin/reload")
def reload_registry():
    REGISTRY.reload()
    return {"ok": True, "providers": [p.id for p in REGISTRY.list()]}

@app.post("/route", response_model=RouteDecision)
def route(tx: Tx):
    # Idempotency: return prior decision for the same idempotency key
    if tx.idempotencyKey:
        prev = IDEMPOTENCY.get(tx.idempotencyKey)
        if prev:
            return prev

    decision = choose_provider(tx, REGISTRY.list())

    if not decision.providerId:
        raise HTTPException(status_code=503, detail="No provider available")

    if tx.idempotencyKey:
        IDEMPOTENCY.put(tx.idempotencyKey, decision)

    return decision
