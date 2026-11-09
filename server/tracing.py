"""Langfuse 관측(선택). 한 턴(/api/chat 한 번)을 트레이스 하나로, 단계를 관찰 단위로 남긴다. 계측 구조의 이유는 ../docs/OBSERVABILITY.md.

- 켜는 조건: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY 가 모두 있고 langfuse 패키지가 있을 때만. 아니면 아무 일도 하지 않는다(키 없는 시험·GitHub Pages 에서 그대로 돈다).
- 대화 원문은 보내지 않는다(이 서비스의 "대화는 저장도 로그도 하지 않는다" 원칙). 남기는 것은 단계 이름, 모드, 근거 카드 id, 글자 수, 시간, 성공 여부뿐이다.
  원문까지 보려면 LANGFUSE_CAPTURE_TEXT=on 을 켠다(전화번호·이메일·카드 번호 모양은 보내기 전에 가린다). 켜기 전에 개인정보 안내를 먼저 고친다.
- 계측이 실패해도 대답은 그대로 나간다(모든 호출을 감싼다). 사용자 키(BYOK)는 어디에도 남기지 않는다.
- 환경변수: ENV(기본 local → Langfuse environment), K_REVISION(Cloud Run 이 넣어 줌 → release), LANGFUSE_BASE_URL(미국 리전 https://us.cloud.langfuse.com).
"""
import inspect
import logging
import os
import time
import re
from datetime import datetime, timezone

log = logging.getLogger("coach")

CAPTURE_TEXT = os.environ.get("LANGFUSE_CAPTURE_TEXT", "off").strip().lower() == "on"
_MASKS = [(re.compile(r"\b\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}\b"), "[전화번호]"),
          (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[이메일]"),
          (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[카드번호]")]


def mask(*, data, **_):
    """Langfuse 가 보내기 직전에 입력·출력·메타데이터에 부르는 함수. 문자열 속 전화번호·이메일·카드 번호 모양을 가린다."""
    if isinstance(data, str):
        for pattern, label in _MASKS:
            data = pattern.sub(label, data)
        return data
    if isinstance(data, dict):
        return {k: mask(data=v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [mask(data=v) for v in data]
    return data


_client = None
_tried = False


def get_client():
    """Langfuse 클라이언트 하나(프로세스 안에서 한 번만 만든다). 켜지지 않으면 None. 테스트에서는 이 함수를 바꿔 끼운다."""
    global _client, _tried
    if _tried:
        return _client
    _tried = True
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from langfuse import Langfuse

        _client = Langfuse(environment=os.environ.get("ENV", "local").strip().lower() or "local",
                           release=os.environ.get("K_REVISION", "local"), mask=mask if CAPTURE_TEXT else None)
    except Exception as error:  # 키 글자는 남기지 않고 오류 종류만 남긴다
        log.warning("tracing off: %s", type(error).__name__)
        _client = None
    return _client


class Obs:
    """관찰 단위 하나. raw 가 None 이면(꺼짐) 모든 호출이 아무 일도 하지 않는다. 안 꺼져 있어도 호출이 실패하면 삼킨다."""

    def __init__(self, raw=None, client=None):
        self.raw, self.client = raw, client

    def child(self, name, as_type="span", **kw):
        if self.raw is None:
            return Obs()
        try:
            return Obs(self.raw.start_observation(name=name, as_type=as_type, **kw), self.client)
        except Exception as error:
            log.warning("tracing step failed: %s", type(error).__name__)
            return Obs()

    def first_token(self):
        """답의 첫 글자가 나온 시각을 남긴다(사용자가 기다린 시간은 끝이 아니라 첫 글자까지다)."""
        self.update(completion_start_time=datetime.now(timezone.utc))

    def update(self, **kw):
        if self.raw is not None:
            try:
                self.raw.update(**kw)
            except Exception as error:
                log.warning("tracing update failed: %s", type(error).__name__)

    def end(self, **kw):
        """닫는다. 이미 닫았으면 아무 일도 하지 않는다(SDK 가 "Calling end() on an ended span" 경고를 내지 않게)."""
        if self.raw is not None and not getattr(self, "ended", False):
            self.ended = True
            try:
                self.raw.update(**kw)
                self.raw.end()
            except Exception as error:
                log.warning("tracing end failed: %s", type(error).__name__)

    def mark_error(self, error):
        """닫지 않고 오류 표시만 한다(실패해도 다음 단계로 이어 가는 경우, 나중에 결과를 덧붙여 닫는다)."""
        self.update(level="ERROR", status_message=type(error).__name__)

    def fail(self, error):
        """오류 종류만 남기고 닫는다(메시지는 제공사 문구·입력이 섞일 수 있어 남기지 않는다)."""
        self.end(level="ERROR", status_message=type(error).__name__)


def usage_kw(fn, usage):
    """LLM 함수가 usage 인자(토큰 수를 채울 dict)를 받을 수 있으면 {"usage": usage}, 아니면 {}(인자가 없는 시험용 가짜 LLM)."""
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return {}
    ok = any(p.name == "usage" or p.kind is inspect.Parameter.VAR_KEYWORD for p in params)
    return {"usage": usage} if ok else {}


def text(value):
    """원문을 남기도록 켠 경우에만 값을 돌려준다. 꺼져 있으면 None(입력·출력 칸이 비어 있다)."""
    return value if CAPTURE_TEXT else None


def start_turn(byok=False):
    """한 턴의 트레이스(chat-turn)를 연다. 꺼져 있으면 아무 일도 하지 않는 Obs. 끝날 때 turn.end(...) 후 flush(turn)."""
    client = get_client()
    if client is None:
        return Obs()
    try:
        # 한 턴의 흐름(듣기·조언·위기 등)을 모델이 고르므로 agent 종류로 둔다(Langfuse 에이전트 그래프에 한 마디로 보인다)
        return Obs(client.start_observation(name="chat-turn", as_type="agent", metadata={"byok": bool(byok)}), client)
    except Exception as error:
        log.warning("tracing start failed: %s", type(error).__name__)
        return Obs()


def flush(turn):
    """Cloud Run 은 응답이 끝나면 CPU 를 줄이므로 기록을 모아 두었다 보내는 SDK 가 못 보낼 수 있다. 턴이 끝날 때 바로 보낸다.
    진단(2026-11-09, 배포한 서버에서 45턴 중 24개만 Langfuse 에 보인 원인을 찾으려고): 보내는 데 걸린 시간과 «시간 안에 다 보냈는지»(provider_ok)를
    트레이스 번호와 함께 로그에 남긴다. 원문·키는 남기지 않는다. provider_ok=False 면 시간 안에 못 보낸 것이다."""
    if turn.client is not None:
        t0 = time.monotonic()
        ok = None
        try:
            provider = getattr(getattr(turn.client, "_resources", None), "tracer_provider", None)
            force = getattr(provider, "force_flush", None)
            if callable(force):
                ok = force(timeout_millis=15000)
            turn.client.flush()
        except Exception as error:
            log.warning("tracing flush failed: %s", type(error).__name__)
        log.info("tracing flush trace=%s provider_ok=%s ms=%d", getattr(turn.raw, "trace_id", None), ok, int((time.monotonic() - t0) * 1000))
