"""LLM 호출. friend-agent 템플릿(app/llm.py)의 complete_json·chat_stream 부분을 옮겨 왔다.

OpenAI 와 Gemini 는 같은 OpenAI SDK 로, Claude 는 Anthropic SDK 로 부른다. 메시지는 OpenAI 형식이다.
fake 는 키 없이 화면과 흐름을 확인하거나 테스트할 때 쓰는 가짜 응답이다(진짜 모델 경로는 이 PC에서 실행해 보지 않았다).
"""
import json
import re
import time

TIMEOUT = 25  # 초
PLAN_TOKENS = 120
REPLY_TOKENS = 450
SVG_TOKENS = 2500


def parse_json_object(text):
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("JSON 응답을 찾지 못했습니다.")
    return json.loads(match.group(0))


class OpenAICompatibleLLM:
    def __init__(self, api_key, model, base_url=None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=TIMEOUT)
        self.model = model

    def complete_json(self, system, user):
        r = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"}, max_tokens=PLAN_TOKENS)
        return json.loads(r.choices[0].message.content)

    def complete_text(self, messages, max_tokens):
        r = self.client.chat.completions.create(model=self.model, messages=messages, max_tokens=max_tokens)
        return r.choices[0].message.content or ""

    def chat_stream(self, messages):
        response = self.client.chat.completions.create(model=self.model, messages=messages, stream=True,
                                                       max_tokens=REPLY_TOKENS)
        for event in response:
            if event.choices and event.choices[0].delta.content:
                yield event.choices[0].delta.content


class ClaudeLLM:
    # friend-agent 와 같은 요청 모양: 안전 분류기가 거절하면 다른 Claude 모델이 이어서 답하게 하고, 생각 깊이는 낮게 둔다.
    BETAS = ["server-side-fallback-2026-07-01"]
    OUTPUT_CONFIG = {"effort": "low"}
    REFUSAL = "[REFUSED]"

    def __init__(self, api_key, model):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key, timeout=TIMEOUT)
        self.model = model

    def _request(self, system, turns, max_tokens):
        return dict(model=self.model, max_tokens=max_tokens, system=system, messages=turns,
                    output_config=self.OUTPUT_CONFIG, betas=self.BETAS, fallbacks="default")

    def complete_json(self, system, user):
        system = system + "\n\n반드시 JSON 객체 하나만 출력한다. 설명이나 코드 블록 표시는 붙이지 않는다."
        r = self.client.beta.messages.create(**self._request(system, [{"role": "user", "content": user}], PLAN_TOKENS))
        if r.stop_reason == "refusal":
            raise ValueError("Claude가 요청을 거절했습니다.")
        return parse_json_object("".join(b.text for b in r.content if b.type == "text"))

    def complete_text(self, messages, max_tokens):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        turns = [m for m in messages if m["role"] != "system"]
        r = self.client.beta.messages.create(**self._request(system, turns, max_tokens))
        if r.stop_reason == "refusal":
            raise ValueError("Claude가 요청을 거절했습니다.")
        return "".join(b.text for b in r.content if b.type == "text")

    def chat_stream(self, messages):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        turns = [m for m in messages if m["role"] != "system"]
        with self.client.beta.messages.stream(**self._request(system, turns, REPLY_TOKENS)) as stream:
            sent = False
            for text in stream.text_stream:
                sent = True
                yield text
            if stream.get_final_message().stop_reason == "refusal" and not sent:
                yield self.REFUSAL


