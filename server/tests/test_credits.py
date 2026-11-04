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


def order(client, cid, pid="credits_100"):
    r = client.post("/api/orders", json={"productId": pid}, headers=hdr(cid))
    assert r.status_code == 200
    return r.json()


def test_bad_client_id_rejected(env):
    client, _, _ = env
    assert client.get("/api/credits", headers=hdr("not-a-uuid")).status_code == 400
    assert chat(client, "x").status_code == 400


def test_chat_is_free_and_stops_at_the_daily_limit(env, monkeypatch):
    client, store, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 2)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    calls = []

    class Spy(FakeLLM):
        def complete_json(self, *a, **k):
            calls.append(1)
            return super().complete_json(*a, **k)

    main.app.dependency_overrides[main.get_llm] = lambda: Spy(delay=0)
    for _ in range(2):
        r = chat(client, cid)
        assert r.status_code == 200 and any(json.loads(x)["type"] == "done" for x in r.text.splitlines() if x)
    assert store.balance(cid) == 0  # 도우미 대화는 크레딧을 쓰지 않는다
    before = len(calls)
    r = chat(client, cid)
    assert r.status_code == 429 and r.json()["error"] == "daily_limit" and r.json()["message"]
    assert len(calls) == before  # 한도를 넘으면 모델을 부르지 않는다
    assert not any(ch.isdigit() for ch in r.json()["message"])  # 남은 횟수·한도 숫자를 알리지 않는다
    assert "remaining" not in r.json() and "balance" not in r.json()


def test_each_client_has_its_own_daily_limit(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    assert chat(client, a).status_code == 200
    assert chat(client, a).status_code == 429
    assert chat(client, b).status_code == 200


def test_same_ip_has_a_daily_limit_across_new_client_ids(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 100)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 2)
    assert chat(client, str(uuid.uuid4())).status_code == 200
    assert chat(client, str(uuid.uuid4())).status_code == 200
    assert chat(client, str(uuid.uuid4())).status_code == 429  # 새 id 를 계속 만들어도 같은 주소는 막힌다


def test_failed_reply_does_not_use_up_the_daily_count(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    r = chat(client, cid, "fake:error")  # 가짜 LLM 이 답을 만들다 실패
    assert '"type": "error"' in r.text
    assert chat(client, cid).status_code == 200  # 센 것을 되돌렸으므로 한 번은 더 된다


def test_byok_and_crisis_are_not_counted(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    main.app.dependency_overrides[main.get_user_llm_factory] = lambda: (lambda key: FakeLLM(delay=0))
    for _ in range(2):  # 내 키는 한도 밖
        r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]},
                        headers={**hdr(cid), "X-User-LLM-Key": "sk-" + "a" * 40})
        assert r.status_code == 200
    crisis = next(w for w in ("죽고 싶어", "자살", "suicide", "kill myself") if main.coach.is_crisis(w))
    assert chat(client, cid, crisis).status_code == 200  # 위기 안내는 모델을 안 부르므로 세지 않는다
    assert chat(client, cid).status_code == 200  # 운영자 키 대화는 아직 한 번도 안 셌다
    assert chat(client, cid).status_code == 429


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
    o, r = pay_item(client, cid, "theme_notebook", toss)
    assert r.status_code == 200 and r.json()["kind"] == "item"
    assert store.balance(cid) == before  # 크레딧은 늘지 않는다
    assert client.get("/api/shop", headers=hdr(cid)).json()["owned"] == ["theme_notebook"]
    assert o["amount"] == creditlib.ITEMS["theme_notebook"]["amount"]


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
    pay_item(client, cid, "theme_cloud", toss)
    r = client.post("/api/orders", json={"productId": "theme_cloud"}, headers=hdr(cid))
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
    o, r = pay_item(client, cid, "theme_retro", toss)
    assert r.status_code == 400 and store.owned(cid) == []


