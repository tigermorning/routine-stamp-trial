"""도우미(루틴 코치 친구)의 규칙. 모델 판단과 상관없이 코드로 지키는 것: 입력 길이, 위기 키워드, 카드 id 검사, 숫자 검사.

대화 내용은 저장하지도 로그에 남기지도 않는다(이 모듈은 로그를 쓰지 않는다).
"""
import re

import cards as cardlib

from policy import *  # noqa: F401,F403  범위·페르소나·안전 규칙·한도는 policy.py 한 곳에 있다


def is_crisis(text):
    low = text.lower()
    return any(k in low for k in CRISIS_KEYWORDS)


def plan_messages(history, todos_n=0):  # todos_n: 이전 버전 화면과의 호환용 인자. 이제 분류에는 쓰지 않는다(할 일 목록이 없어졌다)
    convo = "\n".join(f"{'사용자' if m['role'] == 'user' else '도우미'}: {m['content']}" for m in history)
    return PLAN_SYSTEM, f"[카드 목록]\n{cardlib.catalogue()}\n\n[대화]\n{convo}"


def clean_history(raw):
    """화면에서 받은 대화를 정리한다. 마지막은 반드시 사용자 말이어야 한다. 아니면 None."""
    out = []
    for m in raw or []:
        role = m.get("role")
        text = " ".join(str(m.get("content") or "").split())[:MAX_MSG]
        if role in ("user", "assistant") and text:
            out.append({"role": role, "content": text})
    merged = []
    for m in out:  # 같은 쪽 말이 이어지면 하나로 합친다(일부 제공사는 번갈아 오는 대화만 받는다)
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] = (merged[-1]["content"] + "\n" + m["content"])[:MAX_MSG]
        else:
            merged.append(dict(m))
    out = merged[-MAX_TURNS:]
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out if out and out[-1]["role"] == "user" else None


def clean_context(ctx):
    """사용자가 보여 주기로 한 칸 이름·일수. 없으면 None."""
    if not isinstance(ctx, dict):
        return None
    slots = [" ".join(str(s).split())[:30] for s in (ctx.get("slots") or [])[:MAX_SLOTS] if str(s).strip()]
    try:
        days = max(0, min(int(ctx.get("days", 0)), 100000))
    except (TypeError, ValueError):
        days = 0
    return {"slots": slots, "days": days} if slots else None


def clean_todos(raw):
    return [" ".join(str(t).split())[:MAX_TODO_LEN] for t in (raw or [])[:MAX_TODOS] if str(t).strip()]


_NAME_STRIP = re.compile(r"[\"'`<>{}\[\]\\\r\n\t]")


def clean_character(raw):
    """화면에서 받은 캐릭터 설정을 허용값으로 정리한다. 필드가 없거나 객체가 아니면 None(= 설정 없음, 기본 동작).
    허용 목록 밖의 값은 기본값으로 바꾸고, 이름은 괄호·따옴표·줄바꿈을 걷어 내고 20자로 자른다."""
    if not isinstance(raw, dict):
        return None
    d = CHARACTER_DEFAULTS
    speech = raw.get("speech") if raw.get("speech") in SPEECH_CHOICES else d["speech"]
    emoji = raw.get("emoji") if raw.get("emoji") in EMOJI_CHOICES else d["emoji"]
    name = " ".join(_NAME_STRIP.sub(" ", str(raw.get("name") or "")).split())[:MAX_NAME]
    return {"name": name, "speech": speech, "emoji": emoji}


def ends_with_question(text):
    return text.strip().rstrip(" 😊🌟✨🙂😄😉👍💪🏃‍♂️🎉").endswith(("?", "？"))


def variation_hint(history):
    """직전 도우미 말이 질문으로 끝났으면 이번에는 질문으로 끝내지 않게 한다(같은 형태 되풀이 방지).
    모델의 판단에 맡기지 않고 서버가 직전 말을 보고 정한다."""
    assistants = [m["content"] for m in (history or []) if m["role"] == "assistant"]
    if not assistants or not ends_with_question(assistants[-1]):
        return ""
    twice = len(assistants) >= 2 and ends_with_question(assistants[-2])
    return ("[이번 답의 형태] 직전 도우미 말이 질문으로 끝났다" + ("(그 전 말도 질문이었다)" if twice else "")
            + ". 이번 답은 질문으로 끝내지 않는다. 사용자가 방금 한 말을 되받아 요약하거나, 선택지 두 개를 주거나, 사용자가 말한 범위 안에서 다음 한 걸음을 제안하며 마무리한다.")


EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐❤]")
POLITE_END = re.compile(r"(요|니다|니까|세요|죠|네요|군요)$")
_SENT = re.compile(r"[^.!?。！？\n]+[.!?。！？]?")
_HANGUL = re.compile("[가-힣]")


def polite_ratio(text):
    """한국어 문장 중 존댓말로 끝나는 문장의 비율(휴리스틱). 한글 문장이 없으면 None."""
    ends = []
    for s in _SENT.findall(text):
        if not any(ch.isalpha() for ch in s):
            continue
        s = EMOJI.sub("", s).strip().rstrip(".!?。！？~ ")
        if s and _HANGUL.search(s):
            ends.append(bool(POLITE_END.search(s)))
    return sum(ends) / len(ends) if ends else None