class FakeLLM:
    """AI 를 부르지 않는다. 마지막 사용자 말에 'fake:...' 가 있으면 그에 맞춰 동작해 흐름을 시험할 수 있다.

    비용이 들지 않고 같은 입력에는 늘 같은 답을 돌려준다.
    """

    model = "fake"

    def __init__(self, delay=0.02):
        self.delay = delay

    @staticmethod
    def _last_user(text):
        return text.rsplit("사용자:", 1)[-1]

    def complete_json(self, system, user):
        last = self._last_user(user)
        if "fake:planerror" in last:
            raise RuntimeError("fake plan error")
        if "fake:badjson" in last:
            return {"mode": "banana", "card_ids": "x"}
        if "fake:nocard" in last:
            return {"mode": "advise", "card_ids": ["no-such-card"]}
        if "fake:advise" in last or "fake:badnum" in last or "fake:error" in last or "fake:cut" in last:
            return {"mode": "advise", "card_ids": ["missed-one-day", "no-such-card", "missed-one-day"]}
        if "fake:quest" in last:
            return {"mode": "quest", "card_ids": ["if-then"]}
        if "fake:organize" in last:
            return {"mode": "organize", "card_ids": []}
        if "fake:scope" in last:
            return {"mode": "out_of_scope", "card_ids": []}
        if "fake:modelcrisis" in last:
            return {"mode": "crisis", "card_ids": []}
        return {"mode": "listen", "card_ids": []}

    def _reply(self, messages):
        system = messages[0]["content"]
        last = messages[-1]["content"]
        if "[모드: quest]" in system:
            return "만약 저녁밥을 먹고 나면, 스트레칭을 하나만 한다."
        if "[모드: advise]" in system:
            if "fake:badnum" in last:
                return "연구에서는 73% 가 좋아졌다고 해요."
            if "fake:error" in last:
                raise RuntimeError("fake stream error")
            return "하루 빠진 것만으로 무너지지는 않는다고 연구에서 보고했어요. 다만 한 번 놓친 경우만 본 연구예요."
        if "[모드: organize]" in system:
            return "지금 할 일을 묶어 보면 이렇게 돼요."
        return "그랬군요. 그때 가장 어려웠던 게 뭐였어요?"

    FAKE_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><circle cx="32" cy="32" r="24" fill="#ffd666" stroke="#e0a800" stroke-width="3"/>'
                '<path d="M20 34q12 14 24 0" fill="none" stroke="#8a5a00" stroke-width="3" stroke-linecap="round"/>'
                '<circle cx="24" cy="26" r="3" fill="#8a5a00"/><circle cx="40" cy="26" r="3" fill="#8a5a00"/></svg>')

    def complete_text(self, messages, max_tokens):
        """도장 그림용 가짜 응답: 고정 모양 SVG. 이름에 fake:… 가 있으면 위험한 응답 등을 흉내 낸다."""
        user = messages[-1]["content"]
        if "fake:evil" in user:
            return ('<svg xmlns="http://www.w3.org/2000/svg" width="200" onload="alert(1)"><script>alert(1)</script><image href="http://x/y.png"/>'
                    '<circle cx="32" cy="32" r="20" fill="url(http://evil/x)" onclick="x()"/><rect x="1" y="1" width="9" height="9" style="fill:url(https://e/x)"/>'
                    '<a href="javascript:1"><path d="M0 0L9 9"/></a><g><path d="M1 1L5 5" fill="red"/></g></svg>')
        if "fake:big" in user:
            return '<svg xmlns="http://www.w3.org/2000/svg"><path d="' + "M0 0L1 1 " * 2500 + '"/></svg>'
        if "fake:garbage" in user:
            return "그릴 수 없어요"
        if "fake:error" in user:
            raise RuntimeError("fake svg error")
        return "설명 먼저 " + self.FAKE_SVG + " 끝"

    def chat_stream(self, messages):
        text = self._reply(messages)
        for i in range(0, len(text), 3):
            time.sleep(self.delay)
            yield text[i:i + 3]


PROVIDERS = {
    "openai": {"base_url": None, "model": "gpt-4o-mini"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-3.8-flash"},
    "claude": {"base_url": None, "model": "claude-opus-5-5"},
    "fake": {"base_url": None, "model": "fake"},
}


def make_llm(provider, api_key, model):
    if provider not in PROVIDERS:
        raise SystemExit(f"LLM_PROVIDER 값 '{provider}' 를 알 수 없습니다. openai, gemini, claude, fake 중 하나를 쓰세요.")
    model = model or PROVIDERS[provider]["model"]
    if provider == "fake":
        return FakeLLM()
    if not api_key:
        raise SystemExit("LLM_API_KEY 환경변수가 없어 시작하지 않습니다.")
    if provider == "claude":
        return ClaudeLLM(api_key, model)
    return OpenAICompatibleLLM(api_key, model, PROVIDERS[provider]["base_url"])