def test_item_price_comes_from_server_table(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    o = order(client, cid, "theme_notebook")
    r = client.post("/api/payments/confirm", json={"paymentKey": "pk_y", "orderId": o["orderId"], "amount": "1"}, headers=hdr(cid))
    assert r.status_code == 400 and store.owned(cid) == [] and toss.calls == []


def test_quote_of_day_is_stable_per_day():
    import datetime
    d = datetime.date(2026, 11, 4)
    assert creditlib.quote_of_day(d) == creditlib.quote_of_day(d) and len(set(creditlib.QUOTES)) == len(creditlib.QUOTES)


# ---- 화면 기능 상품: 지난 기록 돌아보기, 도장 모양 바꾸기 ----
def test_feature_items_listed_with_description(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    items = {i["id"]: i for i in client.get("/api/shop", headers=hdr(cid)).json()["items"]}
    assert items["history_view"]["kind"] == "feature" and items["stamp_shapes"]["kind"] == "stamp"
    assert all(i["desc"] for k, i in items.items() if k != "daily_quote")  # 좋은 말은 화면이 예시 문장을 직접 보여 준다


def test_feature_item_purchase_grants_ownership_once(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    client.get("/api/credits", headers=hdr(cid))
    before = store.balance(cid)
    o, r = pay_item(client, cid, "history_view", toss)
    assert r.status_code == 200 and r.json()["kind"] == "item" and o["amount"] == creditlib.ITEMS["history_view"]["amount"]
    assert store.owned(cid) == ["history_view"] and store.balance(cid) == before
    again = client.post("/api/orders", json={"productId": "history_view"}, headers=hdr(cid))
    assert again.status_code == 409
    pay_item(client, cid, "stamp_shapes", toss)
    assert store.owned(cid) == ["history_view", "stamp_shapes"]


# ---- 열림 건너뛰기(3·28·60일째, 전체): 가격 구조와 소유 ----
def _unlocks():
    return [creditlib.ITEMS[k] for k in ("unlock_3", "unlock_28", "unlock_60")]


def test_unlock_prices_rise_and_all_is_cheaper_than_sum():
    a, b, c = _unlocks()
    assert a["amount"] < b["amount"] < c["amount"]  # 복잡해질수록 조금씩 비싸게(사용자 방향, 임시값)
    allp = creditlib.ITEMS["unlock_all"]["amount"]
    assert allp < a["amount"] + b["amount"] + c["amount"]  # 전체는 개별 합계보다 싸다
    assert [i["at"] for i in _unlocks()] == [3, 28, 60] and creditlib.ITEMS["unlock_all"]["at"] == 0


def test_unlock_purchase_grants_ownership_without_credits(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    client.get("/api/credits", headers=hdr(cid))
    before = store.balance(cid)
    o, r = pay_item(client, cid, "unlock_28", toss)
    assert r.status_code == 200 and o["amount"] == creditlib.ITEMS["unlock_28"]["amount"]
    assert store.owned(cid) == ["unlock_28"] and store.balance(cid) == before
    assert client.post("/api/orders", json={"productId": "unlock_28"}, headers=hdr(cid)).status_code == 409
    items = {i["id"]: i for i in client.get("/api/shop", headers=hdr(cid)).json()["items"]}
    assert items["unlock_all"]["kind"] == "unlock" and items["unlock_60"]["desc"]


# ---- 스티커 팩: 상품·소유, 화면의 그림 목록과 id 일치 ----
def test_sticker_packs_are_items_and_match_the_screen_list():
    packs = [i for i in creditlib.ITEMS.values() if i["kind"] == "sticker"]
    assert len(packs) == 8 and all(i["amount"] > 0 and i["desc"] for i in packs)
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    block = html[html.index("const STICKER_PACKS={"):html.index("const STICKERS_PER_DAY")]
    for i in packs:
        assert i["id"] + ":" in block  # 화면 STICKER_PACKS 에 같은 id 의 그림 목록이 있어야 한다


def test_sticker_purchase_grants_ownership(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    o, r = pay_item(client, cid, "sticker_round", toss)
    assert r.status_code == 200 and store.owned(cid) == ["sticker_round"]
    assert client.post("/api/orders", json={"productId": "sticker_round"}, headers=hdr(cid)).status_code == 409


# ---- 무료 하루 한도를 다 쓴 뒤에만 쓰이는 추가 대화권(크레딧) ----
def _buy_tickets(client, cid):
    o = order(client, cid, "credits_100")
    r = client.post("/api/payments/confirm", json={"paymentKey": "pk_" + uuid.uuid4().hex[:10], "orderId": o["orderId"],
                                                   "amount": str(o["amount"])}, headers=hdr(cid))
    assert r.status_code == 200


def test_limit_response_offers_to_buy_and_has_no_numbers(env, monkeypatch):
    client, store, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    assert chat(client, cid).status_code == 200
    r = chat(client, cid)
    assert r.status_code == 429 and r.json()["error"] == "daily_limit" and r.json()["canBuy"] is True
    assert not any(ch.isdigit() for ch in r.json()["message"]) and "balance" not in r.json()


def test_extra_tickets_are_used_only_after_the_free_limit(env, monkeypatch):
    client, store, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    _buy_tickets(client, cid)
    assert store.balance(cid) == 100
    assert chat(client, cid).status_code == 200 and store.balance(cid) == 100  # 무료 한도 안이라 대화권을 쓰지 않는다
    assert chat(client, cid).status_code == 200 and store.balance(cid) == 99   # 한도를 넘은 대화부터 1개씩


def test_failed_reply_gives_back_the_extra_ticket(env, monkeypatch):
    client, store, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    _buy_tickets(client, cid)
    assert chat(client, cid).status_code == 200  # 무료 한 번
    r = chat(client, cid, "fake:error")  # 대화권으로 시도했으나 답을 못 만듦
    assert '"type": "error"' in r.text
    assert store.balance(cid) == 100  # 되돌려졌다


def test_no_tickets_left_stops_again(env, monkeypatch):
    client, store, _ = env
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_DAY", 1)
    monkeypatch.setattr(creditlib, "CHAT_FREE_PER_IP_PER_DAY", 100)
    cid = str(uuid.uuid4())
    _buy_tickets(client, cid)
    for _ in range(98):  # 대화권을 2개만 남긴다(속도 제한 시험과 섞이지 않게 원장에서 직접 줄임)
        assert store.charge(cid, "chat:" + uuid.uuid4().hex)[0]
    assert store.balance(cid) == 2
    for _ in range(3):  # 무료 1번 + 대화권 2개
        assert chat(client, cid).status_code == 200
    assert store.balance(cid) == 0
    r = chat(client, cid)
    assert r.status_code == 429 and r.json()["canBuy"] is True


# ---- 할 일 아이콘 스타일 팩: 상품과 화면 id 일치, 그림 모양 정의 ----
def test_icon_packs_are_items_and_match_the_screen():
    packs = [i for i in creditlib.ITEMS.values() if i["kind"] == "iconpack"]
    assert len(packs) == 3 and all(i["amount"] > 0 and i["desc"] for i in packs)
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    block = html[html.index("const ICON_PACKS={"):html.index("const ICON_PREVIEW")]
    for i in packs:
        assert i["id"] + ":" in block
    glyphs = html[html.index("const GLYPHS={"):html.index("function glyphSVG")]
    for key in ("wake", "water", "walkrun", "read", "tooth", "orig", "origwin", "climb", "eng", "fa"):
        assert "\n" + key + ":" in glyphs  # 뜻이 불분명했던 그림과 새로 더한 그림의 모양 정의가 있다


def test_old_color_themes_are_free_and_new_design_themes_are_sold():
    ids = set(creditlib.ITEMS)
    assert not ({"theme_ocean", "theme_forest", "theme_rose"} & ids)  # 바다·숲·장미는 무료 색 테마라 상품이 아니다
    assert {"theme_notebook", "theme_retro", "theme_cloud"} <= ids
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    for tid in ("notebook", "retro", "cloud"):
        assert ":root[data-theme=\"" + tid + "\"]" in html  # 화면에 같은 id 의 디자인 CSS 가 있다
