"""크레딧 원장·주문·결제 승인 시험. 가짜 LLM, 가짜 토스 승인(실제 토스페이먼츠를 부르지 않음), 임시 파일 DB."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import credits as creditlib
import main
from llm import FakeLLM


class FakeToss:
    """결제 승인 API 대신. 응답 모양은 승인 성공 시 Payment 객체의 일부(orderId·totalAmount·approvedAt·status)."""

    def __init__(self, ok=True):
        self.calls, self.ok = [], ok

    def __call__(self, payment_key, order_id, amount, idempotency_key):
        self.calls.append({"paymentKey": payment_key, "orderId": order_id, "amount": amount, "idem": idempotency_key})
        if not self.ok:
            return {"ok": False, "status": 400, "body": {"code": "REJECT_CARD_COMPANY", "message": "카드사에서 거절했습니다."}}
        return {"ok": True, "status": 200, "body": {"orderId": order_id, "totalAmount": amount, "status": "DONE",
                                                    "approvedAt": "2026-11-04T12:00:00+09:00", "paymentKey": payment_key}}


@pytest.fixture
def env(tmp_path):
    main._hits.clear()
    store = creditlib.Store(tmp_path / "credit.db")
    toss = FakeToss()
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM(delay=0)
    main.app.dependency_overrides[main.get_credit_store] = lambda: store
    main.app.dependency_overrides[main.get_toss_confirm] = lambda: toss
    yield TestClient(main.app), store, toss
    main.app.dependency_overrides.clear()


def hdr(cid):
    return {"X-Client-Id": cid}


def chat(client, cid, text="안녕"):
    return client.post("/api/chat", json={"messages": [{"role": "user", "content": text}]}, headers=hdr(cid))


def drain_to(store, cid, target):
    """원장에 -줄을 직접 쌓아 잔액을 target 으로 만든다(시험 준비)."""
    store.ensure_client(cid, "test")
    for _ in range(store.balance(cid) - target):
        assert store.charge(cid, "chat:" + uuid.uuid4().hex)[0]


def order(client, cid, pid="credits_100"):
    r = client.post("/api/orders", json={"productId": pid}, headers=hdr(cid))
    assert r.status_code == 200
    return r.json()


def test_first_visit_gets_free_credits_once(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    assert client.get("/api/credits", headers=hdr(cid)).json()["balance"] == creditlib.FREE_CREDITS
    assert client.get("/api/credits", headers=hdr(cid)).json()["balance"] == creditlib.FREE_CREDITS  # 두 번 불러도 한 번


def test_bad_client_id_rejected(env):
    client, _, _ = env
    assert client.get("/api/credits", headers=hdr("not-a-uuid")).status_code == 400
    assert chat(client, "x").status_code == 400


def test_one_message_costs_one_credit(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    before = client.get("/api/credits", headers=hdr(cid)).json()["balance"]
    r = chat(client, cid)
    assert r.status_code == 200 and any(json.loads(x)["type"] == "done" for x in r.text.splitlines() if x)
    after = client.get("/api/credits", headers=hdr(cid)).json()
    assert after["balance"] == before - 1
    assert after["recent"][0]["delta"] == -1 and after["recent"][0]["ref"].startswith("chat:")


def test_zero_balance_gets_402_and_model_not_called(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    drain_to(store, cid, 0)
    calls = []

    class Spy(FakeLLM):
        def complete_json(self, *a, **k):
            calls.append(1)
            return super().complete_json(*a, **k)

    main.app.dependency_overrides[main.get_llm] = lambda: Spy(delay=0)
    r = chat(client, cid)
    assert r.status_code == 402
    assert r.json()["error"] == "insufficient_credits" and r.json()["balance"] == 0 and r.json()["message"]
    assert calls == []


def test_failed_reply_is_refunded(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    store.ensure_client(cid, "test")
    r = chat(client, cid, "fake:error")  # 가짜 LLM 이 답을 만들다 실패
    assert '"type": "error"' in r.text
    rows = store.recent(cid)
    assert store.balance(cid) == creditlib.FREE_CREDITS
    assert rows[0]["reason"] == "refund" and rows[1]["reason"] == "chat"
    assert rows[0]["ref"].split(":")[1] == rows[1]["ref"].split(":")[1]


def test_byok_is_not_charged(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    store.ensure_client(cid, "test")
    main.app.dependency_overrides[main.get_user_llm_factory] = lambda: (lambda key: FakeLLM(delay=0))
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]},
                    headers={**hdr(cid), "X-User-LLM-Key": "sk-" + "a" * 40})
    assert r.status_code == 200
    assert store.balance(cid) == creditlib.FREE_CREDITS


def test_products_come_from_server_table(env):
    client, _, _ = env
    got = {p["id"]: (p["amount"], p["credits"]) for p in client.get("/api/products").json()["products"]}
    assert got == {"credits_100": (1000, 100), "credits_550": (5000, 550), "credits_1200": (10000, 1200)}


def test_order_uses_server_price_and_random_id(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    r = client.post("/api/orders", json={"productId": "credits_550", "amount": 1}, headers=hdr(cid)).json()
    assert r["amount"] == 5000 and r["credits"] == 550
    o = store.get_order(r["orderId"])
    assert o["status"] == "pending" and o["amount"] == 5000
    assert order(client, cid)["orderId"] != r["orderId"] and len(r["orderId"]) >= 20


def test_config_has_no_secret(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setenv("TOSS_SECRET_KEY", "test_gsk_SHOULD_NOT_LEAK")
    monkeypatch.setenv("TOSS_CLIENT_KEY", "test_gck_public")
    text = client.get("/api/config").text
    assert "gsk" not in text and "SHOULD_NOT_LEAK" not in text and "test_gck_public" in text


def test_live_keys_are_ignored(monkeypatch):
    import toss
    monkeypatch.setenv("TOSS_CLIENT_KEY", "live_gck_x")
    monkeypatch.setenv("TOSS_SECRET_KEY", "live_gsk_x")
    assert toss.client_key() == "" and toss.secret_key() == ""
    assert toss.confirm("pk", "ord_123456", 1000, "ord_123456")["body"]["code"] == "NOT_CONFIGURED"


def confirm(client, cid, o, amount=None, pk="tpk_test_123"):
    return client.post("/api/payments/confirm", headers=hdr(cid),
                       json={"paymentKey": pk, "orderId": o["orderId"], "amount": o["amount"] if amount is None else amount})


def test_confirm_twice_credits_once(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    store.ensure_client(cid, "test")
    o = order(client, cid)
    r1, r2 = confirm(client, cid, o), confirm(client, cid, o)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["balance"] == r2.json()["balance"] == creditlib.FREE_CREDITS + 100
    assert r2.json()["already"] is True
    assert len(toss.calls) == 1 and toss.calls[0]["idem"] == o["orderId"]  # 두 번째는 승인 API 를 다시 부르지 않음
    assert [r["ref"] for r in store.recent(cid)].count(f"order:{o['orderId']}") == 1
    so = store.get_order(o["orderId"])
    assert so["status"] == "done" and so["payment_key"] == "tpk_test_123" and so["approved_at"]


def test_changed_amount_rejected_without_calling_toss(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    o = order(client, cid)
    r = confirm(client, cid, o, amount=100)
    assert r.status_code == 400 and r.json()["error"] == "amount_mismatch"
    assert toss.calls == []
    assert store.get_order(o["orderId"])["status"] == "pending"
    assert store.balance(cid) == 0


def test_other_clients_order_rejected_without_calling_toss(env):
    client, store, toss = env
    owner, thief = str(uuid.uuid4()), str(uuid.uuid4())
    o = order(client, owner)
    r = confirm(client, thief, o)
    assert r.status_code == 404
    assert toss.calls == []
    assert store.balance(thief) == 0 and store.get_order(o["orderId"])["status"] == "pending"
    assert client.get(f"/api/orders/{o['orderId']}", headers=hdr(thief)).status_code == 404


def test_toss_failure_keeps_credits_and_fails_order(env):
    client, store, toss = env
    toss.ok = False
    cid = str(uuid.uuid4())
    store.ensure_client(cid, "test")
    o = order(client, cid)
    r = confirm(client, cid, o)
    assert r.status_code == 400 and r.json()["code"] == "REJECT_CARD_COMPANY"
    assert store.balance(cid) == creditlib.FREE_CREDITS
    assert store.get_order(o["orderId"])["status"] == "failed"
    assert confirm(client, cid, o).status_code == 409 and len(toss.calls) == 1  # 실패한 주문은 다시 승인하지 않음


def test_credits_off_keeps_old_behaviour(tmp_path):
    main._hits.clear()
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM(delay=0)
    try:
        client = TestClient(main.app)
        assert client.get("/api/credits").status_code == 404
        r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]})  # X-Client-Id 없이도 예전처럼
        assert r.status_code == 200
    finally:
        main.app.dependency_overrides.clear()


# ---- 일회 구매 상품(영구 소유): 테마·오늘의 좋은 말 ----
def pay_item(client, cid, item_id, toss):
    o = order(client, cid, item_id)
    r = client.post("/api/payments/confirm", json={"paymentKey": "pk_" + uuid.uuid4().hex[:10], "orderId": o["orderId"],
                                                   "amount": str(o["amount"])}, headers=hdr(cid))
    return o, r


def test_item_purchase_grants_ownership_not_credits(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    client.get("/api/credits", headers=hdr(cid))
    before = store.balance(cid)
    o, r = pay_item(client, cid, "theme_ocean", toss)
    assert r.status_code == 200 and r.json()["kind"] == "item"
    assert store.balance(cid) == before  # 크레딧은 늘지 않는다
    assert client.get("/api/shop", headers=hdr(cid)).json()["owned"] == ["theme_ocean"]
    assert o["amount"] == creditlib.ITEMS["theme_ocean"]["amount"]


def test_item_confirm_twice_owns_once(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    o, r = pay_item(client, cid, "daily_quote", toss)
    r2 = client.post("/api/payments/confirm", json={"paymentKey": "pk_x", "orderId": o["orderId"], "amount": str(o["amount"])}, headers=hdr(cid))
    assert r2.json()["already"] is True and len(toss.calls) == 1
    assert store.owned(cid) == ["daily_quote"]


def test_owned_item_cannot_be_ordered_again(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    pay_item(client, cid, "theme_rose", toss)
    r = client.post("/api/orders", json={"productId": "theme_rose"}, headers=hdr(cid))
    assert r.status_code == 409 and r.json()["error"] == "already_owned"


def test_quote_requires_ownership_on_server(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    assert client.get("/api/quote", headers=hdr(cid)).status_code == 403
    pay_item(client, cid, "daily_quote", toss)
    r = client.get("/api/quote", headers=hdr(cid))
    assert r.status_code == 200 and r.json()["quote"] == creditlib.quote_of_day()
    assert client.get("/api/quote", headers=hdr(str(uuid.uuid4()))).status_code == 403  # 남의 소유는 쓸 수 없다


def test_failed_item_payment_grants_nothing(env):
    client, store, toss = env
    toss.ok = False
    cid = str(uuid.uuid4())
    o, r = pay_item(client, cid, "theme_forest", toss)
    assert r.status_code == 400 and store.owned(cid) == []


def test_item_price_comes_from_server_table(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    o = order(client, cid, "theme_ocean")
    r = client.post("/api/payments/confirm", json={"paymentKey": "pk_y", "orderId": o["orderId"], "amount": "1"}, headers=hdr(cid))
    assert r.status_code == 400 and store.owned(cid) == [] and toss.calls == []


def test_quote_of_day_is_stable_per_day():
    import datetime
    d = datetime.date(2026, 11, 4)
    assert creditlib.quote_of_day(d) == creditlib.quote_of_day(d) and len(set(creditlib.QUOTES)) == len(creditlib.QUOTES)
