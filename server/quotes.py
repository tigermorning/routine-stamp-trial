"""오늘의 한마디: 실제로 있는 격언·속담 모음(server/quotes.json)을 읽어 서버 DB 표(quotes)에 넣는다.

- 이 앱이 지어낸 문장은 넣지 않는다(사용자 지적 2026-11-04: 지어낸 말은 감동이 없다). 속담과 저작권이 끝난 고전만 쓰고, 항목마다 출처와 확인한 주소를 적는다.
- SNS(Pinterest·Instagram)에 퍼진 문구는 모으지 않는다(저작권·약관·출처 불명). 항목은 verified=true 이고 ko·author·source·source_url 이 모두 있는 것만 받는다.
"""
import json
from pathlib import Path

QUOTES_FILE = Path(__file__).resolve().parent / "quotes.json"
REQUIRED = ("ko", "author", "source", "source_url")


def valid(item):
    return isinstance(item, dict) and item.get("verified") is True and all(str(item.get(k, "")).strip() for k in REQUIRED)


def load_quotes(path=None):
    p = Path(path) if path else QUOTES_FILE
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [i for i in data if valid(i)] if isinstance(data, list) else []


AFFIRM_FILE = Path(__file__).resolve().parent / "affirmations.json"


def load_affirmations(path=None):
    """언어별 일상 응원 문장({언어: [문장…]}). 2026-11-06 사용자 결정으로 격언 대신 쓴다(직접 쓴 짧은 문장, 외부 문구를 가져오지 않는다)."""
    p = Path(path) if path else AFFIRM_FILE
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {k: [t for t in v if isinstance(t, str) and t.strip()] for k, v in d.items() if isinstance(v, list)} if isinstance(d, dict) else {}


def pick_affirmation(lang, exclude=()):
    """lang 문장 중 최근에 본 번호(exclude, 1부터)를 피해 무작위 하나. 모르는 언어는 영어. {id,text,author,source,source_url,category}"""
    import random
    d = load_affirmations()
    items = d.get(lang) or d.get("en") or []
    if not items:
        return None
    ex = {int(x) for x in exclude}
    ids = [i for i in range(1, len(items) + 1) if i not in ex] or list(range(1, len(items) + 1))
    i = random.choice(ids)
    return {"id": i, "text": items[i - 1], "author": "", "source": "", "source_url": "", "category": "affirmation"}
