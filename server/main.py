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
"""
import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

import byok
import cards as cardlib
import coach
import feedback
import llm as llm_module
import stamp
from llm import make_llm

PAGE = Path(__file__).resolve().parent.parent / "index.html"
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
def chat(req: ChatRequest, request: Request, model=Depends(get_llm), factory=Depends(get_user_llm_factory)):
    if limited(client_ip(request)):
        return JSONResponse({"error": "busy"}, status_code=429)
    history = coach.clean_history([m.model_dump() for m in req.messages])
    if not history:
        return JSONResponse({"error": "empty"}, status_code=400)
    ctx, todos = coach.clean_context(req.context), coach.clean_todos(req.todos)
    character = coach.clean_character(req.character)
    last = history[-1]["content"]
    raw_key = request.headers.get(byok.HEADER)

    def events():
        if coach.is_crisis(last):  # 모델에 보내지 않는다
            yield line({"type": "crisis"})
            return
        engine, user_key, key_error = pick_llm(raw_key, model, factory)
        if key_error:  # 키가 없거나 형식이 틀림: 운영자 키로 대신 부르지 않고 안내만
            yield line({"type": "error", "key": key_error})
            return
        try:
            system, user = coach.plan_messages(history, len(todos))
            try:
                plan = engine.complete_json(system, user)
            except Exception as error:  # 계획 단계가 실패해도 듣기 모드로 이어 간다(사용자 키 문제면 안내하고 끝낸다)
                log.warning("plan failed: %s", type(error).__name__)
                key_error = byok.classify_error(error) if user_key else None
                if key_error:
                    yield line({"type": "error", "key": key_error})
                    return
                plan = {}
            mode = plan.get("mode") if plan.get("mode") in coach.MODES else "listen"
            picked = cardlib.pick(plan.get("card_ids"))
            if mode == "crisis":
                yield line({"type": "crisis"})
                return
            if mode == "out_of_scope":
                yield line({"type": "scope"})
                return
            if mode in ("advise", "quest") and not picked:
                # 맞는 카드가 없으면 방법을 말하지 않고 듣기로 돌아간다
                yield line({"type": "notice", "key": "noEvidence"})
                mode = "listen"
            yield line({"type": "mode", "mode": mode})
            msgs = [{"role": "system", "content": coach.build_system(mode, picked, ctx, todos, character, history)}] + coach.with_tone_reminder(coach.neutralize_history(history, character), character, coach.variation_hint(history) if mode in coach.CHAT_MODES else "")
            limiter = coach.Limiter(coach.MAX_QUEST if mode == "quest" else coach.MAX_REPLY, one_line=(mode == "quest"))
            for piece in engine.chat_stream(msgs):
                out = limiter.feed(piece)
                if out:
                    yield line({"type": "delta", "text": out})
                if limiter.done:
                    break
            reply = limiter.out.strip()
            ok = bool(reply) and "[REFUSED]" not in reply
            if ok and mode in ("advise", "quest", "app", "general", "listen"):  # 근거 없는 숫자를 지어내지 않았는지(앱·대화 모드는 앱 안내의 숫자만 더 허용)
                ok = coach.numbers_ok(reply, picked, history, ctx, todos, coach.APP_NUMBERS if mode in ("app", "listen") else ())
            basis = "cards" if mode in ("advise", "quest") else mode if mode in ("app", "general") else "none"  # 화면의 근거 표시용(general=출처 미확인 일반 정보)
            yield line({"type": "done", "ok": ok, "mode": mode, "basis": basis, "cards": cardlib.meta(picked) if mode in ("advise", "quest") else []})
        except Exception as error:  # 입력·응답 내용은 남기지 않고 오류 종류만 남긴다
            log.error("chat failed: %s", type(error).__name__)
            key_error = byok.classify_error(error) if user_key else None
            yield line({"type": "error", "key": key_error} if key_error else {"type": "error"})

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})
