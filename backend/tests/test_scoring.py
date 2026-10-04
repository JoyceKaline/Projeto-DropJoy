from types import SimpleNamespace
from app.services.scoring import finance, dropjoy_score

def test_finance_and_score_ranges():
    supplier = SimpleNamespace(reliability=.9)
    product = SimpleNamespace(sale_price=100.0, competition_score=.8)
    offer = SimpleNamespace(cost=50.0, stock=100, shipping_hours=24, supplier=supplier)
    f = finance(product, offer)
    assert f["fees"] == 24.0
    assert f["profit"] == 26.0
    assert f["margin"] == 26.0
    score = dropjoy_score(product, offer)
    assert 0 <= score <= 100
