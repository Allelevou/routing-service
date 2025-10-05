from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict

class Tx(BaseModel):
    id: str
    amountMinor: int
    currency: str
    originCountry: str
    destinationCountry: str
    scheme: Optional[Literal["visa", "mastercard", "amex"]] = None
    fundingType: Optional[Literal["debit", "credit"]] = None
    mcc: Optional[str] = None
    idempotencyKey: Optional[str] = None

class Attempt(BaseModel):
    providerId: str
    ts: str
    outcome: Literal["considered", "selected", "skipped", "unhealthy", "incompatible"]
    latencyMs: int

class RouteDecision(BaseModel):
    paymentId: str
    providerId: Optional[str] = None
    ruleId: Optional[str] = None
    attempts: List[Attempt] = Field(default_factory=list)

class Provider(BaseModel):
    id: str
    regions: List[str]
    currencies: List[str]
    schemes: List[str]
    funding: List[str]
    baseWeight: int
    costBps: int
    status: Literal["healthy", "down"] = "healthy"

class ProviderRegistry(BaseModel):
    providers: List[Provider]
