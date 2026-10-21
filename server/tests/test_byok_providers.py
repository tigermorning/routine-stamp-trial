"""BYOK 제공사 선택(키 모양)과 제공사별 오류 분류 시험. 진짜 호출은 하지 않는다(가짜 LLM, SDK 의 진짜 예외 클래스를 흉내 낸 값만 쓴다)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest
from fastapi.testclient import TestClient

import byok
import main
from llm import FakeLLM

HDR = byok.HEADER
KEYS = {
    "claude": "sk-ant-api03-SECRETANTHROPICKEY0123456789",
    "gemini": "AIzaSySECRETGEMINIKEY0123456789abcdefg",
    "openai": "sk-proj-SECRETOPENAIKEY0123456789abcdef",
    "openai-plain": "sk-SECRETOPENAIPLAINKEY0123456789",
}


@pytest.fixture(autouse=True)
def fresh():
    main._hits.clear()
    yield
    main.app.dependency_overrides.clear()


# ---- 접두사로 제공사 고르기 ----
@pytest.mark.parametrize("key,provider", [
    (KEYS["claude"], "claude"), ("sk-ant-x", "claude"),
    (KEYS["gemini"], "gemini"), ("AIza", "gemini"),
    (KEYS["openai"], "openai"), (KEYS["openai-plain"], "openai"), ("sk-svcacct-abc", "openai"),
    ("something-else-123", "openai"), ("sk-an-not-anthropic", "openai"), ("aiza-lowercase", "openai"),
])
def test_provider_for(key, provider):
    assert byok.provider_for(key) == provider


def test_build_user_llm_passes_chosen_provider_default_model_and_the_key(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "PROVIDER", "openai")
    monkeypatch.setattr(main, "make_llm", lambda p, k, m: calls.append((p, k, m)) or object())
    for key in KEYS.values():
        main.build_user_llm(key)
    assert [(p, m) for p, _, m in calls] == [("claude", ""), ("gemini", ""), ("openai", ""), ("openai", "")]  # 모델은 빈 값 = 제공사 기본
    assert [k for _, k, _ in calls] == list(KEYS.values())


def test_fake_provider_ignores_key_shape(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "PROVIDER", "fake")
    monkeypatch.setattr(main, "make_llm", lambda p, k, m: calls.append(p) or object())
    main.build_user_llm(KEYS["claude"])
    assert calls == ["fake"]  # 로컬 시험에서는 키 모양과 상관없이 가짜


def test_real_make_llm_builds_each_provider_client_with_default_model():
    pytest.importorskip("openai")
    pytest.importorskip("anthropic")
    from llm import ClaudeLLM, OpenAICompatibleLLM, PROVIDERS

    for key, cls, model_key in ((KEYS["claude"], ClaudeLLM, "claude"), (KEYS["gemini"], OpenAICompatibleLLM, "gemini"), (KEYS["openai"], OpenAICompatibleLLM, "openai")):
        obj = main.make_llm(byok.provider_for(key), key, "")  # 네트워크 호출 없이 객체만 만든다
        assert isinstance(obj, cls) and obj.model == PROVIDERS[model_key]["model"]
    gem = main.make_llm("gemini", KEYS["gemini"], "")
    assert "generativelanguage.googleapis.com" in str(gem.client.base_url)  # 제미나이는 OpenAI 호환 주소


# ---- 운영자 경로는 그대로 ----
def test_operator_path_never_uses_key_shape_or_the_user_factory(monkeypatch):
    built = []
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM(delay=0)
    main.app.dependency_overrides[main.get_user_llm_factory] = lambda: (lambda key: built.append(key) or FakeLLM(delay=0))
    r = TestClient(main.app).post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]})
    assert json.loads(r.text.splitlines()[-1])["type"] == "done" and built == []
    r = TestClient(main.app).post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]}, headers={HDR: KEYS["claude"]})
    assert built == [KEYS["claude"]]  # 헤더가 있을 때만 사용자 경로


# ---- 제공사별 오류 → keyInvalid / keyLimit ----
def http_error(cls_module, cls_name, status, body):
    mod = pytest.importorskip(cls_module)
    req = httpx.Request("POST", "http://example.invalid/v1")
    resp = httpx.Response(status, request=req, json=body)
    return getattr(mod, cls_name)("제공사 메시지에는 키가 있을 수 있다 " + KEYS["openai"], response=resp, body=body)


CASES = [
    # OpenAI (SDK 의 진짜 예외 클래스)
    ("openai", "AuthenticationError", 401, {"error": {"code": "invalid_api_key", "type": "invalid_request_error"}}, "keyInvalid"),
    ("openai", "PermissionDeniedError", 403, {"error": {"code": "unsupported_country_region_territory"}}, "keyInvalid"),
    ("openai", "RateLimitError", 429, {"error": {"code": "insufficient_quota", "type": "insufficient_quota"}}, "keyLimit"),
    ("openai", "RateLimitError", 429, {"error": {"code": "rate_limit_exceeded"}}, "keyLimit"),
    ("openai", "InternalServerError", 500, {"error": {"code": "server_error"}}, None),
    # Anthropic
    ("anthropic", "AuthenticationError", 401, {"type": "error", "error": {"type": "authentication_error"}}, "keyInvalid"),
    ("anthropic", "PermissionDeniedError", 403, {"type": "error", "error": {"type": "permission_error"}}, "keyInvalid"),
    ("anthropic", "RateLimitError", 429, {"type": "error", "error": {"type": "rate_limit_error"}}, "keyLimit"),
    ("anthropic", "APIStatusError", 402, {"type": "error", "error": {"type": "billing_error"}}, "keyLimit"),
    ("anthropic", "BadRequestError", 400, {"type": "error", "error": {"type": "invalid_request_error"}}, None),
    # Gemini(OpenAI 호환 주소): 잘못된 키가 401 이 아니라 400 + API_KEY_INVALID 로 오는 모양(커뮤니티 보고)
    ("openai", "BadRequestError", 400, [{"error": {"code": 400, "status": "INVALID_ARGUMENT", "details": [{"@type": "x", "reason": "API_KEY_INVALID"}]}}], "keyInvalid"),
    ("openai", "BadRequestError", 400, [{"error": {"code": 400, "status": "INVALID_ARGUMENT", "details": [{"reason": "SOMETHING_ELSE"}]}}], None),
    ("openai", "RateLimitError", 429, [{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}], "keyLimit"),
    ("openai", "AuthenticationError", 401, [{"error": {"code": 401, "status": "UNAUTHENTICATED"}}], "keyInvalid"),
]


@pytest.mark.parametrize("module,cls,status,body,expected", CASES)
def test_classify_real_sdk_exception_classes(module, cls, status, body, expected):
    exc = http_error(module, cls, status, body)
    assert byok.classify_error(exc) == expected


def test_classify_reads_codes_not_message_text():
    class Weird(Exception):
        status_code = 400
        body = {"error": {"message": "invalid_api_key insufficient_quota API_KEY_INVALID", "code": "bad_request"}}

    assert byok.classify_error(Weird()) is None  # 문구에 코드 낱말이 들어 있어도 문구는 보지 않는다


# ---- 끝에서 끝까지: 키 모양별 사용자 경로 + 로그에 키·제공사 이름 없음 ----
class Failing(FakeLLM):
    def __init__(self, exc):
        super().__init__(delay=0)
        self.exc = exc

    def complete_json(self, system, user):
        raise self.exc

    def chat_stream(self, messages):
        raise self.exc
        yield  # pragma: no cover

    def complete_text(self, messages, max_tokens):
        raise self.exc


def make_factory(exc):
    """FastAPI 는 기본값 인자를 복사하려 하므로(예외 객체는 복사가 안 된다) 닫힌 함수로 만든다."""
    def provider():
        return lambda key: Failing(exc)
    return provider


def test_end_to_end_each_key_shape_maps_errors_and_never_logs_key_or_provider(caplog):
    outputs = []
    with caplog.at_level("DEBUG"):
        for key in KEYS.values():
            for module, cls, status, body, expected in (
                ("anthropic", "AuthenticationError", 401, {"error": {"type": "authentication_error"}}, "keyInvalid"),
                ("openai", "RateLimitError", 429, {"error": {"code": "insufficient_quota"}}, "keyLimit"),
            ):
                main._hits.clear()
                main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM(delay=0)
                exc = http_error(module, cls, status, body)
                main.app.dependency_overrides[main.get_user_llm_factory] = make_factory(exc)
                c = TestClient(main.app)
                r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "안녕"}]}, headers={HDR: key})
                ev = [json.loads(x) for x in r.text.splitlines() if x]
                assert ev[-1] == {"type": "error", "key": expected}
                s = c.post("/api/stamp", json={"name": "독서"}, headers={HDR: key})
                assert s.json() == {"error": expected} and s.status_code == (401 if expected == "keyInvalid" else 429)
                outputs += [r.text, s.text]
    everything = " ".join(outputs) + caplog.text
    for key in KEYS.values():
        assert key not in everything
    lowered = everything.lower()
    for word in ("claude", "gemini", "openai", "anthropic", "sk-ant", "aiza"):
        assert word not in lowered, word  # 제공사 이름·키 접두사도 응답·로그에 없다
    assert "authenticationerror" in lowered or "ratelimiterror" in lowered  # 오류 종류 이름만 남는다
