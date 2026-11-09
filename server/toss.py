"""토스페이먼츠 결제 승인 API 호출(서버 전용).

근거(2026-11-04 읽음):
- 결제위젯 연동 문서 https://docs.tosspayments.com/guides/v2/payment-widget/integration : 승인은 서버가 시크릿 키로,
  Authorization: Basic base64("{시크릿 키}:") , 본문은 paymentKey·orderId·amount.
- 코어 API 문서 https://docs.tosspayments.com/reference : POST /v1/payments/confirm.
- 멱등키 문서 https://docs.tosspayments.com/reference/using-api/idempotency-key : Idempotency-Key 헤더, 300자 이하, 15일 유효,
  첫 요청이 처리 중이면 409 IDEMPOTENT_REQUEST_PROCESSING → 잠시 뒤 같은 키로 다시 요청.

시크릿 키는 환경변수 TOSS_SECRET_KEY 에서만 읽고, 로그·응답에 쓰지 않는다. live_ 로 시작하는 키는 쓰지 않는다(이 저장소는 테스트용).
"""
import base64
import json
import logging
import os
import time
import urllib.error
import urllib.request

CONFIRM_URL = "https://api.tosspayments.com/v1/payments/confirm"
log = logging.getLogger("coach")


def secret_key():
    k = os.environ.get("TOSS_SECRET_KEY", "").strip()
    return k if k.startswith("test_") else ""  # 비었거나 live_ 면 쓰지 않는다


def client_key():
    k = os.environ.get("TOSS_CLIENT_KEY", "").strip()
    return k if k.startswith("test_") else ""


def mask(value):
    v = str(value or "")
    return ("…" + v[-4:]) if len(v) > 4 else "…"


def confirm(payment_key, order_id, amount, idempotency_key):
    """{"ok": bool, "status": HTTP 상태, "body": 응답 JSON}. 키가 없으면 승인 API 를 부르지 않는다."""
    sk = secret_key()
    if not sk:
        return {"ok": False, "status": 0, "body": {"code": "NOT_CONFIGURED", "message": "TOSS_SECRET_KEY 가 설정되지 않았습니다."}}
    auth = base64.b64encode((sk + ":").encode()).decode()
    data = json.dumps({"paymentKey": payment_key, "orderId": order_id, "amount": amount}).encode()
    for attempt in range(3):
        req = urllib.request.Request(CONFIRM_URL, data=data, method="POST", headers={
            "Authorization": "Basic " + auth, "Content-Type": "application/json", "Idempotency-Key": idempotency_key})
        # 남기는 것: orderId·Idempotency-Key·paymentKey 끝 4자리. 시크릿 키와 paymentKey 전체는 남기지 않는다
        log.info("toss confirm call orderId=%s idempotencyKey=%s paymentKey=%s attempt=%d", order_id, idempotency_key, mask(payment_key), attempt + 1)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return {"ok": True, "status": r.status, "body": json.loads(r.read().decode() or "{}")}
        except urllib.error.HTTPError as e:
            try:
                body = json.loads(e.read().decode() or "{}")
            except ValueError:
                body = {}
            if e.code == 409 and body.get("code") == "IDEMPOTENT_REQUEST_PROCESSING" and attempt < 2:
                time.sleep(1.5)  # 첫 요청이 처리 중: 같은 키로 다시 묻는다(키를 바꾸지 않는다)
                continue
            log.warning("toss confirm failed orderId=%s status=%s code=%s", order_id, e.code, body.get("code"))
            return {"ok": False, "status": e.code, "body": body}
        except (urllib.error.URLError, TimeoutError) as e:
            log.warning("toss confirm network error orderId=%s: %s", order_id, type(e).__name__)
            return {"ok": False, "status": 0, "body": {"code": "NETWORK_ERROR", "message": "결제 승인 서버에 연결하지 못했습니다."}}
    return {"ok": False, "status": 409, "body": {"code": "IDEMPOTENT_REQUEST_PROCESSING", "message": "승인 처리 중입니다. 잠시 뒤 다시 시도해 주세요."}}
