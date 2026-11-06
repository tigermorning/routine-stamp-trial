"""크레딧 원장과 주문(로컬 시험용 SQLite 파일 DB 하나).

- 잔액 칸을 두지 않는다. 잔액 = credit_ledger 의 delta 합계. 기록은 고치거나 지우지 않고 쌓기만 한다.
- ref 는 유일하다(signup:<client_id> / chat:<uuid> / refund:<uuid> / order:<order_id>). 같은 일로 두 번 쌓이는 것을 DB 가 막는다.
- 차감은 잔액 확인과 -1 기록을 한 트랜잭션(BEGIN IMMEDIATE: 쓰기 잠금을 먼저 잡음)으로 묶는다.
- 주의: 서버 인스턴스 안의 파일이라 로컬 시험용이다. 운영(Cloud Run 처럼 인스턴스가 여러 개이고 파일이 사라지는 곳)에서는
  별도 DB(예: Postgres)가 필요하다.
- 상품표는 이 파일의 PRODUCTS 한 곳에만 둔다. 화면은 GET /api/products 로 받아 그대로 보여 준다.
"""
import datetime as dt
import hashlib
import os
import secrets
import sqlite3
import uuid
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "credit.db"
FREE_CREDITS = 20
CHAT_COST = 1
# 같은 주소(IP)에서 하루에 무료 크레딧을 받을 수 있는 새 client_id 수. 0 이면 제한 없음(완화책 전 상태 재현용)
FREE_GRANTS_PER_IP_PER_DAY = int(os.environ.get("FREE_GRANTS_PER_IP_PER_DAY", "3"))
# 도우미 대화는 무료이고 하루 한도만 둔다(사용자 결정 2026-11-04). 한도 숫자는 호출당 비용·파일럿 사용량을 재기 전의 임시값이며 근거가 없다.
# 한 사람(client_id)당, 그리고 같은 주소(IP)당 하루 횟수. 0 이면 제한 없음. 남은 횟수는 화면에 보이지 않는다(줄어드는 숫자 금지 원칙).
CHAT_FREE_PER_DAY = int(os.environ.get("CHAT_FREE_PER_DAY", "30"))
CHAT_FREE_PER_IP_PER_DAY = int(os.environ.get("CHAT_FREE_PER_IP_PER_DAY", str(CHAT_FREE_PER_DAY * 3)))

PRODUCTS = {
    "credits_100": {"id": "credits_100", "name": "추가 대화 100번", "amount": 1000, "credits": 100},
    "credits_550": {"id": "credits_550", "name": "추가 대화 550번", "amount": 5000, "credits": 550},
    "credits_1200": {"id": "credits_1200", "name": "추가 대화 1,200번", "amount": 10000, "credits": 1200},
}

