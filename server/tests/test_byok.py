"""BYOK(사용자 키) 시험. 진짜 키는 쓰지 않는다. 시험용 가짜 키 문자열이 응답·로그 어디에도 나오지 않는지 확인한다."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

import byok
import main
from llm import FakeLLM

KEY = "sk-test-SECRETKEY-1234567890abcdef"
H = {byok.HEADER: KEY}
LISTEN = {"mode": "listen", "card_ids": []}


class ProviderError(Exception):
    """제공사 오류 흉내. 메시지에 키가 들어 있다(실제 제공사 오류도 그럴 수 있다)."""

    def __init__(self, status, body=None, name=None):
        super().__init__(f"Incorrect API key provided: {KEY}")
        self.status_code, self.body = status, body
        if name:
            self.__class__ = type(name, (ProviderError,), {})


class Engine(FakeLLM):
    """호출 횟수를 세고, 정해 둔 오류를 낼 수 있는 가짜 LLM."""

    def __init__(self, plan=LISTEN, plan_exc=None, stream_exc=None, text_exc=None):
        super().__init__(delay=0)
        self.plan, self.plan_exc, self.stream_exc, self.text_exc, self.calls = plan, plan_exc, stream_exc, text_exc, 0

    def complete_json(self, system, user):
        self.calls += 1
        if self.plan_exc:
            raise self.plan_exc
        return self.plan

    def chat_stream(self, messages):
        self.calls += 1
        if self.stream_exc:
            raise self.stream_exc
        yield "네."

    def complete_text(self, messages, max_tokens):
        self.calls += 1
        if self.text_exc:
            raise self.text_exc
        return FakeLLM.FAKE_SVG


@pytest.fixture(autouse=True)
def fresh():
    main._hits.clear()
    yield
    main.app.dependency_overrides.clear()


class Setup:
    def __init__(self, operator=None, user=None):
        self.operator, self.user, self.factory_keys = operator or Engine(), user or Engine(), []
        main.app.dependency_overrides[main.get_llm] = lambda: self.operator
        main.app.dependency_overrides[main.get_user_llm_factory] = lambda: self._factory
        self.client = TestClient(main.app)

    def _factory(self, key):
        self.factory_keys.append(key)
        return self.user

    def chat(self, headers=None, text="안녕하세요"):
        r = self.client.post("/api/chat", json={"messages": [{"role": "user", "content": text}]}, headers=headers or {})
        return r, [json.loads(x) for x in r.text.splitlines() if x]

    def stamp(self, headers=None, name="달리기"):
        return self.client.post("/api/stamp", json={"name": name}, headers=headers or {})


# ---- optional(기본) ----
def test_default_mode_is_optional():
    assert main.BYOK_MODE == "optional" and byok.parse_mode(None) == "optional" and byok.parse_mode(" REQUIRED ") == "required"
    with pytest.raises(SystemExit):
        byok.parse_mode("sometimes")


def test_optional_without_header_uses_operator_key_as_before():
    s = Setup()
    _, ev = s.chat()
    assert ev[-1]["type"] == "done" and s.operator.calls > 0 and s.user.calls == 0 and s.factory_keys == []
    assert s.stamp().status_code == 200 and s.user.calls == 0


def test_optional_with_header_uses_user_key_not_operator():
    s = Setup()
    _, ev = s.chat(H)
    assert ev[-1]["type"] == "done" and s.user.calls > 0 and s.operator.calls == 0 and s.factory_keys == [KEY]
    s.operator.calls = 0
    assert s.stamp(H).status_code == 200 and s.operator.calls == 0


def test_user_llm_is_built_fresh_every_request_not_cached():
    s = Setup()
    s.chat(H)
    s.chat(H)
    s.stamp(H)
    assert s.factory_keys == [KEY, KEY, KEY]


# ---- required ----
def test_required_without_header_never_touches_operator_key(monkeypatch):
    monkeypatch.setattr(main, "BYOK_MODE", "required")
    s = Setup()
    r, ev = s.chat()
    assert r.status_code == 200 and ev == [{"type": "error", "key": "keyMissing"}]
    r = s.stamp()
    assert r.status_code == 401 and r.json() == {"error": "keyMissing"}
    assert s.operator.calls == 0 and s.user.calls == 0
    r = s.client.post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]}, headers={byok.HEADER: "   "})
    assert json.loads(r.text.splitlines()[0]) == {"type": "error", "key": "keyMissing"}  # 빈 헤더도 없는 것과 같다


def test_required_with_header_works(monkeypatch):
    monkeypatch.setattr(main, "BYOK_MODE", "required")
    s = Setup()
    _, ev = s.chat(H)
    assert ev[-1]["type"] == "done" and s.operator.calls == 0 and s.user.calls > 0


def test_crisis_still_gets_safety_message_without_a_key(monkeypatch):
    monkeypatch.setattr(main, "BYOK_MODE", "required")
    _, ev = Setup().chat(text="죽고 싶어요")
    assert ev == [{"type": "crisis"}]  # 키가 없어도 안전 안내는 막지 않는다


# ---- 키 형식 ----
@pytest.mark.parametrize("bad", ["x" * 201, "bad key", "키값", "sk-\x7f-del"])
def test_malformed_key_is_keyInvalid_and_not_sent_to_any_provider(bad):
    s = Setup()
    headers = {byok.HEADER: bad.encode("utf-8")} if not bad.isascii() else {byok.HEADER: bad}
    _, ev = s.chat(headers)
    assert ev == [{"type": "error", "key": "keyInvalid"}]
    r = s.stamp(headers)
    assert r.status_code == 401 and r.json() == {"error": "keyInvalid"}
    assert s.factory_keys == [] and s.operator.calls == 0  # 운영자 키로 대신 부르지 않는다


def test_valid_unit():
    assert byok.valid("sk-abc_123") and byok.valid("x" * 200)
    assert not byok.valid("") and not byok.valid("x" * 201) and not byok.valid("a b") and not byok.valid("키")


# ---- 제공사 오류 분류 ----
@pytest.mark.parametrize("exc,expected", [
    (ProviderError(401), "keyInvalid"),
    (ProviderError(403), "keyInvalid"),
    (ProviderError(None, name="AuthenticationError"), "keyInvalid"),
    (ProviderError(429), "keyLimit"),
    (ProviderError(402), "keyLimit"),
    (ProviderError(None, name="RateLimitError"), "keyLimit"),
    (ProviderError(400, body={"error": {"code": "insufficient_quota"}}), "keyLimit"),
    (ProviderError(500), None),
    (ProviderError(None), None),
    (RuntimeError("boom"), None),
])
def test_classify_error(exc, expected):
    assert byok.classify_error(exc) == expected


@pytest.mark.parametrize("status,key", [(401, "keyInvalid"), (429, "keyLimit")])
def test_chat_maps_plan_stage_errors_and_stops_the_stream(status, key):
    s = Setup(user=Engine(plan_exc=ProviderError(status)))
    r, ev = s.chat(H)
    assert r.status_code == 200 and ev == [{"type": "error", "key": key}]
    assert s.operator.calls == 0  # 운영자 키로 대신 부르지 않는다


@pytest.mark.parametrize("status,key", [(401, "keyInvalid"), (429, "keyLimit")])
def test_chat_maps_stream_stage_errors(status, key):
    s = Setup(user=Engine(stream_exc=ProviderError(status)))
    _, ev = s.chat(H)
    assert ev[-1] == {"type": "error", "key": key} and not any(e["type"] == "done" for e in ev)


def test_chat_other_provider_errors_stay_generic_error():
    s = Setup(user=Engine(stream_exc=ProviderError(500)))
    _, ev = s.chat(H)
    assert ev[-1] == {"type": "error"}  # key 필드가 없는 기존 모양
    s = Setup(user=Engine(plan_exc=ProviderError(500)))
    _, ev = s.chat(H)
    assert ev[-1]["type"] == "done"  # 계획 단계의 일반 오류는 지금처럼 듣기로 이어 간다


def test_operator_key_problems_are_not_blamed_on_the_user():
    s = Setup(operator=Engine(stream_exc=ProviderError(401)))
    _, ev = s.chat()  # 헤더 없음 → 운영자 키. 운영자 키 오류를 사용자에게 keyInvalid 라고 하지 않는다
    assert ev[-1] == {"type": "error"}
    assert s.stamp().status_code in (200, 502)
    s = Setup(operator=Engine(text_exc=ProviderError(401)))
    r = s.stamp()
    assert r.status_code == 502 and r.json() == {"error": "failed"}


@pytest.mark.parametrize("status,http,key", [(401, 401, "keyInvalid"), (403, 401, "keyInvalid"), (429, 429, "keyLimit")])
def test_stamp_maps_user_key_errors(status, http, key):
    s = Setup(user=Engine(text_exc=ProviderError(status)))
    r = s.stamp(H)
    assert r.status_code == http and r.json() == {"error": key} and s.operator.calls == 0


def test_stamp_other_provider_error_is_502_failed():
    r = Setup(user=Engine(text_exc=ProviderError(500))).stamp(H)
    assert r.status_code == 502 and r.json() == {"error": "failed"}


def test_factory_failure_is_keyInvalid_without_leaking_key():
    s = Setup()

    def boom(key):
        raise ValueError(f"bad key {key}")

    main.app.dependency_overrides[main.get_user_llm_factory] = lambda: boom
    r, ev = s.chat(H)
    assert ev == [{"type": "error", "key": "keyInvalid"}] and KEY not in r.text


# ---- 속도 제한은 사용자 키여도 그대로 ----
def test_rate_limits_still_apply_with_user_key(monkeypatch):
    monkeypatch.setattr(main, "RATE_PER_IP", 1)
    s = Setup()
    assert s.chat(H)[0].status_code == 200
    assert s.chat(H)[0].status_code == 429
    monkeypatch.setattr(main, "RATE_STAMP_PER_IP", 1)
    assert s.stamp(H).status_code == 200
    assert s.stamp(H).status_code == 429


# ---- 키는 어디에도 남지 않는다 ----
def test_key_never_in_responses_or_logs(caplog):
    with caplog.at_level("DEBUG"):
        outputs = []
        s = Setup()
        outputs.append(s.chat(H)[0].text)                                            # 정상
        outputs.append(s.stamp(H).text)
        for status in (401, 429, 500):                                               # 제공사 오류(메시지에 키가 들어 있음)
            s = Setup(user=Engine(plan_exc=ProviderError(status)))
            outputs.append(s.chat(H)[0].text)
            s = Setup(user=Engine(stream_exc=ProviderError(status)))
            outputs.append(s.chat(H)[0].text)
            s = Setup(user=Engine(text_exc=ProviderError(status)))
            outputs.append(s.stamp(H).text)
        s = Setup()
        main.app.dependency_overrides[main.get_user_llm_factory] = lambda: (lambda key: (_ for _ in ()).throw(ValueError(key)))
        outputs.append(s.chat(H)[0].text)                                            # 객체 만들기 실패
    assert all(KEY not in o and "SECRETKEY" not in o for o in outputs)
    assert KEY not in caplog.text and "SECRETKEY" not in caplog.text
    assert "Incorrect API key" not in caplog.text  # 제공사 오류 문구도 로그에 없다
    assert any("chat failed" in r.message or "stamp failed" in r.message for r in caplog.records)  # 오류 종류는 남는다
