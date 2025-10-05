from typing import Dict, Optional
from .models import RouteDecision

class IdempotencyStore:
    def __init__(self) -> None:
        self._store: Dict[str, RouteDecision] = {}

    def get(self, key: str) -> Optional[RouteDecision]:
        return self._store.get(key)

    def put(self, key: str, decision: RouteDecision) -> None:
        self._store[key] = decision

    def clear(self) -> None:
        self._store.clear()

IDEMPOTENCY = IdempotencyStore()
