"""BYOK(사용자가 자기 키를 넣어 쓰기): 키 읽기·검사, 제공사 오류 분류.

키는 요청 헤더 X-User-LLM-Key 로만 받는다. 그 요청을 처리하는 동안만 쓰고 저장·로그·응답·오류 메시지 어디에도 남기지 않는다
(이 모듈은 로그를 쓰지 않고, 오류는 종류(클래스 이름·상태 코드)만 보며 메시지 글은 읽지 않는다 — 제공사 오류 문구에는 키 앞부분이 들어 있을 수 있다).
"""
import os

HEADER = "X-User-LLM-Key"
MAX_KEY = 200
MODES = ("optional", "required")


def parse_mode(value):
    """BYOK_MODE 값. optional(기본): 헤더가 있으면 그 키, 없으면 운영자 키. required: 헤더가 없으면 운영자 키를 쓰지 않고 안내만."""
    mode = (value or "optional").strip().lower()
    if mode not in MODES:
        raise SystemExit(f"BYOK_MODE 값 '{mode}' 를 알 수 없습니다. optional 또는 required 를 쓰세요.")
    return mode


def valid(key):
    """길이 200 이하, 공백 없는 출력 가능한 ASCII(33~126)만."""
    return 0 < len(key) <= MAX_KEY and all(33 <= ord(c) <= 126 for c in key)


def provider_for(key):
    """키의 모양으로 제공사를 고른다: 'sk-ant-' → claude, 'AIza' → gemini, 그 밖('sk-', 'sk-proj-' …) → openai.
    고른 결과는 로그·응답에 남기지 않는다(제공사 이름도 키 정보의 일부로 본다)."""
    if key.startswith("sk-ant-"):
        return "claude"
    if key.startswith("AIza"):
        return "gemini"
    return "openai"


# 제공사가 오류 본문에 담는 기계용 코드(문구가 아니다). 이 코드들만 본다.
_INVALID_CODES = {"invalid_api_key", "authentication_error", "permission_error", "API_KEY_INVALID", "UNAUTHENTICATED", "PERMISSION_DENIED"}
_LIMIT_CODES = {"insufficient_quota", "billing_hard_limit_reached", "billing_error", "rate_limit_error", "RESOURCE_EXHAUSTED"}


def _codes(node, depth=0):
    """오류 본문(dict·list 중첩)에서 code·type·status·reason 이 문자열인 값만 모은다. 'message' 같은 문구 칸은 읽지 않는다."""
    out = set()
    if depth > 4:
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("code", "type", "status", "reason") and isinstance(v, str):
                out.add(v)
            elif isinstance(v, (dict, list)):
                out |= _codes(v, depth + 1)
    elif isinstance(node, list):
        for v in node:
            out |= _codes(v, depth + 1)
    return out


def classify_error(exc):
    """제공사(OpenAI·Anthropic·Gemini의 OpenAI 호환 주소) 오류를 keyInvalid(인증 실패) / keyLimit(한도·결제) / None(그 밖) 으로 나눈다.
    클래스 이름·상태 코드·본문의 기계용 코드만 본다. 메시지 문구는 읽지도 돌려주지도 않는다.
    알려진 모양: OpenAI·Anthropic 은 401/403 → 인증, 429(·Anthropic 402 billing_error) → 한도·결제. Gemini 호환 주소는 잘못된 키에
    401 이 아니라 400 + reason API_KEY_INVALID 를 주는 경우가 있다(커뮤니티 보고, 공식 문서로는 확인 못 함)."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    name = type(exc).__name__
    codes = _codes(getattr(exc, "body", None))
    code = getattr(exc, "code", None)
    if isinstance(code, str):
        codes.add(code)
    if status in (401, 403) or name in ("AuthenticationError", "PermissionDeniedError") or codes & _INVALID_CODES:
        return "keyInvalid"
    if status in (402, 429) or name == "RateLimitError" or codes & _LIMIT_CODES:
        return "keyLimit"
    return None
