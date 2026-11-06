"""루틴 도장 서버: 대화형 도우미(루틴 코치 친구). 서버는 상태를 갖지 않는다.

- GET  /          : 앱 화면(../index.html). 화면과 API 가 같은 주소라 CORS 가 필요 없다.
- GET  /health    : 상태 확인
- POST /api/stamp : 루틴 이름 → {"svg": 정리된 SVG}. 대화와 별도의 더 빡빡한 속도 제한(stamp.py 가 SVG 를 정리한다)
- POST /api/feedback : 의견 글 → 만든 사람 메일로 전달(feedback.py). 저장하지 않고 본문을 로그에 남기지 않는다. 오류: 400 empty / 429 busy / 503 notConfigured / 502 failed
- POST /api/chat  : 최근 대화 + (사용자가 허락한) 칸 이름·일수 + 할 일 목록 → 도우미의 답. NDJSON 이벤트로 스트리밍한다.
    이벤트: mode{mode} / notice{key} / delta{text} / done{ok,mode,cards} / crisis / scope / error
    화면은 done 을 받지 못하거나 ok 가 false 이면 그 답을 버린다.

흐름: ① 입력 정리·위기 키워드 검사(걸리면 모델을 부르지 않음) → ② 짧은 비스트리밍 호출로 모드와 근거 카드 id 를 고름 →
      ③ 서버가 카드 id 가 실제 있는 카드인지 검사 → ④ 선택된 카드 본문만 넣고 답을 스트리밍 → ⑤ 끝나고 숫자 검사.
대화·할 일은 저장하지도 로그에 남기지도 않는다(오류 종류만 남긴다). 도장 날짜별 기록은 받지 않는다.
환경변수: LLM_PROVIDER(기본 fake) LLM_API_KEY LLM_MODEL. 키는 코드·화면에 넣지 않고 서버 환경(Secret Manager 등)에만 둔다.

크레딧·결제(CREDITS=on 일 때만, 로컬 시험용 SQLite: credits.py). 끄면(기본) 위 동작 그대로다.
- 화면은 localStorage 의 무작위 UUID 를 X-Client-Id 헤더로 보낸다(계정 없음). 처음 보는 id 는 무료 크레딧을 받는다.
- /api/chat 은 운영자 키로 모델을 부르기 전에 서버에서만 1개 차감(사용자 키 BYOK 는 차감 없음), 모자라면 402 insufficient_credits.
- GET /api/credits · GET /api/products · POST /api/orders · GET /api/orders/{id} · POST /api/payments/confirm · POST /api/payments/fail
- GET /api/config : 토스페이먼츠 클라이언트 키(test_ 만)와 크레딧 켜짐 여부. 시크릿 키는 내려 주지 않는다.
- GET /pay · /pay/success · /pay/fail : ../pay.html (결제위젯·성공·실패 화면)
- 크레딧을 늘리는 곳: 결제 승인 성공(confirm_payment → Store.complete_order), 가입 무료 지급, 실패한 답의 되돌림.
"""
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

import byok
import cards as cardlib
import coach
import credits as creditlib
import feedback
import llm as llm_module
import stamp
import toss
import tracing
from llm import make_llm

