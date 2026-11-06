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


SAMPLE_QUOTES = [
    {"ko": "천 리 길도 한 걸음부터.", "author": "한국 속담", "source": "견본", "source_url": "https://example.test/1", "verified": True},
    {"ko": "시작이 반이다.", "author": "한국 속담", "source": "견본", "source_url": "https://example.test/2", "verified": True},
]


def test_quote_requires_ownership_and_comes_from_the_quote_db(env):
    client, store, toss = env
    store.seed_quotes(SAMPLE_QUOTES)
    cid = str(uuid.uuid4())
    assert client.get("/api/quote", headers=hdr(cid)).status_code == 403
    pay_item(client, cid, "daily_quote", toss)
    r = client.get("/api/quote", headers=hdr(cid))
    j = r.json()
    import quotes
    pool = {q["ko"] for q in SAMPLE_QUOTES} | {q["ko"] for q in quotes.load_quotes()}  # 저장소가 quotes.json도 함께 싣는다
    assert r.status_code == 200 and j["text"] in pool and j["author"] and j["source_url"]
    assert client.get("/api/quote", headers=hdr(str(uuid.uuid4()))).status_code == 403  # 남의 소유는 쓸 수 없다


def test_quote_exclude_skips_recently_seen_and_sample_is_public(env):
    client, store, _ = env
    store.seed_quotes(SAMPLE_QUOTES)
    first = client.get("/api/quote/sample").json()  # 소유 확인 없이 미리 보기
    other = client.get("/api/quote/sample", params={"exclude": str(first["id"])}).json()
    assert other["id"] != first["id"]
    assert client.get("/api/quote/sample", params={"exclude": "1,2"}).status_code == 200  # 다 피하면 전체에서 뽑는다


def test_quote_file_has_only_verified_entries_with_sources():
    import quotes
    items = quotes.load_quotes()
    for i in items:
        assert i["verified"] is True and i["author"] and i["source"] and i["source_url"].startswith("http")
    assert len({(i["ko"], i["author"]) for i in items}) == len(items)  # 같은 문장이 두 번 들어 있지 않다


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



# ---- 화면 기능 상품: 지난 기록 돌아보기 (도장 모양 바꾸기는 2026-11-06 없앴다) ----
def test_feature_items_listed_with_description(env):
    client, store, toss = env
    cid = str(uuid.uuid4())
    items = {i["id"]: i for i in client.get("/api/shop", headers=hdr(cid)).json()["items"]}
    assert items["history_view"]["kind"] == "feature" and "stamp_shapes" not in items  # 도장 모양 상품은 없앴다
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
    again2 = client.post("/api/orders", json={"productId": "stamp_shapes"}, headers=hdr(cid))
    assert again2.status_code in (400, 404)  # 없앤 상품은 주문할 수 없다


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
    assert len(packs) == 21 and all(i["amount"] > 0 and i["desc"] for i in packs)
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
    assert not ({"theme_ocean", "theme_forest", "theme_peachpink", "theme_base"} & ids)  # 기본·복숭아·바다는 무료 색이라 상품이 아니다
    assert {"theme_notebook", "theme_retro", "theme_cloud"} <= ids
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    for tid in ("notebook", "retro", "cloud"):
        assert ":root[data-theme=\"" + tid + "\"]" in html  # 화면에 같은 id 의 디자인 CSS 가 있다


def test_space_and_donut_design_themes_are_sold_with_matching_css():
    assert {"theme_space", "theme_donut"} <= set(creditlib.ITEMS)
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    for tid in ("space", "donut"):
        assert ":root[data-theme=\"" + tid + "\"]" in html
    assert "--bg:#000;" in html and "%23ff7b1c" in html and "%232f7fa3" in html  # 우주 테마: 짙은 남색 바탕, 쨍한 주황 행성과 파란 행성 색이 들어 있다