OMITTED = "(앞선 도우미 말은 말투 설정이 달라 생략했어요.)"


def neutralize_history(history, character):
    """말투 설정을 바꾼 직후에는 앞선 도우미 말이 옛 말투라, 모델이 그걸 따라 한다(2026-10-21 실측: 존댓말 설정이 반말로 답하는 일 3/3).
    한국어 도우미 말 중 지금 설정과 말투가 어긋난 것은 내용 대신 생략 표시로 바꿔 모델에 보낸다(화면·저장 기록은 그대로).
    캐릭터 설정이 없거나 한글이 아닌 말은 건드리지 않는다."""
    if not character or not history:
        return history
    out = []
    for m in history:
        if m["role"] == "assistant":
            r = polite_ratio(m["content"])
            if r is not None and ((character["speech"] == "casual" and r > 0.6) or (character["speech"] == "polite" and r < 0.4)):
                m = {"role": "assistant", "content": OMITTED}
        out.append(m)
    return out


def with_tone_reminder(history, character, extra=""):
    """모델에 보내는 대화의 마지막 사용자 말 뒤에 말투 한 줄(과 extra 한 줄)을 붙인 사본을 돌려준다(원본·화면·저장 기록은 그대로).
    앞선 도우미 말투를 모델이 따라 하는 것을 막고(2026-10-21 실측 2/6 → 6/6), 시스템 지시보다 센 '마지막 말 뒤' 자리에 형태 힌트도 둔다.
    캐릭터 설정도 extra 도 없으면 그대로 돌려준다."""
    notes = ([TONE_REMINDER[character["speech"]]] if character else []) + ([extra] if extra else [])
    if not notes or not history or history[-1]["role"] != "user":
        return history
    out = [dict(m) for m in history]
    out[-1]["content"] = out[-1]["content"] + "\n\n" + "\n".join(notes)
    return out


APP_NUMBERS = set(re.findall(r"\d+(?:[.,]\d+)?", APP_GUIDE))  # 앱 안내에 나오는 숫자(3·28·60·6·10 …). 앱 이야기에서만 말해도 된다


def build_system(mode, cards, ctx, todos, character=None, history=None):
    """규칙(안전·범위·카드·위기)은 캐릭터 설정보다 앞에 있고, 설정으로 바뀌지 않는다. 설정은 말투 줄과 이름 칸만 바꾼다."""
    parts = [fixed_rules(tone_for(character), with_character=bool(character))]
    if name_block(character):
        parts.append(name_block(character))
    parts.append(MODE_RULES[mode])
    if mode in ("advise", "quest") and cards:
        parts.append("[근거 카드]\n" + cardlib.card_block(cards))
    parts.append(APP_GUIDE)
    if mode in CHAT_MODES and variation_hint(history):
        parts.append(variation_hint(history))
    info = []
    if ctx:
        info.append(f"[이 앱에 저장된 내 칸(칸 이름과 도장이 쌓인 일수)] 칸: {', '.join(ctx['slots'])} / 도장이 쌓인 일수: {ctx['days']}")
    if todos:
        info.append("[내 할 일]\n" + "\n".join(f"- {t}" for t in todos))
    return "\n\n".join(parts + info)


NUM = re.compile(r"\d+(?:[.,]\d+)?")


def numbers_ok(reply, cards, history, ctx, todos, extra=()):
    """답에 들어 있는 숫자가 카드의 수치이거나 사용자가 쓴 말에 있던 숫자(앱 이야기면 앱 안내의 숫자 extra)인지 검사한다.

    아라비아 숫자만 본다(한글 수사나 다른 문자 숫자는 못 거른다). 근사 검사이며 위반율은 평가 세트로 잰다.
    """
    allowed = {n for c in cards for n in c["numbers"]} | set(extra)
    pool = " ".join([m["content"] for m in history] + todos + ((ctx or {}).get("slots") or []))
    allowed |= set(NUM.findall(pool))
    if ctx:
        allowed.add(str(ctx["days"]))
    for m in NUM.finditer(reply):
        n = m.group(0)
        if n in allowed:
            continue
        return False  # 프롬프트가 숫자 사용을 막았으므로 "5분", "1회" 같은 지어낸 크기도 통과시키지 않는다
    return True


class Limiter:
    """모델이 주는 조각을 길이 상한과 한 줄 규칙에 맞게 걸러 낸다(퀘스트는 한 문장·한 줄)."""

    def __init__(self, max_chars, one_line=False):
        self.max, self.one_line, self.out, self.done, self.started = max_chars, one_line, "", False, False

    def feed(self, piece):
        if self.done:
            return ""
        if not self.started:
            piece = piece.lstrip(" \t\r\n\"'`“”‘’「」*-•·")
            if not piece:
                return ""
            self.started = True
        if self.one_line and "\n" in piece:
            piece, self.done = piece.split("\n", 1)[0], True
        room = self.max - len(self.out)
        if len(piece) >= room:
            piece, self.done = piece[:room], True
        self.out += piece
        return piece
