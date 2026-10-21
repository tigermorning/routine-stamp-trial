"""근거 카드 불러오기와 검사. 도우미가 방법을 말할 때 쓰는 내용은 여기 카드에서만 나온다."""
import json
from pathlib import Path

LEVELS = ("full", "partial", "abstract")  # 원문 확인 / 원문 일부 / 초록만
PATH = Path(__file__).resolve().parent / "cards.json"


def load_cards(path=PATH):
    cards = json.loads(Path(path).read_text(encoding="utf-8"))["cards"]
    ids = set()
    for c in cards:
        assert c["id"] not in ids, f"카드 id 중복: {c['id']}"
        ids.add(c["id"])
        assert c["level"] in LEVELS, f"{c['id']}: level 오류"
        assert c["sources"] and all(s.get("doi") and s.get("short") for s in c["sources"]), f"{c['id']}: 출처 없음"
        assert c["can_say"] and c["limits"] and c["summary"], f"{c['id']}: 빈 칸"
        # 수치는 원문을 확인한 카드에서만 말할 수 있다
        assert c["level"] == "full" or not c["numbers"], f"{c['id']}: 원문 확인이 아닌데 수치가 있음"
        # 카드 수준은 출처 중 가장 낮은 확인 수준이어야 한다
        order = {"full": 0, "partial": 1, "abstract": 2}
        worst = max((s["checked"].split()[0] for s in c["sources"]), key=lambda x: order[x])
        assert order[c["level"]] >= order[worst], f"{c['id']}: 카드 수준이 출처보다 높음"
    return {c["id"]: c for c in cards}


CARDS = load_cards()


def catalogue(cards=None):
    """계획 단계에서 모델이 고를 수 있는 카드 목록(id와 어떤 고민에 맞는지)."""
    return "\n".join(f"{c['id']} | {', '.join(c['topics'])}" for c in (cards or CARDS).values())


def pick(ids):
    """모델이 고른 id 중 실제 있는 카드만, 중복 없이 최대 2장."""
    out = []
    for i in ids if isinstance(ids, list) else []:
        if isinstance(i, str) and i in CARDS and CARDS[i] not in out:
            out.append(CARDS[i])
    return out[:2]


def card_block(cards):
    """답을 만들 때 시스템 지시문에 넣는 카드 본문."""
    parts = []
    for c in cards:
        nums = ", ".join(c["numbers"]) if c["numbers"] else "없음(수치를 말하지 않는다)"
        src = "; ".join(f"{s['short']}({s['checked']})" for s in c["sources"])
        parts.append(f"[카드 {c['id']}] 확인 수준: {c['level']}\n요약: {c['summary']}\n말해도 되는 것: {' / '.join(c['can_say'])}\n한계: {c['limits']}\n써도 되는 수치: {nums}\n출처: {src}")
    return "\n\n".join(parts)


def meta(cards):
    """화면에 '근거' 표시를 하기 위한 정보."""
    return [{"id": c["id"], "level": c["level"],
             "sources": [{"short": s["short"], "doi": s["doi"], "checked": s["checked"].split()[0]} for s in c["sources"]]}
            for c in cards]