def test_diary_dialog_and_button_exist_in_page():
    html = (Path(__file__).resolve().parents[2] / "index.html").read_text(encoding="utf-8")
    assert 'id="diaryBtn"' in html and 'id="diaryDlg"' in html and "S.diary" in html


def test_paper_bundles_are_two_of_four_and_css_for_each_paper():
    # 2026-11-06 사용자 결정: 메모지는 7종 한 묶음이 아니라 4종씩 두 번들
    assert "paper_pack" not in creditlib.ITEMS  # 옛 «7종»은 더 팔지 않는다(산 기록만 화면이 읽는다)
    bundles = {"paper_notes": ("lined", "grid", "dot", "biggrid"), "paper_mood": ("kraft", "sticky", "letter", "wash")}
    for bid in bundles:
        item = creditlib.ITEMS[bid]
        assert item["kind"] == "paper" and item["amount"] > 0 and item["desc"]
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    for bid, pids in bundles.items():
        assert len(pids) == 4 and f"{bid}:[" in html
        for pid in pids:
            assert f"{{id:'{pid}'" in html and f".paper-{pid}{{" in html  # 화면 목록과 CSS가 어긋나지 않는다


def test_all_prices_are_multiples_of_one_dollar_in_three_decor_tiers():
    # 2026-11-06 사용자 결정: 모든 가격은 1달러 기준(≈1,344원을 올림해 1,350원). 꾸미기는 1·2·3달러 세 가격대(단계 선물이 오래 지속할수록 더 비싼 팩을 주기 위해). 충전(대화권)은 그대로
    usd = 1350
    for k, v in creditlib.ITEMS.items():
        if v["kind"] != "unlock":
            assert v["amount"] in (usd, 2 * usd, 3 * usd), k
    tiers = {}
    for v in creditlib.ITEMS.values():
        if v["kind"] in creditlib.GIFT_KINDS:
            tiers.setdefault(v["amount"], []).append(v["id"])
    assert sorted(tiers) == [usd, 2 * usd, 3 * usd] and all(len(x) >= 5 for x in tiers.values())  # 가격대마다 선물로 뽑을 상품이 넉넉하다
    assert [creditlib.ITEMS[k]["amount"] for k in ("unlock_3", "unlock_28", "unlock_60", "unlock_all")] == [usd, 2 * usd, 3 * usd, 5 * usd]
    assert {k: v["amount"] for k, v in creditlib.PRODUCTS.items()} == {"credits_100": 1000, "credits_550": 5000, "credits_1200": 10000}


def test_stage_gift_gets_pricier_the_longer_you_keep_going(env):
    client, store, _ = env
    assert creditlib.GIFT_STAGE_TIER == {3: 1350, 28: 2700, 60: 4050}
    for _ in range(8):  # 무작위라 여러 번 시험해도 항상 그 단계의 가격대다(요청 횟수 제한을 피해 저장소를 직접 부른다)
        cid = str(uuid.uuid4())
        got = [store.stage_gift(cid, st)["item"]["amount"] for st in (3, 28, 60)]
        assert got == [1350, 2700, 4050]
    j = client.post("/api/gift", json={"stage": 3}, headers=hdr(str(uuid.uuid4()))).json()
    assert j["item"]["amount"] == 1350  # 화면이 «N원 상당»으로 보여 주도록 응답에도 가격이 있다