PAGE = Path(__file__).resolve().parent.parent / "index.html"
PAY_PAGE = Path(__file__).resolve().parent.parent / "pay.html"
RATE_PER_IP = int(os.environ.get("RATE_PER_IP_PER_MIN", "20"))
RATE_ALL = int(os.environ.get("RATE_ALL_PER_MIN", "120"))
RATE_STAMP_PER_IP = int(os.environ.get("RATE_STAMP_PER_IP_PER_MIN", "5"))   # 도장 그림은 비용이 커서 훨씬 빡빡하다
RATE_STAMP_ALL = int(os.environ.get("RATE_STAMP_ALL_PER_MIN", "30"))
RATE_FEEDBACK_PER_IP = int(os.environ.get("RATE_FEEDBACK_PER_IP_PER_MIN", "3"))   # 의견 메일은 스팸이 되기 쉬워 빡빡하다
RATE_FEEDBACK_ALL = int(os.environ.get("RATE_FEEDBACK_ALL_PER_MIN", "20"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("coach")

app = FastAPI(title="루틴 도장")
BYOK_MODE = byok.parse_mode(os.environ.get("BYOK_MODE"))  # optional(기본) | required
PROVIDER = os.environ.get("LLM_PROVIDER", "fake").strip().lower()
_operator_key = os.environ.get("LLM_API_KEY", "").strip()
# required 에서는 운영자 키 없이도 시작할 수 있다(운영자 키를 아예 쓰지 않으므로)
_llm = None if (BYOK_MODE == "required" and PROVIDER != "fake" and not _operator_key) else make_llm(PROVIDER, _operator_key, os.environ.get("LLM_MODEL", "").strip())
_hits = defaultdict(deque)  # 이 인스턴스 안에서만 세는 간단한 속도 제한(인스턴스가 여러 개면 합쳐지지 않는다)


def get_llm():
    """테스트에서는 이 함수를 바꿔 끼운다."""
    return _llm


def build_user_llm(key):
    """사용자 키로 만든 LLM 객체. 요청마다 새로 만들고 캐시하지 않는다. 제공사는 키의 모양으로 고르고(byok.provider_for) 모델은 그 제공사의 기본값이다.
    고른 제공사는 로그·응답에 남기지 않는다. 운영자 키 경로(헤더 없음)는 이 함수를 쓰지 않고 LLM_PROVIDER 그대로다.
    LLM_PROVIDER=fake(로컬 시험)에서는 키를 쓰지 않고 가짜 LLM 을 돌려준다."""
    return make_llm("fake" if PROVIDER == "fake" else byok.provider_for(key), key, "")


def get_user_llm_factory():
    """테스트에서는 이 함수를 바꿔 끼운다."""
    return build_user_llm


CREDITS_ON = os.environ.get("CREDITS", "off").strip().lower() == "on"
_store = None


def get_credit_store():
    """크레딧 원장(켜졌을 때만, 아니면 None). 테스트에서는 이 함수를 바꿔 끼운다(임시 파일 DB)."""
    global _store
    if not CREDITS_ON:
        return None
    if _store is None:
        _store = creditlib.Store(os.environ.get("CREDIT_DB", "").strip() or creditlib.DEFAULT_DB)
    return _store


def get_toss_confirm():
    """토스페이먼츠 결제 승인 API 호출 함수. 테스트에서는 가짜로 바꿔 끼운다."""
    return toss.confirm


def client_id_of(request):
    return creditlib.valid_client_id(request.headers.get("x-client-id"))


def credits_off():
    return JSONResponse({"error": "creditsOff"}, status_code=404)


def pick_llm(raw_key, operator_llm, factory):
    """(쓸 LLM, 사용자 키로 부르는가, 오류 키). 헤더가 있으면 그 키로, 없으면 optional 에서만 운영자 키.
    사용자 키가 틀리거나 한도에 걸려도 운영자 키로 몰래 대신 부르지 않는다."""
    key = (raw_key or "").strip()
    if key:
        if not byok.valid(key):
            return None, True, "keyInvalid"
        try:
            return factory(key), True, None
        except Exception as error:  # 키 글자는 남기지 않고 오류 종류만 남긴다
            log.warning("user llm build failed: %s", type(error).__name__)
            return None, True, "keyInvalid"
    if BYOK_MODE == "required" or operator_llm is None:
        return None, False, "keyMissing"
    return operator_llm, False, None


def limited(ip, scope="chat", per_ip=None, per_all=None):
    """scope 별로 따로 센다(도장 그림은 대화보다 훨씬 빡빡하다)."""
    per_ip = RATE_PER_IP if per_ip is None else per_ip
    per_all = RATE_ALL if per_all is None else per_all
    now = time.time()
    keys = ((scope, ip, per_ip), (scope, "*", per_all))
    for key in keys:
        q = _hits[key[:2]]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= key[2]:
            return True
    for key in keys:
        _hits[key[:2]].append(now)
    return False


def client_ip(request):
    return (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()


class Msg(BaseModel):
    role: str = ""
    content: str = ""


class ChatRequest(BaseModel):
    messages: list[Msg] = []
    context: dict | None = None   # 사용자가 보여 주기로 한 칸 이름·일수. 허락하지 않았으면 None
    todos: list[str] = []
    character: Any = None  # (dict 가 아니면 설정 없음으로 본다) 선택: {"name": ≤20자, "speech": "casual"|"polite", "emoji": "none"|"some"|"often"}. 없으면 기본 동작


def line(event):
    return json.dumps(event, ensure_ascii=False) + "\n"


@app.get("/")
def home():
    return FileResponse(PAGE, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/pay")
@app.get("/pay/success")
@app.get("/pay/fail")
def pay_page():
    return FileResponse(PAY_PAGE, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})


@app.get("/api/config")
def config(store=Depends(get_credit_store)):
    """화면에 내려 주는 설정: 크레딧 켜짐 여부와 클라이언트 키(드러나도 되는 값)뿐. 시크릿 키는 절대 넣지 않는다."""
    return JSONResponse({"credits": store is not None, "tossClientKey": toss.client_key()}, headers={"Cache-Control": "no-store"})


@app.get("/api/products")
def products(store=Depends(get_credit_store)):
    if store is None:
        return credits_off()
    return {"products": list(creditlib.PRODUCTS.values()), "chatCost": creditlib.CHAT_COST}


@app.get("/api/credits")
def get_credits(request: Request, store=Depends(get_credit_store)):
    """잔액과 최근 기록 10줄. 처음 보는 client_id 면 무료 크레딧을 먼저 쌓는다."""
    if store is None:
        return credits_off()
    cid = client_id_of(request)
    if not cid:
        return JSONResponse({"error": "clientId"}, status_code=400)
    return JSONResponse({"balance": store.balance(cid), "recent": store.recent(cid, 10), "owned": store.owned(cid)},
                        headers={"Cache-Control": "no-store"})


@app.get("/api/shop")
def shop(request: Request, store=Depends(get_credit_store)):
    """상점: 일회 구매 상품(영구 소유)과 내가 가진 것. 도우미 대화용 크레딧 상품은 /api/products 로 따로 준다."""
    if store is None:
        return credits_off()
    cid = client_id_of(request)
    if not cid:
        return JSONResponse({"error": "clientId"}, status_code=400)
    return JSONResponse({"items": list(creditlib.ITEMS.values()), "owned": store.owned(cid)}, headers={"Cache-Control": "no-store"})


def _exclude(request: Request):
    return [x for x in request.query_params.get("exclude", "").split(",") if x.strip().isdigit()][:50]


@app.get("/api/quote")
def quote(request: Request, store=Depends(get_credit_store)):
    """오늘의 한마디: 실제 격언·속담 DB 에서 무작위 한 개(exclude=최근에 본 id 들은 피함). «오늘의 한마디» 상품을 산 사람에게만 준다(서버가 소유를 확인)."""
    if store is None:
        return credits_off()
    cid = client_id_of(request)
    if not cid:
        return JSONResponse({"error": "clientId"}, status_code=400)
    if not store.has_item(cid, "daily_quote"):
        return JSONResponse({"error": "not_owned"}, status_code=403)
    q = store.random_quote(_exclude(request))
    if q is None:
        return JSONResponse({"error": "no_quotes"}, status_code=503)
    return JSONResponse(q, headers={"Cache-Control": "no-store"})


@app.get("/api/quote/sample")
def quote_sample(request: Request, store=Depends(get_credit_store)):
    """사기 전 미리 보기용 무작위 격언 하나(소유 확인 없음, 같은 DB 에서 뽑는다)."""
    if store is None:
        return credits_off()
    if limited(client_ip(request), "quote-sample", 30, 60):
        return JSONResponse({"error": "busy"}, status_code=429)
    q = store.random_quote(_exclude(request))
    if q is None:
        return JSONResponse({"error": "no_quotes"}, status_code=503)
    return JSONResponse(q, headers={"Cache-Control": "no-store"})


class GiftRequest(BaseModel):
    stage: int = 0


@app.post("/api/gift")
def stage_gift(req: GiftRequest, request: Request, store=Depends(get_credit_store)):
    """도장 단계(3·28·60일)를 지났을 때 꾸미기 팩 하나를 무작위로 준다(단계당 한 번, 같은 단계를 다시 부르면 처음 받은 것을 돌려준다)."""
    if store is None:
        return credits_off()
    cid = client_id_of(request)
    if not cid:
        return JSONResponse({"error": "clientId"}, status_code=400)
    if req.stage not in creditlib.GIFT_STAGES:
        return JSONResponse({"error": "stage"}, status_code=400)
    if limited(client_ip(request), "gift", 10, 60):
        return JSONResponse({"error": "busy"}, status_code=429)
    g = store.stage_gift(cid, req.stage)
    it = g["item"]
    return JSONResponse({"item": {"id": it["id"], "name": it["name"], "kind": it["kind"], "amount": it["amount"]} if it else None, "already": g["already"]},
                        headers={"Cache-Control": "no-store"})


class OrderRequest(BaseModel):
    productId: str = ""


@app.post("/api/orders")
def create_order(req: OrderRequest, request: Request, store=Depends(get_credit_store)):
    """상품 ID만 받는다. 금액·크레딧은 서버 상품표에서 찾는다(화면이 보낸 금액은 쓰지 않음)."""
    if store is None:
        return credits_off()
    cid = client_id_of(request)
    if not cid:
        return JSONResponse({"error": "clientId"}, status_code=400)
    if limited(client_ip(request), "orders", 10, 60):
        return JSONResponse({"error": "busy"}, status_code=429)
    product = creditlib.PRODUCTS.get(req.productId) or creditlib.ITEMS.get(req.productId)
    if not product:
        return JSONResponse({"error": "unknown_product"}, status_code=400)
    if product["id"] in creditlib.ITEMS and store.has_item(cid, product["id"]):
        return JSONResponse({"error": "already_owned"}, status_code=409)  # 일회 구매 상품은 한 번만 산다
    o = store.create_order(cid, product)
    return JSONResponse({"orderId": o["order_id"], "amount": o["amount"], "credits": o["credits"], "orderName": product["name"]},
                        headers={"Cache-Control": "no-store"})


@app.get("/api/orders/{order_id}")
def read_order(order_id: str, request: Request, store=Depends(get_credit_store)):
    """결제 화면이 금액을 서버에서 다시 읽는다(주소의 값을 믿지 않음). 내 주문만."""
    if store is None:
        return credits_off()
    o = store.get_order(order_id)
    if not o or o["client_id"] != client_id_of(request):
        return JSONResponse({"error": "order_not_found"}, status_code=404)
    return JSONResponse({"orderId": o["order_id"], "amount": o["amount"], "credits": o["credits"], "status": o["status"],
                         "orderName": (creditlib.PRODUCTS.get(o["product_id"]) or creditlib.ITEMS.get(o["product_id"]) or {}).get("name", o["product_id"]),
                         "kind": "item" if o["product_id"] in creditlib.ITEMS else "credits"},
                        headers={"Cache-Control": "no-store"})


class ConfirmRequest(BaseModel):
    paymentKey: str = ""
    orderId: str = ""
    amount: Any = None


def _done_result(store, o, already):
    return JSONResponse({"ok": True, "already": already, "orderId": o["order_id"], "credits": o["credits"],
                         "kind": "item" if o["product_id"] in creditlib.ITEMS else "credits",
                         "itemName": creditlib.ITEMS.get(o["product_id"], {}).get("name"),
                         "approvedAt": o["approved_at"], "balance": store.balance(o["client_id"])}, headers={"Cache-Control": "no-store"})


@app.post("/api/payments/confirm")
def confirm_payment(req: ConfirmRequest, request: Request, store=Depends(get_credit_store), confirm=Depends(get_toss_confirm)):
    """성공 페이지가 주소의 paymentKey·orderId·amount 를 보낸다. 결제로 크레딧을 늘리는 곳은 여기(승인 성공 뒤) 한 곳이다.
    ① 내 주문인가 ② 이미 완료면 첫 결과 그대로(승인 API 다시 안 부름) ③ 대기인가 ④ 금액이 저장한 금액과 같은가
    → 토스 승인(Idempotency-Key = order_id) → 성공이면 한 트랜잭션에서 주문 완료 + 원장 +credits(ref order:<id>)."""
    if store is None:
        return credits_off()
    cid = client_id_of(request)
    o = store.get_order(req.orderId)
    if not cid or not o or o["client_id"] != cid:
        return JSONResponse({"error": "order_not_found"}, status_code=404)
    if o["status"] == "done":
        return _done_result(store, o, True)
    if o["status"] != "pending":
        return JSONResponse({"error": "order_failed", "code": o["fail_code"]}, status_code=409)
    if str(req.amount).strip() != str(o["amount"]):
        log.warning("confirm rejected orderId=%s reason=amount_mismatch", o["order_id"])
        return JSONResponse({"error": "amount_mismatch"}, status_code=400)
    payment_key = str(req.paymentKey or "").strip()
    if not payment_key or len(payment_key) > 200:
        return JSONResponse({"error": "bad_payment_key"}, status_code=400)
    result = confirm(payment_key, o["order_id"], o["amount"], o["order_id"])
    body = result.get("body") or {}
    if not result.get("ok"):
        code = str(body.get("code") or "UNKNOWN")
        if code in ("NOT_CONFIGURED", "NETWORK_ERROR", "IDEMPOTENT_REQUEST_PROCESSING"):
            # 승인이 됐는지 모르는(또는 아직 못 부른) 상태 → 주문을 실패로 바꾸지 않고 대기로 둔다(같은 키로 다시 시도)
            return JSONResponse({"error": "confirm_unavailable", "code": code, "message": str(body.get("message", ""))[:200]}, status_code=503)
        store.fail_order(o["order_id"], code)
        return JSONResponse({"error": "payment_failed", "code": code, "message": str(body.get("message", ""))[:200]}, status_code=400)
    if body.get("orderId") not in (None, o["order_id"]) or body.get("totalAmount") not in (None, o["amount"]):
        log.error("confirm response mismatch orderId=%s", o["order_id"])  # 응답이 주문과 다르면 크레딧을 주지 않는다
        return JSONResponse({"error": "confirm_mismatch"}, status_code=502)
    approved_at = str(body.get("approvedAt") or creditlib.now())
    first = store.complete_order(o["order_id"], payment_key, approved_at)
    log.info("order completed orderId=%s credited=%s", o["order_id"], first)
    return _done_result(store, store.get_order(o["order_id"]), not first)


class FailRequest(BaseModel):
    orderId: str = ""
    code: str = ""


@app.post("/api/payments/fail")
def payment_failed(req: FailRequest, request: Request, store=Depends(get_credit_store)):
    """실패 페이지가 부른다: 내 대기 주문을 실패로(크레딧은 그대로)."""
    if store is None:
        return credits_off()
    o = store.get_order(req.orderId)
    if not o or o["client_id"] != client_id_of(request):
        return JSONResponse({"error": "order_not_found"}, status_code=404)
    return {"ok": True, "changed": store.fail_order(o["order_id"], req.code or "FAIL_PAGE")}


class StampRequest(BaseModel):
    name: str = ""


@app.post("/api/stamp")
def stamp_picture(req: StampRequest, request: Request, model=Depends(get_llm), factory=Depends(get_user_llm_factory)):
    """루틴 이름 → {"svg": "<svg ...>"} (정리된 SVG 한 개, viewBox 0 0 64 64, 16000자 이하).
    오류: 400 empty(이름 없음) / 422 refused(위기 표현) / 429 busy(한도) / 502 failed(모델 실패·읽을 수 없는 그림) /
    401 keyMissing·keyInvalid(BYOK 키 없음·틀림) / 429 keyLimit(사용자 키의 한도·결제 문제)."""
    if limited(client_ip(request), "stamp", RATE_STAMP_PER_IP, RATE_STAMP_ALL):
        return JSONResponse({"error": "busy"}, status_code=429)
    engine, user_key, key_error = pick_llm(request.headers.get(byok.HEADER), model, factory)
    if key_error:
        return JSONResponse({"error": key_error}, status_code=429 if key_error == "keyLimit" else 401)
    name = stamp.clean_name(req.name)
    if not name:
        return JSONResponse({"error": "empty"}, status_code=400)
    if coach.is_crisis(req.name):  # 위기 표현이면 그리지 않는다(모델에 보내지 않음)
        return JSONResponse({"error": "refused"}, status_code=422)
    try:
        raw = engine.complete_text(stamp.build_messages(name), llm_module.SVG_TOKENS)
    except Exception as error:  # 이름·응답·키는 남기지 않고 오류 종류만 남긴다(제공사 오류 문구는 읽지도 돌려주지도 않는다)
        log.error("stamp failed: %s", type(error).__name__)
        key_error = byok.classify_error(error) if user_key else None
        if key_error:
            return JSONResponse({"error": key_error}, status_code=429 if key_error == "keyLimit" else 401)
        return JSONResponse({"error": "failed"}, status_code=502)
    svg = stamp.clean_svg(raw)
    if not svg:
        return JSONResponse({"error": "failed"}, status_code=502)
    return JSONResponse({"svg": svg}, headers={"Cache-Control": "no-store"})


class FeedbackRequest(BaseModel):
    text: str = ""
    stats: str = ""


@app.post("/api/feedback")
def send_feedback(req: FeedbackRequest, request: Request):
    """의견 한 통을 메일로 보낸다. 성공 {"ok": true}."""
    if limited(client_ip(request), "feedback", RATE_FEEDBACK_PER_IP, RATE_FEEDBACK_ALL):
        return JSONResponse({"error": "busy"}, status_code=429)
    text = feedback.clean(req.text, feedback.MAX_TEXT)
    if not text:
        return JSONResponse({"error": "empty"}, status_code=400)
    if not feedback.configured():
        return JSONResponse({"error": "notConfigured"}, status_code=503)
    try:
        feedback.send(text, req.stats)
    except Exception as error:  # 글·계정·비밀번호는 남기지 않고 오류 종류만 남긴다
        log.error("feedback failed: %s", type(error).__name__)
        return JSONResponse({"error": "failed"}, status_code=502)
    return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})


@app.post("/api/chat")
def chat(req: ChatRequest, request: Request, model=Depends(get_llm), factory=Depends(get_user_llm_factory), store=Depends(get_credit_store)):
    if limited(client_ip(request)):
        return JSONResponse({"error": "busy"}, status_code=429)
    history = coach.clean_history([m.model_dump() for m in req.messages])
    if not history:
        return JSONResponse({"error": "empty"}, status_code=400)
    ctx, todos = coach.clean_context(req.context), coach.clean_todos(req.todos)
    character = coach.clean_character(req.character)
    last = history[-1]["content"]
    raw_key = request.headers.get(byok.HEADER)
    engine, user_key, pick_error = pick_llm(raw_key, model, factory)
    # 하루 한도: 도우미 대화는 무료이고, 운영자 키로 모델을 부를 때만 부르기 전에 서버에서 하루 횟수를 센다
    # (위기 키워드는 모델을 안 부르므로 세지 않고, 내 키(BYOK)도 세지 않는다). 남은 횟수는 알려 주지 않는다.
    cid, charge_ref, outcome = None, None, {"refund": False}
    if store is not None:
        cid = client_id_of(request)
        if not cid:
            return JSONResponse({"error": "clientId"}, status_code=400)
        if not pick_error and not user_key and not coach.is_crisis(last):
            taken = store.chat_take(cid, client_ip(request))
            if taken is not None:
                charge_ref = ("free", taken)
            else:  # 하루 무료 한도를 다 썼으면 산 추가 대화권(원장)에서 1개를 쓴다. 없으면 모델을 부르지 않고 안내만 한다(남은 숫자는 알리지 않음)
                ref = "chat:" + uuid.uuid4().hex
                charged, _bal = store.charge(cid, ref)
                if not charged:
                    return JSONResponse({"error": "daily_limit", "canBuy": True,
                                         "message": "오늘의 무료 대화를 모두 썼어요. 내일 다시 이야기하거나, 추가 대화권을 사서 계속 이야기할 수 있어요. 설정에서 내 API 키를 넣어도 돼요. 도장 찍기는 그대로 쓸 수 있어요."},
                                        status_code=429)
                charge_ref = ("credit", ref)

    def events():
        turn = tracing.start_turn()  # 한 턴 = 트레이스 하나(chat-turn). 키가 없으면 아무 일도 하지 않는다
        try:
            yield from run(turn)
        except Exception:
            outcome["refund"] = True
            raise
        finally:
            turn.end()
            tracing.flush(turn)
            if charge_ref and outcome["refund"]:  # 답을 만들지 못했으면 센 것을 되돌린다(사용자가 연결을 끊은 경우는 되돌리지 않음)
                kind, ref = charge_ref
                if kind == "free":
                    store.chat_give_back(ref)
                else:
                    store.refund(cid, ref)

    def run(turn):
        key_error = pick_error  # (run 안에서 다시 정하므로 지역 이름으로 받는다)
        turn.update(input=tracing.text(last))  # 트레이스 입력은 사용자 말 하나(원문 수집을 켠 경우만, 기본은 비어 있음)
        safety = turn.child("check-safety", "guardrail")
        crisis = coach.is_crisis(last)
        safety.end(output={"crisis": crisis})
        if crisis:  # 모델에 보내지 않는다
            turn.update(output={"result": "crisis", "by": "keyword"})
            yield line({"type": "crisis"})
            return
        turn.update(metadata={"byok": user_key})
        if key_error:  # 키가 없거나 형식이 틀림: 운영자 키로 대신 부르지 않고 안내만
            turn.update(output={"result": "key-error"})
            yield line({"type": "error", "key": key_error})
            return
        try:
            system, user, plan_prompt = coach.plan_messages_with_prompt(history)
            # 가져온 Langfuse 프롬프트를 연결하면 트레이스에 지시문 이름·버전이 보인다(가져오지 못했으면 None, 코드의 문장으로 답함)
            plan_obs = turn.child("choose-mode", "generation", model=getattr(engine, "model", None), input=tracing.text(user),
                                  **({"prompt": plan_prompt} if plan_prompt is not None else {}))
            plan_usage = {}  # 토큰 수(Langfuse 가 모델 가격표로 비용을 계산한다)
            try:
                plan = engine.complete_json(system, user, **tracing.usage_kw(engine.complete_json, plan_usage))
            except Exception as error:  # 계획 단계가 실패해도 듣기 모드로 이어 간다(사용자 키 문제면 안내하고 끝낸다)
                log.warning("plan failed: %s", type(error).__name__)
                plan_obs.mark_error(error)  # 듣기 모드로 이어 가므로 닫지 않고, 아래에서 고른 모드(listen)를 덧붙여 닫는다
                key_error = byok.classify_error(error) if user_key else None
                if key_error:
                    plan_obs.end()
                    outcome["refund"] = True
                    yield line({"type": "error", "key": key_error})
                    return
                plan = {}
            mode = plan.get("mode") if plan.get("mode") in coach.MODES else "listen"
            picked = cardlib.pick(plan.get("card_ids"))
            asked = plan.get("card_ids")
            plan_obs.end(usage_details=plan_usage or None, metadata={"mode": mode, "card_ids": [c["id"] for c in picked], "asked_cards": len(asked) if isinstance(asked, list) else 0})  # 요청한 수와 실제 카드 수가 다르면 모델이 없는 카드 id 를 댄 것
            if mode == "crisis":
                outcome["refund"] = True
                turn.update(output={"result": "crisis", "by": "model"})
                yield line({"type": "crisis"})
                return
            if mode == "out_of_scope":
                outcome["refund"] = True
                turn.update(output={"result": "scope"})
                yield line({"type": "scope"})
                return
            if mode in ("advise", "quest") and not picked:
                # 맞는 카드가 없으면 방법을 말하지 않고 듣기로 돌아간다
                yield line({"type": "notice", "key": "noEvidence"})
                mode = "listen"
            yield line({"type": "mode", "mode": mode})
            used_prompts = []
            msgs = [{"role": "system", "content": coach.build_system(mode, picked, ctx, todos, character, history, used_prompts)}] + coach.with_tone_reminder(coach.neutralize_history(history, character), character, coach.variation_hint(history) if mode in coach.CHAT_MODES else "")
            # 대화 모드는 문장 단위로 걸러 내보낸다(질문 하나, 되묻기 되풀이 금지, 근거 없는 숫자 문장 차단). 조언·퀘스트는 길이만 자른다
            limiter = coach.reply_filter(mode, picked, history, ctx, todos)
            reply_obs = turn.child("generate-reply", "generation", model=getattr(engine, "model", None), metadata={"mode": mode}, input=tracing.text(msgs),
                                   **({"prompt": used_prompts[0]} if used_prompts else {}))
            reply_usage = {}
            first = True
            try:
                for piece in engine.chat_stream(msgs, **tracing.usage_kw(engine.chat_stream, reply_usage)):
                    out = limiter.feed(piece)
                    if out:
                        if first:
                            first = False
                            reply_obs.first_token()
                        yield line({"type": "delta", "text": out})
                    if limiter.done:
                        break
                tail = limiter.finish()  # 문장 끝 부호 없이 끝난 마지막 조각
                if tail:
                    if first:
                        reply_obs.first_token()
                    yield line({"type": "delta", "text": tail})
            except Exception as error:
                reply_obs.fail(error)
                raise
            reply = limiter.out.strip()
            ok = bool(reply) and "[REFUSED]" not in reply
            # 길이 제한으로 스트림을 먼저 끊으면(cut) 사용량이 담긴 마지막 조각을 받지 못해 토큰 칸이 빈다
            reply_obs.end(output=tracing.text(reply), usage_details=reply_usage or None,
                          metadata={"mode": mode, "reply_chars": len(reply), "refused": "[REFUSED]" in reply, "cut": limiter.done})
            if ok and mode in ("advise", "quest", "app", "general", "listen"):  # 근거 없는 숫자를 지어내지 않았는지(앱·대화 모드는 앱 안내의 숫자만 더 허용)
                ok = coach.numbers_ok(reply, picked, history, ctx, todos, coach.APP_NUMBERS if mode in ("app", "listen") else ())
                turn.child("check-numbers", "guardrail").end(output={"ok": ok}, metadata={"mode": mode})
            basis = "cards" if mode in ("advise", "quest") else mode if mode in ("app", "general") else "none"  # 화면의 근거 표시용(general=출처 미확인 일반 정보)
            outcome["refund"] = not ok  # 화면이 버리는 답(ok=false)이면 되돌린다
            turn.update(output={"result": "reply", "ok": ok, "mode": mode, "basis": basis, **({"reply": reply} if tracing.CAPTURE_TEXT else {})})
            yield line({"type": "done", "ok": ok, "mode": mode, "basis": basis, "cards": cardlib.meta(picked) if mode in ("advise", "quest") else []})
        except Exception as error:  # 입력·응답 내용은 남기지 않고 오류 종류만 남긴다
            log.error("chat failed: %s", type(error).__name__)
            turn.update(level="ERROR", status_message=type(error).__name__)
            outcome["refund"] = True
            key_error = byok.classify_error(error) if user_key else None
            yield line({"type": "error", "key": key_error} if key_error else {"type": "error"})

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})
