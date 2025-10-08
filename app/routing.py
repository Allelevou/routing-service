from typing import List, Optional, Tuple
from datetime import datetime
import random

from .models import Tx, Provider, Attempt, RouteDecision

EU_COUNTRIES = {
    "DE","FR","ES","IT","NL","BE","PT","IE","AT","FI","GR","SE","DK","PL","CZ","HU",
    "RO","BG","SK","SI","HR","LT","LV","EE","LU","CY","MT"
}

def country_to_region(country: str) -> str:
    country = country.upper()
    if country == "ZA":
        return "ZA"
    if country == "US":
        return "US"
    if country in EU_COUNTRIES:
        return "EU"
    # Fallback: treat the country code itself as a region tag
    return country

def compatible(p: Provider, tx: Tx) -> Tuple[bool, List[str]]:
    reasons = []
    if p.status != "healthy":
        reasons.append("unhealthy")
    if tx.currency not in p.currencies:
        reasons.append("currency")
    if tx.scheme and tx.scheme not in p.schemes:
        reasons.append("scheme")
    if tx.fundingType and tx.fundingType not in p.funding:
        reasons.append("funding")
    dest_region = country_to_region(tx.destinationCountry)
    if dest_region not in p.regions:
        reasons.append("region")
    return (len(reasons) == 0, reasons)

def score_provider(p: Provider, candidates: List[Provider]) -> float:
    # Higher is better. Normalize cost so lower cost => higher score.
    max_cost = max(x.costBps for x in candidates) if candidates else p.costBps
    cost_factor = (max_cost / p.costBps) if p.costBps > 0 else 1.0
    return p.baseWeight * cost_factor

def choose_provider(tx: Tx, providers: List[Provider]) -> RouteDecision:
    now = lambda: datetime.utcnow().isoformat() + "Z"
    decision = RouteDecision(paymentId=tx.id, ruleId="v1_weighted_cost")

    considered = []
    incompatible_attempts = []
    for p in providers:
        ok, reasons = compatible(p, tx)
        if ok:
            considered.append(p)
        else:
            # record an attempt explaining incompatibility
            outcome = "unhealthy" if "unhealthy" in reasons else "incompatible"
            decision.attempts.append(Attempt(
                providerId=p.id, ts=now(), outcome=outcome, latencyMs=random.randint(8, 35)
            ))
            incompatible_attempts.append((p, reasons))

    if not considered:
        return decision  # providerId stays None; caller will 503

    # Weighted random by baseWeight + cost advantage
    weights = [score_provider(p, considered) for p in considered]
    selected = random.choices(considered, weights=weights, k=1)[0]

    # mark all considered as "considered" then selected as "selected"
    for p in considered:
        decision.attempts.append(Attempt(
            providerId=p.id, ts=now(),
            outcome="selected" if p.id == selected.id else "considered",
            latencyMs=random.randint(10, 80)
        ))

    decision.providerId = selected.id
    return decision