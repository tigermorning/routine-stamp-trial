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
    "daily_quote": {"id": "daily_quote", "kind": "quote", "name": "오늘의 한마디", "amount": 1350, "desc": "하루에 도움이 되는 응원 한마디를 포춘쿠키로 뽑아 봐요"},
    # kind 'feature' 는 화면에서만 열리고 닫히는 기능이다(데이터가 이 브라우저에 있어 서버가 막을 것이 없다)
    "history_view": {"id": "history_view", "kind": "feature", "name": "지난 기록 돌아보기", "amount": 1350, "desc": "지난 달의 도장을 달력으로 돌아봐요"},
    # 스티커 팩(2026-11-04): 누적 60일에 열리는 달력의 날짜 칸에 붙이는 스티커. 그림 목록은 화면 index.html 의 STICKER_PACKS 에 있고(id 가 같아야 함, 시험이 확인),
    # 서버는 상품·가격·소유만 다룬다. 가격은 임시값이다(근거 없음).
    "sticker_round": {"id": "sticker_round", "kind": "sticker", "name": "동물·반려 스티커 팩", "amount": 1350, "desc": "강아지·고양이부터 동물원·바다 친구들까지 — 스티커 53개"},
    "sticker_daily": {"id": "sticker_daily", "kind": "sticker", "name": "집안일·생활 스티커 팩", "amount": 1350, "desc": "청소·빨래·택배·은행 업무까지 살림과 생활 처리 — 스티커 30개"},
    "sticker_party": {"id": "sticker_party", "kind": "sticker", "name": "기념일·파티 스티커 팩", "amount": 1350, "desc": "생일·결혼식·명절·연말까지 축하하는 날 — 스티커 30개"},
    "sticker_life": {"id": "sticker_life", "kind": "sticker", "name": "운동·활동 스티커 팩", "amount": 2700, "desc": "헬스·러닝·구기 종목·겨울 스포츠까지 몸을 움직이는 날 — 스티커 53개"},
    "sticker_cafe": {"id": "sticker_cafe", "kind": "sticker", "name": "음식·카페 스티커 팩", "amount": 4050, "desc": "밥·면·고기·디저트·커피·술까지 먹고 마시는 하루 — 스티커 57개"},
    "sticker_highlight": {"id": "sticker_highlight", "kind": "sticker", "name": "하이라이트 스티커 팩", "amount": 1350, "desc": "날짜에 형광펜(노랑·초록·파랑·분홍·주황·보라·민트)·굵은 밑줄·줄무늬·물결·이중·점선·실선·파선 밑줄과 동그라미·네모·붓 밑줄 17가지를 그려요"},
    "sticker_office": {"id": "sticker_office", "kind": "sticker", "name": "일·공부 스티커 팩", "amount": 2700, "desc": "출근·회의·보고서·시험·자격증까지 일과 배움 — 스티커 45개"},
    # 새 팩 3종(2026-11-06 사용자 요청: 네이버 캘린더처럼 화풍이 서로 다른 스티커. 네이버 그림은 베끼지 않고 화풍 구성만 참고한 이 앱 전용 그림)
    "sticker_dojang": {"id": "sticker_dojang", "kind": "sticker", "name": "사람들 일상 스티커 팩", "amount": 2700, "desc": "학생·직장인·요리사부터 인사·발표·아이고까지 사람이 사는 모습 — 스티커 46개"},
    "sticker_seal": {"id": "sticker_seal", "kind": "sticker", "name": "참 잘했어요 도장 팩", "amount": 1350, "desc": "참 잘했어요·최고예요·100점·해냈다 등 잉크 도장 40종"},
    "sticker_washi": {"id": "sticker_washi", "kind": "sticker", "name": "마스킹테이프 팩", "amount": 2700, "desc": "줄무늬·깅엄·별·하트·무지개 등 다이어리 꾸미기 테이프 40종"},
    # 감정·날씨·D-day 팩(2026-11-06 사용자 요청): 과일 캐릭터 감정, 펠트 바느질 날씨, 뜯는 달력·풍선·티켓·깃발 카운터
    "sticker_fruit": {"id": "sticker_fruit", "kind": "sticker", "name": "기분·마음 스티커 팩", "amount": 2700, "desc": "기쁨·설렘·피곤·불안·분노까지 오늘의 기분 — 스티커 44개"},
    "sticker_felt": {"id": "sticker_felt", "kind": "sticker", "name": "날씨·계절 스티커 팩", "amount": 2700, "desc": "맑음·비·눈·미세먼지부터 봄 벚꽃·가을 단풍까지 — 스티커 36개"},
    "sticker_dday": {"id": "sticker_dday", "kind": "sticker", "name": "D-day 카운터 팩", "amount": 1350, "desc": "D-100·D-30·D-7·D-DAY·D+100·D+365 등 뜯는 달력·풍선·티켓·깃발 카운터 47종"},
    # 일정 모음(2026-11-06 사용자 요청): 피부관리·네일·병원·운동·모임·공부·여행·경조사까지 일상 일정 거의 전부를 한 팩에
    "sticker_sched": {"id": "sticker_sched", "kind": "sticker", "name": "건강·병원 스티커 팩", "amount": 2700, "desc": "병원·약·검사·몸 관리까지 건강과 관련된 하루 — 스티커 30개"},
    # 화풍 더 섞기 4종(2026-11-06 사용자 요청): 낙서(삐뚤빼뚤 선), 말랑 3D(광택 입체), 손글씨 레터링(한글), 마커 표시
    "sticker_doodle": {"id": "sticker_doodle", "kind": "sticker", "name": "여행·이동 스티커 팩", "amount": 2700, "desc": "비행기·기차·캠핑·드라이브까지 떠나고 오가는 날 — 스티커 47개"},
    "sticker_glossy": {"id": "sticker_glossy", "kind": "sticker", "name": "취미·여가 스티커 팩", "amount": 4050, "desc": "영화·게임·음악·그림·뜨개질까지 혼자서도 함께도 즐기는 시간 — 스티커 49개"},
    "sticker_letter": {"id": "sticker_letter", "kind": "sticker", "name": "손글씨 레터링 스티커 팩", "amount": 1350, "desc": "해냈다·파이팅·고마워·수고했어·힘내 등 한글 글자 스티커 16종"},
    "sticker_marker": {"id": "sticker_marker", "kind": "sticker", "name": "마커 표시 스티커 팩", "amount": 1350, "desc": "동그라미·체크·화살표·물결 밑줄·형광 박스 등 마커로 그은 표시 16종"},
    # 일상 테마 확장(2026-11-09 사용자 요청): 쇼핑·미용·만남·식물 팩
    "sticker_money": {"id": "sticker_money", "kind": "sticker", "name": "쇼핑·돈 스티커 팩", "amount": 2700, "desc": "장보기·온라인 쇼핑·저축·투자까지 돈과 소비 — 스티커 31개"},
    "sticker_beauty": {"id": "sticker_beauty", "kind": "sticker", "name": "미용·패션 스티커 팩", "amount": 2700, "desc": "미용실·네일·스킨케어·옷 입기까지 가꾸는 시간 — 스티커 46개"},
    "sticker_love": {"id": "sticker_love", "kind": "sticker", "name": "만남·사랑 스티커 팩", "amount": 2700, "desc": "친구·가족·연인과 만나고 마음을 나누는 날 — 스티커 47개"},
    "sticker_plant": {"id": "sticker_plant", "kind": "sticker", "name": "식물·자연 스티커 팩", "amount": 1350, "desc": "새싹·화분·꽃·나무·산책길까지 초록과 자연 — 스티커 45개"},
    # 취미·여행 확장(2026-11-09 사용자 요청): 세계 명소·음악·게임·그림·영화·독서·캠핑·정원·사진·응원 팩(Iconify 오픈 아이콘 세트)
    "sticker_world": {"id": "sticker_world", "kind": "sticker", "name": "세계 명소 스티커 팩", "amount": 4050, "desc": "에펠탑·타지마할·만리장성·자유의 여신상까지 세계 곳곳의 명소와 풍경 — 스티커 58개"},
    "sticker_music": {"id": "sticker_music", "kind": "sticker", "name": "음악·악기 스티커 팩", "amount": 2700, "desc": "기타·피아노·바이올린·드럼부터 마이크·헤드폰·LP까지 음악 하는 시간 — 스티커 47개"},
    "sticker_game": {"id": "sticker_game", "kind": "sticker", "name": "게임·놀이 스티커 팩", "amount": 2700, "desc": "게임기·보드게임·퍼즐·체스·카드까지 노는 시간 — 스티커 49개"},
    "sticker_art": {"id": "sticker_art", "kind": "sticker", "name": "그림·공예 스티커 팩", "amount": 2700, "desc": "그림·뜨개질·도자기·종이접기까지 손으로 만드는 시간 — 스티커 30개"},
    "sticker_cinema": {"id": "sticker_cinema", "kind": "sticker", "name": "영화·공연·전시 스티커 팩", "amount": 2700, "desc": "영화관·연극·뮤지컬·미술관까지 보러 가는 날 — 스티커 34개"},
    "sticker_read": {"id": "sticker_read", "kind": "sticker", "name": "독서·글쓰기 스티커 팩", "amount": 2700, "desc": "책·서점·일기·편지·타자기까지 읽고 쓰는 시간 — 스티커 32개"},
    "sticker_outdoor": {"id": "sticker_outdoor", "kind": "sticker", "name": "캠핑·낚시·등산 스티커 팩", "amount": 2700, "desc": "텐트·모닥불·낚시·등산까지 밖에서 보내는 시간 — 스티커 31개"},
    "sticker_garden": {"id": "sticker_garden", "kind": "sticker", "name": "정원·반려식물 스티커 팩", "amount": 2700, "desc": "화분·새싹·물주기·텃밭까지 식물 가꾸는 시간 — 스티커 37개"},
    "sticker_photo": {"id": "sticker_photo", "kind": "sticker", "name": "사진·영상·SNS 스티커 팩", "amount": 2700, "desc": "사진·브이로그·라이브·해시태그까지 남기고 나누는 시간 — 스티커 46개"},
    "sticker_cheer": {"id": "sticker_cheer", "kind": "sticker", "name": "응원·스포츠 관람 스티커 팩", "amount": 2700, "desc": "경기장·응원·메달·트로피까지 보고 응원하는 날 — 스티커 40개"},
    # 스타일 팩(2026-11-09 사용자 요청: 구글 캘린더식 이모지에서 벗어나 팩마다 질감·색감·모양이 다르게): 도트·말랑·연필·파스텔 타일·배지·젤리
    "st_pixel": {"id": "st_pixel", "kind": "sticker", "name": "도트 일상 스티커 팩", "amount": 2700, "desc": "도트 한 칸 한 칸 찍은 레트로 일상 스티커 — 스티커 32개"},
    "st_pop": {"id": "st_pop", "kind": "sticker", "name": "말랑 팝 스티커 팩", "amount": 2700, "desc": "통통 튀는 색에 흰 테두리를 두른 말랑한 일상 스티커 — 스티커 25개"},
    "st_pencil": {"id": "st_pencil", "kind": "sticker", "name": "연필 낙서 스티커 팩", "amount": 2700, "desc": "삐뚤빼뚤 연필선 위에 색 얼룩을 깐 손낙서 일상 — 스티커 25개"},
    "st_duo": {"id": "st_duo", "kind": "sticker", "name": "파스텔 타일 스티커 팩", "amount": 2700, "desc": "부드러운 파스텔 타일에 두 겹 색으로 칠한 일상 — 스티커 40개"},
    "st_badge": {"id": "st_badge", "kind": "sticker", "name": "동그라미 배지 스티커 팩", "amount": 2700, "desc": "진한 색 동그라미 배지에 하얀 그림을 박은 일상 — 스티커 36개"},
    "st_jelly": {"id": "st_jelly", "kind": "sticker", "name": "젤리 글로시 스티커 팩", "amount": 2700, "desc": "반짝 광택이 도는 젤리처럼 볼록한 일상 — 스티커 32개"},
    # AI 일러스트 팩(2026-11-09 사용자 요청: 팩마다 스타일이 다른 일러스트): 점토·수채·도트·종이접기·크레용·잉크
    "ai_clay": {"id": "ai_clay", "kind": "sticker", "name": "점토 일상 스티커 팩", "amount": 2700, "desc": "말랑한 3D 점토로 빚은 하루 소품 — 스티커 18개"},
    "ai_water": {"id": "ai_water", "kind": "sticker", "name": "수채 계절 스티커 팩", "amount": 2700, "desc": "물감이 번지는 수채화로 그린 계절과 자연 — 스티커 18개"},
    "ai_pixel": {"id": "ai_pixel", "kind": "sticker", "name": "도트 간식 스티커 팩", "amount": 2700, "desc": "도트 한 칸씩 찍은 레트로 먹거리 — 스티커 18개"},
    "ai_paper": {"id": "ai_paper", "kind": "sticker", "name": "종이접기 동물 스티커 팩", "amount": 2700, "desc": "겹겹이 오려 붙인 종이 공예 동물과 식물 — 스티커 18개"},
    "ai_crayon": {"id": "ai_crayon", "kind": "sticker", "name": "크레용 놀이 스티커 팩", "amount": 2700, "desc": "크레용으로 쓱쓱 그린 신나는 하루 — 스티커 18개"},
    "ai_ink": {"id": "ai_ink", "kind": "sticker", "name": "잉크 여행 스티커 팩", "amount": 2700, "desc": "굵은 선과 평평한 색으로 찍은 레트로 탈것과 여행 — 스티커 18개"},
    # 할 일 아이콘 스타일 팩(2026-11-04): 할 일 칸의 그림 25종을 다른 분위기로 바꾼다(그림은 화면 index.html 의 GLYPHS·ICON_PACKS, id 가 같아야 함). 가격은 임시값이다(근거 없음).
    # 메모지(2026-11-06 사용자 결정): 7종 한 묶음 대신 4종씩 두 번들. 예전에 «메모지 7종»(paper_pack)을 산 기록은 DB 에 남고 화면이 옛 7종 소유로 읽는다
    "paper_notes": {"id": "paper_notes", "kind": "paper", "name": "줄·격자 노트 4종 번들", "amount": 2700, "desc": "선과 격자가 그려진 노트 4가지 — 줄노트·모눈·도트·큰 모눈"},
    "paper_mood": {"id": "paper_mood", "kind": "paper", "name": "감성 종이 4종 번들", "amount": 2700, "desc": "종이 느낌이 나는 메모지 4가지 — 크라프트(갈색 종이)·포스트잇·옥스포드 노트(붉은 여백선)·수채(번지는 색)"},
    "icons_cute": {"id": "icons_cute", "kind": "sticker", "name": "귀여운 표정 스티커 팩", "amount": 2700, "desc": "표정이 있는 귀여운 일상 그림 20개 — 스티커로도, 할 일 칸 그림으로도 써요"},
    "icons_simple": {"id": "icons_simple", "kind": "sticker", "name": "심플 선 스티커 팩", "amount": 2700, "desc": "깔끔한 선 그림 일상 스티커 20개 — 스티커로도, 할 일 칸 그림으로도 써요"},
    "icons_pastel": {"id": "icons_pastel", "kind": "sticker", "name": "파스텔 스티커 팩", "amount": 2700, "desc": "흰 테두리 파스텔 일상 스티커 20개 — 스티커로도, 할 일 칸 그림으로도 써요"},
    # 바로 열기(2026-11-04): 기록·칸·달력이 열리는 3·28·60일째를 돈으로 먼저 연다. 기능만 열리고 달성 표시(✔)·축하는 실제 일수에만 준다.
    # 가격대(2026-11-06 사용자 결정): 모든 가격은 1달러를 기준으로 한다. 꾸미기 상품은 1·2·3달러 세 가격대로 나눠 단계 선물이 오래 지속할수록 더 비싼 팩을 주게 한다(GIFT_STAGE_TIER). 1달러: 배경 색 5·동글동글·하루·기념일·하이라이트·참 잘했어요 도장·D-day·손글씨 레터링·마커 표시 스티커, 2달러: 메모지 번들 2·아이콘 팩 3·생활 필수·오피스·도장이·마스킹테이프·과일 감정·펠트 날씨·낙서 스티커, 3달러: 디자인 테마 5·카페·말랑 3D 스티커. 1달러 ≈ 1,344원(환율 1,343.93원/달러, open.er-api.com 2026-11-04 조회)을 원 단위로 올려 1,350원으로 둔다. 기능(오늘의 한마디·지난 기록)은 1달러, 바로 열기는 기록 1달러·칸 늘리기 2달러·달력·일정 3달러, 전체는 개별 합계(6달러)보다 싼 5달러(6,750원). 환율은 오르내리므로 정기 갱신 기준은 아직 정하지 않았다(임시값). 화면이 «이전 열림이 열려 있을 때만» 보여 준다(일수는 브라우저에만 있어 서버는 모름)
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
