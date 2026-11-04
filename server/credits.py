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

PRODUCTS = {
    "credits_100": {"id": "credits_100", "name": "크레딧 100개", "amount": 1000, "credits": 100},
    "credits_550": {"id": "credits_550", "name": "크레딧 550개", "amount": 5000, "credits": 550},
    "credits_1200": {"id": "credits_1200", "name": "크레딧 1,200개", "amount": 10000, "credits": 1200},
}

# 일회 구매(영구 소유) 상품. 크레딧(도우미 대화용 소모형)과 화폐를 나눈다: 이 상품은 크레딧을 쓰지 않고 원 단위로 한 번 산다.
# kind 'theme' 는 화면의 색 테마(id 는 화면 THEMES 의 id), 'quote' 는 서버가 주는 «오늘의 좋은 말».
ITEMS = {
    "theme_ocean": {"id": "theme_ocean", "kind": "theme", "theme": "ocean", "name": "바다 테마", "amount": 1000, "desc": "색을 바꿔요"},
    "theme_forest": {"id": "theme_forest", "kind": "theme", "theme": "forest", "name": "숲 테마", "amount": 1000, "desc": "색을 바꿔요"},
    "theme_rose": {"id": "theme_rose", "kind": "theme", "theme": "rose", "name": "장미 테마", "amount": 1000, "desc": "색을 바꿔요"},
    "daily_quote": {"id": "daily_quote", "kind": "quote", "name": "오늘의 좋은 말", "amount": 1000, "desc": ""},
    # kind 'feature'/'stamp' 는 화면에서만 열리고 닫히는 기능이다(데이터가 이 브라우저에 있어 서버가 막을 것이 없다)
    "history_view": {"id": "history_view", "kind": "feature", "name": "지난 기록 돌아보기", "amount": 1000, "desc": "지난 달의 도장을 달력으로 돌아봐요"},
    "stamp_shapes": {"id": "stamp_shapes", "kind": "stamp", "name": "도장 모양 바꾸기", "amount": 1000, "desc": "동그라미 말고 네 가지 모양 중에 골라요"},
    # 열림 건너뛰기(2026-11-04): 칸·색·달력이 열리는 3·28·60일째를 돈으로 먼저 연다. 기능만 열리고 달성 표시(✔)·축하는 실제 일수에만 준다.
    # 가격은 «열림이 복잡해질수록 조금씩 비싸게, 전체는 개별 합계보다 싸게» 라는 사용자 방향에 맞춘 임시값이다(근거 없음).
    # 5달러 ≈ 6,720원(환율 1,343.93원/달러, open.er-api.com 2026-11-04 조회)을 기준으로 전체를 6,500원으로 잡았다. 화면이 «이전 열림이 열려 있을 때만» 보여 준다(일수는 브라우저에만 있어 서버는 모름).
    "unlock_3": {"id": "unlock_3", "kind": "unlock", "at": 3, "name": "3일째 열림 건너뛰기", "amount": 1500, "desc": "4번째 칸과 복숭아 색이 바로 열려요"},
    "unlock_28": {"id": "unlock_28", "kind": "unlock", "at": 28, "name": "28일째 열림 건너뛰기", "amount": 2500, "desc": "5번째 칸과 라벤더 색이 바로 열려요"},
    "unlock_60": {"id": "unlock_60", "kind": "unlock", "at": 60, "name": "60일째 열림 건너뛰기", "amount": 3500, "desc": "6번째 칸, 햇살 색, 달력·일정 메모가 바로 열려요"},
    "unlock_all": {"id": "unlock_all", "kind": "unlock", "at": 0, "name": "모든 열림 건너뛰기", "amount": 6500, "desc": "3·28·60일째 열림을 한 번에 열어요(개별로 사는 것보다 1,000원 저렴)"},
}

# 오늘의 좋은 말(날짜로 하나를 고름). 유명인 말을 옮기지 않고 이 앱이 쓴 짧은 응원 문장이다.
QUOTES = [
    "오늘 한 칸이면 충분해요.", "빠뜨린 날이 있어도 쌓은 도장은 그대로예요.", "작게 해도 한 것은 한 거예요.",
    "어제보다 한 칸만 더 가벼워지면 돼요.", "쉬어 간 날도 내일의 힘이 돼요.", "완벽한 하루보다 이어지는 하루가 좋아요.",
    "시작이 반이라면, 오늘 도장이 그 반이에요.", "천천히 쌓는 사람이 오래 가요.", "오늘의 나에게 도장 하나 선물해요.",
    "해야 할 일보다 할 수 있는 일부터요.", "마음이 무거운 날엔 가장 쉬운 칸부터요.", "도장은 쌓이고, 쌓인 것은 사라지지 않아요.",
    "비교는 어제의 나하고만 해요.", "조금씩, 그래도 계속.", "오늘 해낸 것을 먼저 세어 봐요.",
    "쉬운 날도 어려운 날도 한 칸은 한 칸이에요.", "지금 이 순간이 새로 시작하기 좋은 때예요.", "나를 재촉하지 않아도 괜찮아요.",
    "한 칸 한 칸이 모여 나만의 길이 돼요.", "오늘은 오늘만큼만 해요.", "해낸 날이 많아질수록 마음도 단단해져요.",
    "잠깐 멈춰도 길은 그대로 있어요.", "작은 도장이 큰 하루를 만들어요.", "오늘의 나는 어제보다 한 걸음 앞에 있어요.",
    "잘하고 있어요, 지금 이대로도.", "기분이 어떻든 도장은 찍을 수 있어요.", "조급해하지 말고 꾸준히 가요.",
    "오늘의 한 칸이 내일의 습관이 돼요.", "이어 가는 마음이 가장 큰 재주예요.", "오늘도 여기 와 준 것만으로 반은 했어요.",
    "내 속도가 내 정답이에요.",
]


def quote_of_day(day=None):
    d = day or dt.date.today()
    return QUOTES[d.toordinal() % len(QUOTES)]


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
"""


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


class Store:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        c = self._conn()
        try:
            c.executescript(SCHEMA)
        finally:
            c.close()

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
