import json
from pathlib import Path
from typing import Dict, List, Optional
from .models import Provider, ProviderRegistry

class Registry:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._providers: Dict[str, Provider] = {}
        self.reload()

    def reload(self) -> None:
        data = json.loads(self._path.read_text())
        reg = ProviderRegistry(**data)
        self._providers = {p.id: p for p in reg.providers}

    def list(self) -> List[Provider]:
        return list(self._providers.values())

    def get(self, pid: str) -> Optional[Provider]:
        return self._providers.get(pid)

    def set_status(self, pid: str, state: str) -> bool:
        p = self.get(pid)
        if not p:
            return False
        if state not in ("healthy", "down"):
            return False
        p.status = state  # mutate in-memory
        return True

    def replace(self, providers: List[Provider]) -> None:
        self._providers = {p.id: p for p in providers}
