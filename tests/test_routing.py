import json
from app.models import Tx
from app.registry import Registry
from app.routing import choose_provider

def test_basic_routing():
    reg = Registry(path="./providers.json")
    tx = Tx(
        id="t_test",
        amountMinor=10000,
        currency="ZAR",
        originCountry="ZA",
        destinationCountry="ZA",
        scheme="visa",
        fundingType="debit",
    )
    decision = choose_provider(tx, reg.list())
    assert decision.providerId in {"AcqA", "AcqB"}  # only ZA + ZAR + visa debit