def test_stage_gift_falls_back_to_nearest_lower_tier_when_tier_is_owned(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    conn = store._conn()
    for i in creditlib.ITEMS.values():  # 60일 가격대(3달러)를 모두 가진 사람
        if i["kind"] in creditlib.GIFT_KINDS and i["amount"] == 4050:
            conn.execute("INSERT INTO entitlements(client_id, item_id, order_id, created_at) VALUES (?,?,?,?)", (cid, i["id"], "t", creditlib.now()))
    conn.close()
    assert client.post("/api/gift", json={"stage": 60}, headers=hdr(cid)).json()["item"]["amount"] == 2700  # 가까운 낮은 가격대


def test_roadmap_is_on_main_screen_not_in_shop():
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    assert 'id="roadStrip"' in html and 'id="roadDlg"' in html  # 메인 맨 위 띠와 전체 로드맵 창
    assert 'id="roadmap"' not in html[html.index('id="crDlg"'):html.index('data-t="chat"')]  # 상점 안에는 로드맵이 없다
    assert 'id="goalCard"' not in html  # 아래쪽 성장 단계 카드는 띠로 합쳤다


def test_stage_gift_once_per_stage_random_decor_only(env):
    client, store, _ = env
    cid = str(uuid.uuid4())
    assert client.post("/api/gift", json={"stage": 5}, headers=hdr(cid)).status_code == 400  # 단계가 아니면 거절
    r = client.post("/api/gift", json={"stage": 3}, headers=hdr(cid))
    j = r.json()
    assert r.status_code == 200 and j["already"] is False and j["item"]["kind"] in creditlib.GIFT_KINDS
    assert j["item"]["id"] in store.owned(cid)  # 선물은 소유로 기록된다
    again = client.post("/api/gift", json={"stage": 3}, headers=hdr(cid)).json()
    assert again["already"] is True and again["item"]["id"] == j["item"]["id"]  # 같은 단계는 한 번만
    assert len(store.owned(cid)) == 1
    second = client.post("/api/gift", json={"stage": 28}, headers=hdr(cid)).json()
    assert second["item"]["id"] != j["item"]["id"]  # 이미 가진 것은 뽑지 않는다


def test_stage_gift_pool_excludes_features_and_skips_when_everything_owned(env):
    client, store, _ = env
    assert all(i["kind"] in ("sticker", "iconpack", "paper", "theme") for i in creditlib.ITEMS.values() if i["kind"] in creditlib.GIFT_KINDS)
    assert not any(i["kind"] in creditlib.GIFT_KINDS for i in creditlib.ITEMS.values() if i["id"] in ("daily_quote", "history_view", "unlock_3"))
    cid = str(uuid.uuid4())
    pool = [i["id"] for i in creditlib.ITEMS.values() if i["kind"] in creditlib.GIFT_KINDS]
    for _ in range(3):
        client.post("/api/gift", json={"stage": 3}, headers=hdr(cid))  # 같은 단계 반복은 한 개만 준다
    assert len(store.owned(cid)) == 1
    # 다 가진 사람에게는 줄 것이 없어 item 이 None
    c2 = str(uuid.uuid4())
    conn = store._conn()
    for iid in pool:
        conn.execute("INSERT INTO entitlements(client_id, item_id, order_id, created_at) VALUES (?,?,?,?)", (c2, iid, "t", creditlib.now()))
    conn.close()
    assert client.post("/api/gift", json={"stage": 60}, headers=hdr(c2)).json()["item"] is None


def test_paid_colors_are_sold_and_free_colors_are_only_three():
    colors = ("peach", "rose", "lime", "lavender", "sunny")
    for c in colors:
        it = creditlib.ITEMS["theme_" + c]
        assert it["kind"] == "theme" and it["theme"] == c and it["amount"] == 1350 and it["desc"]
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    start = html.index("const THEMES=[")
    block = html[start:html.index("let OWNED=new Set()", start)]
    for c in colors:
        assert "{id:'%s',shop:'theme_%s',col:1}" % (c, c) in block  # 화면에서도 유료 색으로 묶여 있다
        assert ':root[data-theme="' + c + '"]' in html
    assert block.count("col:1}") == 8 and block.count("shop:") == 10  # 색 8개(무료 3 + 유료 5), 유료 상품 10개(색 5 + 디자인 5)
    for free in ("base", "peachpink", "ocean"):
        assert "{id:'%s',col:1}" % free in block
    assert "at:" not in block  # 일수로 열리는 색은 없다


def test_unlock_items_do_not_mention_colors_and_stamp_shapes_are_gone():
    for k in ("unlock_28", "unlock_60", "unlock_all"):
        it = creditlib.ITEMS[k]
        assert "색" not in it["name"] + it["desc"]
    assert creditlib.ITEMS["unlock_28"]["amount"] == 2700 and creditlib.ITEMS["unlock_60"]["amount"] == 4050
    assert "stamp_shapes" not in creditlib.ITEMS and not any(i["kind"] == "stamp" for i in creditlib.ITEMS.values())
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    for gone in ("shapeRow", "SHAPES", "currentShape", "data-shape", "themePills", "themeCap", "nextcolor"):
        assert gone not in html


def test_sticker_pack_sizes_ids_and_symbols():
    import re
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    block = html[html.index("const STICKER_PACKS={"):html.index("const HL_NAMES")]
    seen = []
    for m in re.finditer(r"(sticker_\w+):\{name:'[^']*',list:\[([^\]]*)\]", block):
        pid, items = m.group(1), re.findall(r"'([a-z]+:[a-z0-9_]+)'", m.group(2))
        assert len(items) >= (12 if pid == "sticker_highlight" else 16), pid
        n = re.search(r"(\d+)(?:개|가지)", creditlib.ITEMS[pid]["desc"])
        if n:
            assert int(n.group(1)) == len(items), pid  # 상품 설명의 개수 = 화면 목록 개수
        seen += items
    assert len(seen) == len(set(seen))  # 팩끼리 id 충돌 없음
    for s in seen:
        if s.startswith("sv:"):
            assert f'<symbol id="sv-{s[3:]}"' in html and f'"{s[3:]}":' in html  # 그림과 이름이 있어야 한다
        elif s.startswith("ig:"):  # 아이콘 팩 글리프(2026-11-06 아이콘·스티커 통합): 스타일과 글리프 키가 화면에 있어야 한다
            style, key = s[3:].split("_")
            assert style in ("cute", "simple", "pastel") and f"\n{key}:{{p:" in html, s
        else:
            assert f".hl-{s[3:]}{{" in html or f".hl-{s[3:]}," in html


def test_icon_and_sticker_are_merged_in_the_screen():
    # 2026-11-06 사용자 결정: 아이콘과 스티커는 기능도 합친다 — 산 스티커·아이콘을 칸 그림으로 고르고, 아이콘 팩 글리프를 붙이는 스티커로도 쓴다
    html = (Path(__file__).resolve().parent.parent.parent / "index.html").read_text(encoding="utf-8")
    block = html[html.index("const STICKER_PACKS={"):html.index("const STICKERS_PER_DAY")]
    for pid in ("icons_cute", "icons_simple", "icons_pastel"):
        assert pid + ":" in block and creditlib.ITEMS[pid]["kind"] == "iconpack"  # 기존 아이콘 팩 상품과 같은 id 라 산 사람은 그대로 스티커로도 쓴다
    assert "if(b.dataset.a){s.art=b.dataset.a" in html and "내 스티커·아이콘" in html  # 칸 그림 고르기에 산 그림이 나온다
    assert "if(s.art){const a=artSVG(s.art" in html  # 칸 그림이 s.art 를 그린다


def test_affirmations_cover_every_ui_language_and_api_uses_lang(env):
    # 2026-11-06 사용자 결정: 오늘의 한마디는 격언 대신 일상 응원 문장, 언어별로
    import quotes
    d = quotes.load_affirmations()
    for lang in ("ko", "en", "zh-Hans", "zh-Hant", "yue", "id", "vi", "es", "fi", "sv"):
        assert len(d[lang]) >= 16 and len(set(d[lang])) == len(d[lang]), lang
    client, store, toss = env[0], env[1], env[2]
    r = client.get("/api/quote/sample", params={"lang": "sv"}).json()
    assert r["text"] in d["sv"] and r["id"] >= 1
    r2 = client.get("/api/quote/sample", params={"lang": "xx", "exclude": "1"}).json()  # 모르는 언어는 영어
    assert r2["text"] in d["en"] and r2["id"] != 1
