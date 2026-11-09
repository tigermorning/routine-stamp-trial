"""Claude 답 생성 한도: 숨은 생각이 max_tokens 를 먹어 답이 비던 문제(Main Quest 08)의 재발 방지."""
import llm


class _Stream:
    text_stream = iter(["안녕하세요."])

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        class F:
            stop_reason = "end_turn"
            usage = None
        return F()


class _Messages:
    def __init__(self):
        self.kw = None

    def stream(self, **kw):
        self.kw = kw
        return _Stream()


def _engine():
    e = llm.ClaudeLLM.__new__(llm.ClaudeLLM)
    e.model = "m"
    e.client = type("C", (), {})()
    e.client.beta = type("B", (), {})()
    e.client.beta.messages = _Messages()
    return e


def test_claude_reply_stream_uses_the_larger_budget_not_the_old_450():
    e = _engine()
    list(e.chat_stream([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]))
    assert e.client.beta.messages.kw["max_tokens"] == llm.CLAUDE_REPLY_TOKENS
    assert llm.CLAUDE_REPLY_TOKENS >= 1500 and llm.REPLY_TOKENS == 450  # 다른 제공사(OpenAI 호환)의 한도는 그대로