# 일회 구매(영구 소유) 상품. 크레딧(도우미 대화용 소모형)과 화폐를 나눈다: 이 상품은 크레딧을 쓰지 않고 원 단위로 한 번 산다.
# kind 'theme' 는 화면의 색 테마(id 는 화면 THEMES 의 id), 'quote' 는 서버가 주는 «오늘의 좋은 말».
ITEMS = {
    # 디자인 테마: 색뿐 아니라 배경 무늬·카드·버튼 모양까지 바꾸는 테마(화면 index.html 의 THEMES·CSS). 가격은 임시값이다.
    # 배경 색(2026-11-06 사용자 결정): 기본·복숭아·바다만 무료이고 나머지 색은 상점에서 산다. 같은 디자인에 색만 바뀐다. 가격은 임시값이다.
    "theme_peach": {"id": "theme_peach", "kind": "theme", "theme": "peach", "name": "가을낙엽 색", "amount": 1350, "desc": "따뜻한 갈색 계열의 가을낙엽 색으로 화면 색만 바꿔요"},
    "theme_rose": {"id": "theme_rose", "kind": "theme", "theme": "rose", "name": "장미 색", "amount": 1350, "desc": "은은한 장미빛 분홍으로 화면 색만 바꿔요"},
    "theme_lime": {"id": "theme_lime", "kind": "theme", "theme": "lime", "name": "라임 색", "amount": 1350, "desc": "산뜻한 라임 연두색으로 화면 색만 바꿔요"},
    "theme_lavender": {"id": "theme_lavender", "kind": "theme", "theme": "lavender", "name": "라벤더 색", "amount": 1350, "desc": "부드러운 보라빛 라벤더 색으로 화면 색만 바꿔요"},
    "theme_sunny": {"id": "theme_sunny", "kind": "theme", "theme": "sunny", "name": "햇살 색", "amount": 1350, "desc": "따뜻한 햇살 노랑으로 화면 색만 바꿔요"},
    "theme_notebook": {"id": "theme_notebook", "kind": "theme", "theme": "notebook", "name": "공책 디자인", "amount": 4050, "desc": "줄 공책 종이 느낌으로 배경과 카드, 버튼 모양까지 바꿔요"},
    "theme_retro": {"id": "theme_retro", "kind": "theme", "theme": "retro", "name": "레트로 디자인", "amount": 4050, "desc": "도트 배경과 굵은 테두리의 옛날 게임 느낌으로 바꿔요"},
    "theme_cloud": {"id": "theme_cloud", "kind": "theme", "theme": "cloud", "name": "구름 디자인", "amount": 4050, "desc": "하늘빛 그라데이션과 말랑한 유리 카드 느낌으로 바꿔요"},
    "theme_space": {"id": "theme_space", "kind": "theme", "theme": "space", "name": "우주 행성 디자인", "amount": 4050, "desc": "검은 우주 바탕에 레트로 주황·청록 행성이 떠 있어요"},
    "theme_donut": {"id": "theme_donut", "kind": "theme", "theme": "donut", "name": "도넛 디자인", "amount": 4050, "desc": "분홍 스프링클 바탕과 도넛, 초콜릿색 둥근 카드로 바꿔요"},
    "daily_quote": {"id": "daily_quote", "kind": "quote", "name": "오늘의 한마디", "amount": 1350, "desc": "실제 격언과 속담을 포춘쿠키로 뽑아 봐요"},
    # kind 'feature' 는 화면에서만 열리고 닫히는 기능이다(데이터가 이 브라우저에 있어 서버가 막을 것이 없다)
    "history_view": {"id": "history_view", "kind": "feature", "name": "지난 기록 돌아보기", "amount": 1350, "desc": "지난 달의 도장을 달력으로 돌아봐요"},
    # 스티커 팩(2026-11-04): 누적 60일에 열리는 달력의 날짜 칸에 붙이는 스티커. 그림 목록은 화면 index.html 의 STICKER_PACKS 에 있고(id 가 같아야 함, 시험이 확인),
    # 서버는 상품·가격·소유만 다룬다. 가격은 임시값이다(근거 없음).
    "sticker_round": {"id": "sticker_round", "kind": "sticker", "name": "동글동글 스티커 팩", "amount": 1350, "desc": "달력 날짜에 붙이는 스티커 6개"},
    "sticker_daily": {"id": "sticker_daily", "kind": "sticker", "name": "하루 스티커 팩", "amount": 1350, "desc": "달력 날짜에 붙이는 스티커 6개"},
    "sticker_party": {"id": "sticker_party", "kind": "sticker", "name": "기념일 스티커 팩", "amount": 1350, "desc": "달력 날짜에 붙이는 스티커 6개"},
    "sticker_life": {"id": "sticker_life", "kind": "sticker", "name": "생활 필수 스티커 팩", "amount": 2700, "desc": "병원·약·택배·은행·빨래·장보기·청소·통화·회의·메모·이동·식사 12개"},
    "sticker_cafe": {"id": "sticker_cafe", "kind": "sticker", "name": "카페 테마 스티커 팩", "amount": 4050, "desc": "커피·차·음료·빵·디저트·카공 16개"},
    "sticker_highlight": {"id": "sticker_highlight", "kind": "sticker", "name": "하이라이트 스티커 팩", "amount": 1350, "desc": "날짜에 형광펜·물결·이중·점선 밑줄과 동그라미·붓 밑줄을 그려요"},
    "sticker_office": {"id": "sticker_office", "kind": "sticker", "name": "오피스 스티커 팩", "amount": 2700, "desc": "가방·보고서·그래프·서류·클립·프린터·노트북·일정 12개"},
    # 할 일 아이콘 스타일 팩(2026-11-04): 할 일 칸의 그림 25종을 다른 분위기로 바꾼다(그림은 화면 index.html 의 GLYPHS·ICON_PACKS, id 가 같아야 함). 가격은 임시값이다(근거 없음).
    # 메모지(2026-11-06 사용자 결정): 7종 한 묶음 대신 4종씩 두 번들. 예전에 «메모지 7종»(paper_pack)을 산 기록은 DB 에 남고 화면이 옛 7종 소유로 읽는다
    "paper_notes": {"id": "paper_notes", "kind": "paper", "name": "노트 메모지 4종 번들", "amount": 2700, "desc": "기록에 쓰는 줄 노트·모눈·점 격자·그리드 4가지 메모지"},
    "paper_mood": {"id": "paper_mood", "kind": "paper", "name": "감성 메모지 4종 번들", "amount": 2700, "desc": "기록에 쓰는 크라프트·노란 메모·편지지·수채 하늘 4가지 메모지"},
    "icons_cute": {"id": "icons_cute", "kind": "iconpack", "name": "귀여운 아이콘 팩", "amount": 2700, "desc": "할 일 그림을 표정 있는 귀여운 그림으로 바꿔요"},
    "icons_simple": {"id": "icons_simple", "kind": "iconpack", "name": "심플 선 아이콘 팩", "amount": 2700, "desc": "할 일 그림을 깔끔한 선 그림으로 바꿔요"},
    "icons_pastel": {"id": "icons_pastel", "kind": "iconpack", "name": "파스텔 스티커 아이콘 팩", "amount": 2700, "desc": "할 일 그림을 흰 테두리 파스텔 스티커로 바꿔요"},
    # 바로 열기(2026-11-04): 기록·칸·달력이 열리는 3·28·60일째를 돈으로 먼저 연다. 기능만 열리고 달성 표시(✔)·축하는 실제 일수에만 준다.
    # 가격대(2026-11-06 사용자 결정): 모든 가격은 1달러를 기준으로 한다. 꾸미기 상품은 1·2·3달러 세 가격대로 나눠 단계 선물이 오래 지속할수록 더 비싼 팩을 주게 한다(GIFT_STAGE_TIER). 1달러: 배경 색 5·동글동글·하루·기념일·하이라이트 스티커, 2달러: 메모지 번들 2·아이콘 팩 3·생활 필수·오피스 스티커, 3달러: 디자인 테마 5·카페 스티커. 1달러 ≈ 1,344원(환율 1,343.93원/달러, open.er-api.com 2026-11-04 조회)을 원 단위로 올려 1,350원으로 둔다. 기능(오늘의 한마디·지난 기록)은 1달러, 바로 열기는 기록 1달러·칸 늘리기 2달러·달력·일정 3달러, 전체는 개별 합계(6달러)보다 싼 5달러(6,750원). 환율은 오르내리므로 정기 갱신 기준은 아직 정하지 않았다(임시값). 화면이 «이전 열림이 열려 있을 때만» 보여 준다(일수는 브라우저에만 있어 서버는 모름)
    "unlock_3": {"id": "unlock_3", "kind": "unlock", "at": 3, "name": "기록 바로 열기", "amount": 1350, "desc": "메모·일기 기록을 바로 열어요. 원래는 도장을 3일 쌓으면 열려요"},
    "unlock_28": {"id": "unlock_28", "kind": "unlock", "at": 28, "name": "칸 늘리기 바로 열기", "amount": 2700, "desc": "칸을 원하는 만큼 늘릴 수 있어요. 원래는 도장을 28일 쌓으면 열려요"},
    "unlock_60": {"id": "unlock_60", "kind": "unlock", "at": 60, "name": "달력·일정 메모 바로 열기", "amount": 4050, "desc": "달력에서 지난 기록과 날짜별 일정 메모를 써요. 원래는 도장을 60일 쌓으면 열려요"},
    "unlock_all": {"id": "unlock_all", "kind": "unlock", "at": 0, "name": "모든 단계 한 번에 열기", "amount": 6750, "desc": "기록, 칸 늘리기, 달력·일정 메모 전부(따로 사는 것보다 1,000원 저렴)"},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
  order_id TEXT PRIMARY KEY,
  client_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  credits INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','done','failed')),
  payment_key TEXT,
  approved_at TEXT,
  fail_code TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS credit_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id TEXT NOT NULL,
  delta INTEGER NOT NULL,
  reason TEXT NOT NULL,
  ref TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ledger_client ON credit_ledger(client_id);
CREATE TABLE IF NOT EXISTS entitlements (
  client_id TEXT NOT NULL,
  item_id TEXT NOT NULL,
  order_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (client_id, item_id)
);
CREATE TABLE IF NOT EXISTS free_grants (
  ip_hash TEXT NOT NULL,
  day TEXT NOT NULL,
  client_id TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS stage_gifts (
  client_id TEXT NOT NULL,
  stage INTEGER NOT NULL,
  item_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (client_id, stage)
);
CREATE TABLE IF NOT EXISTS chat_usage (
  scope TEXT NOT NULL,
  key TEXT NOT NULL,
  day TEXT NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (scope, key, day)
);
CREATE TABLE IF NOT EXISTS quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ko TEXT NOT NULL,
  original TEXT,
  author TEXT NOT NULL,
  source TEXT NOT NULL,
  source_url TEXT NOT NULL,
  category TEXT,
  UNIQUE (ko, author)
);
"""


def chat_day():
    """도우미 하루 한도의 날짜. 한국 시간(UTC+9) 기준으로 자정에 바뀐다(다른 나라 사용자에게는 임시 기준)."""
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def valid_client_id(raw):
    """UUID 형식만 받는다(소문자 표준 형태로 돌려줌). 아니면 None."""
    try:
        return str(uuid.UUID(str(raw or "").strip()))
    except ValueError:
        return None


def new_order_id():
    # 토스페이먼츠 orderId 규칙: 영문 대소문자·숫자·-·_·= , 6~64자(결제 승인 API 문서). token_urlsafe 는 A-Z a-z 0-9 - _ 만 쓴다
    return "ord_" + secrets.token_urlsafe(24)


GIFT_STAGES = (3, 28, 60)  # 도장 누적 일수 단계(화면의 UNLOCKS 와 같아야 한다)
# 단계 선물은 오래 지속할수록 더 비싼 팩(2026-11-06 사용자 결정): 3일 1달러·28일 2달러·60일 3달러 가격대에서 무작위로 한 개. 그 가격대를 다 가졌으면 가까운 낮은 가격대, 그다음 높은 가격대 순으로 뽑는다
GIFT_STAGE_TIER = {3: 1350, 28: 2700, 60: 4050}
GIFT_KINDS = ("sticker", "iconpack", "paper", "theme")  # 추첨 풀: 꾸미기 상품만(기능·도장 모양·한마디·바로 열기·대화권은 제외, 사용자 결정 2026-11-05)


class Store:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        c = self._conn()
        try:
            c.executescript(SCHEMA)
        finally:
            c.close()
        try:  # 서버를 켤 때마다 격언 파일의 검증된 항목을 DB 표에 넣는다
            import quotes as _quotes
            self.seed_quotes(_quotes.load_quotes())
        except Exception:
            pass

    def _conn(self):
        c = sqlite3.connect(self.path, timeout=15, isolation_level=None)  # 트랜잭션은 직접 BEGIN 한다
        c.row_factory = sqlite3.Row
        return c

    # ---- 원장 ----
    def balance(self, client_id, conn=None):
        c = conn or self._conn()
        try:
            return c.execute("SELECT COALESCE(SUM(delta),0) FROM credit_ledger WHERE client_id=?", (client_id,)).fetchone()[0]
        finally:
            if conn is None:
                c.close()

    def recent(self, client_id, n=10):
        c = self._conn()
        try:
            rows = c.execute("SELECT delta, reason, ref, created_at FROM credit_ledger WHERE client_id=? ORDER BY id DESC LIMIT ?",
                             (client_id, n)).fetchall()
            return [dict(r) for r in rows]
        finally:
            c.close()

    def ensure_client(self, client_id, ip):
        """처음 보는 client_id 면 무료 크레딧을 쌓는다(ref signup:<id>, 유일이라 두 번 불러도 한 번).
        같은 주소에서 오늘 이미 FREE_GRANTS_PER_IP_PER_DAY 번 받았으면 쌓지 않는다. 주소는 해시만 저장한다."""
        ref = f"signup:{client_id}"
        c = self._conn()
        try:
            if c.execute("SELECT 1 FROM credit_ledger WHERE ref=?", (ref,)).fetchone():
                return False
            c.execute("BEGIN IMMEDIATE")
            if c.execute("SELECT 1 FROM credit_ledger WHERE ref=?", (ref,)).fetchone():
                c.execute("ROLLBACK")
                return False
            day = dt.date.today().isoformat()
            ip_hash = hashlib.sha256(("rs-free:" + str(ip)).encode()).hexdigest()[:32]
            if FREE_GRANTS_PER_IP_PER_DAY > 0:
                used = c.execute("SELECT COUNT(*) FROM free_grants WHERE ip_hash=? AND day=?", (ip_hash, day)).fetchone()[0]
                if used >= FREE_GRANTS_PER_IP_PER_DAY:
                    c.execute("ROLLBACK")
                    return False
            c.execute("INSERT OR IGNORE INTO free_grants(ip_hash, day, client_id) VALUES (?,?,?)", (ip_hash, day, client_id))
            c.execute("INSERT INTO credit_ledger(client_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)",
                      (client_id, FREE_CREDITS, "signup", ref, now()))
            c.execute("COMMIT")
            return True
        except Exception:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    # ---- 오늘의 한마디(실제 격언 DB) ----
    def seed_quotes(self, items):
        """검증된 격언을 표에 넣는다(같은 문장·같은 사람은 한 번만). 넣은 개수를 돌려준다."""
        c = self._conn()
        try:
            n = 0
            for i in items:
                cur = c.execute("INSERT OR IGNORE INTO quotes(ko, original, author, source, source_url, category) VALUES (?,?,?,?,?,?)",
                                (i["ko"], i.get("original", ""), i["author"], i["source"], i["source_url"], i.get("category", "")))
                n += cur.rowcount
            return n
        finally:
            c.close()

    def random_quote(self, exclude=()):
        """무작위 한 개. exclude 의 id 는 피한다(다 피하면 전체에서 뽑는다). 표가 비었으면 None."""
        c = self._conn()
        try:
            ex = [int(x) for x in exclude if str(x).isdigit()][:50]
            row = None
            if ex:
                row = c.execute("SELECT id, ko, author, source, source_url, category FROM quotes WHERE id NOT IN (%s) ORDER BY RANDOM() LIMIT 1" % ",".join("?" * len(ex)), ex).fetchone()
            if row is None:
                row = c.execute("SELECT id, ko, author, source, source_url, category FROM quotes ORDER BY RANDOM() LIMIT 1").fetchone()
            return None if row is None else {"id": row["id"], "text": row["ko"], "author": row["author"], "source": row["source"], "source_url": row["source_url"], "category": row["category"]}
        finally:
            c.close()

    def chat_take(self, client_id, ip):
        """도우미 대화 한 번을 하루 한도에서 센다(사람당·주소당 둘 다 통과해야 함). 통과하면 되돌릴 때 쓰는 토큰을, 한도를 넘었으면 None."""
        day = chat_day()
        ip_hash = hashlib.sha256(("rs-chat:" + str(ip)).encode()).hexdigest()[:32]
        scopes = [("client", client_id, CHAT_FREE_PER_DAY), ("ip", ip_hash, CHAT_FREE_PER_IP_PER_DAY)]
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            for scope, key, limit in scopes:
                row = c.execute("SELECT n FROM chat_usage WHERE scope=? AND key=? AND day=?", (scope, key, day)).fetchone()
                if limit > 0 and row and row[0] >= limit:
                    c.execute("ROLLBACK")
                    return None
            for scope, key, _ in scopes:
                c.execute("INSERT OR IGNORE INTO chat_usage(scope, key, day, n) VALUES (?,?,?,0)", (scope, key, day))
                c.execute("UPDATE chat_usage SET n=n+1 WHERE scope=? AND key=? AND day=?", (scope, key, day))
            c.execute("COMMIT")
            return (day, client_id, ip_hash)
        except Exception:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    def chat_give_back(self, token):
        """답을 만들지 못했을 때 센 것을 되돌린다(0 밑으로 내려가지 않음)."""
        day, client_id, ip_hash = token
        c = self._conn()
        try:
            for scope, key in (("client", client_id), ("ip", ip_hash)):
                c.execute("UPDATE chat_usage SET n=MAX(n-1,0) WHERE scope=? AND key=? AND day=?", (scope, key, day))
        finally:
            c.close()

    def charge(self, client_id, ref, cost=CHAT_COST):
        """잔액 확인과 -cost 기록을 한 트랜잭션으로. (성공 여부, 차감 뒤 잔액 또는 현재 잔액)."""
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            bal = self.balance(client_id, c)
            if bal < cost:
                c.execute("ROLLBACK")
                return False, bal
            c.execute("INSERT INTO credit_ledger(client_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)",
                      (client_id, -cost, "chat", ref, now()))
            c.execute("COMMIT")
            return True, bal - cost
        except Exception:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    def refund(self, client_id, charge_ref, cost=CHAT_COST):
        """답을 만들지 못한 차감을 되돌리는 +줄(ref refund:<같은 uuid>). 지우지 않고 새 줄을 쌓는다."""
        ref = "refund:" + charge_ref.split(":", 1)[1]
        c = self._conn()
        try:
            c.execute("INSERT OR IGNORE INTO credit_ledger(client_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)",
                      (client_id, cost, "refund", ref, now()))
        finally:
            c.close()

    # ---- 일회 구매 상품(영구 소유) ----
    def owned(self, client_id):
        c = self._conn()
        try:
            return [r[0] for r in c.execute("SELECT item_id FROM entitlements WHERE client_id=? ORDER BY item_id", (client_id,))]
        finally:
            c.close()

    def has_item(self, client_id, item_id):
        return item_id in self.owned(client_id)

    # ---- 단계 선물: 도장 누적 3·28·60일 단계를 지나면 꾸미기 팩 하나를 무작위로 준다 ----
    def stage_gift(self, client_id, stage):
        """(client, stage)마다 한 번만 준다. 서버는 도장 일수를 모르므로 단계 도달은 화면 말을 믿는다(남용은 단계당 1회로만 줄임).
        이미 받았으면 같은 결과를 돌려준다. 줄 팩이 없으면 item None."""
        if stage not in GIFT_STAGES:
            raise ValueError("stage")
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT item_id FROM stage_gifts WHERE client_id=? AND stage=?", (client_id, stage)).fetchone()
            if row:
                c.execute("ROLLBACK")
                return {"item": ITEMS.get(row["item_id"]), "already": True}
            have = {r[0] for r in c.execute("SELECT item_id FROM entitlements WHERE client_id=?", (client_id,))}
            cands = [i for i in ITEMS.values() if i["kind"] in GIFT_KINDS and i["id"] not in have]
            tier = GIFT_STAGE_TIER[stage]
            prices = sorted({i["amount"] for i in cands})
            order = [tier] + sorted([p for p in prices if p < tier], reverse=True) + sorted([p for p in prices if p > tier])
            pool = next(([i for i in cands if i["amount"] == p] for p in order if any(i["amount"] == p for i in cands)), [])
            pick = secrets.choice(pool) if pool else None
            c.execute("INSERT INTO stage_gifts(client_id, stage, item_id, created_at) VALUES (?,?,?,?)",
                      (client_id, stage, pick["id"] if pick else "", now()))
            if pick:
                c.execute("INSERT OR IGNORE INTO entitlements(client_id, item_id, order_id, created_at) VALUES (?,?,?,?)",
                          (client_id, pick["id"], f"gift:{stage}", now()))
            c.execute("COMMIT")
            return {"item": pick, "already": False}
        except Exception:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    # ---- 주문 ----
    def create_order(self, client_id, product):
        order_id = new_order_id()
        c = self._conn()
        try:
            c.execute("INSERT INTO orders(order_id, client_id, product_id, amount, credits, status, created_at) VALUES (?,?,?,?,?,?,?)",
                      (order_id, client_id, product["id"], product["amount"], product.get("credits", 0), "pending", now()))
        finally:
            c.close()
        return self.get_order(order_id)

    def get_order(self, order_id):
        c = self._conn()
        try:
            r = c.execute("SELECT * FROM orders WHERE order_id=?", (str(order_id or ""),)).fetchone()
            return dict(r) if r else None
        finally:
            c.close()

    def complete_order(self, order_id, payment_key, approved_at):
        """대기 → 완료 바꾸기와 +credits 줄(ref order:<id>)을 한 트랜잭션으로. 이미 대기가 아니면 아무것도 하지 않고 False."""
        c = self._conn()
        try:
            c.execute("BEGIN IMMEDIATE")
            cur = c.execute("UPDATE orders SET status='done', payment_key=?, approved_at=? WHERE order_id=? AND status='pending'",
                            (payment_key, approved_at, order_id))
            if cur.rowcount != 1:
                c.execute("ROLLBACK")
                return False
            o = c.execute("SELECT client_id, credits, product_id FROM orders WHERE order_id=?", (order_id,)).fetchone()
            if o["product_id"] in ITEMS:  # 일회 구매 상품: 크레딧 대신 소유 기록(같은 상품은 한 번만)
                c.execute("INSERT OR IGNORE INTO entitlements(client_id, item_id, order_id, created_at) VALUES (?,?,?,?)",
                          (o["client_id"], o["product_id"], order_id, now()))
            else:
                c.execute("INSERT INTO credit_ledger(client_id, delta, reason, ref, created_at) VALUES (?,?,?,?,?)",
                          (o["client_id"], o["credits"], "order", f"order:{order_id}", now()))
            c.execute("COMMIT")
            return True
        except Exception:
            if c.in_transaction:
                c.execute("ROLLBACK")
            raise
        finally:
            c.close()

    def fail_order(self, order_id, code):
        c = self._conn()
        try:
            cur = c.execute("UPDATE orders SET status='failed', fail_code=? WHERE order_id=? AND status='pending'", (str(code)[:60], order_id))
            return cur.rowcount == 1
        finally:
            c.close()
