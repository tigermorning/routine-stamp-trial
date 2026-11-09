"""모양이 다른 «스타일 팩»을 만든다(2026-11-09 사용자: 구글 캘린더식 이모지에서 벗어나 네이버 캘린더처럼 팩마다 질감·색감·모양이 다르게).
같은 일상 낱말 목록을 서로 다른 오픈 아이콘 세트(도트·말랑·연필·듀오톤·배지·젤리)에서 찾아, 그림마다 팩 고유의 색과 질감(스티커 테두리·종이 오림·도트 그림자·타일·광택)을 입혀 stk/fs/*.svg 로 굽는다.
쓰는 법(저장소 루트에서): python tools/stickers/import_styled.py
결과: stk/fs/<키>.svg, tools/stickers/fs_data.json(팩·한글 이름·출처·라이선스), tools/stickers/styled_cache.json(검색 결과)
- 허용 라이선스만(MIT, Apache-2.0, CC BY 4.0, CC0). 그림 내용은 바꾸지 않고 색·테두리·배경만 입힌다(CC BY 출처는 THIRD_PARTY_NOTICES.md)."""
import json, os, re, sys, time, urllib.parse, urllib.request, hashlib

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'stk', 'fs')
CACHE = os.path.join(HERE, 'styled_cache.json')
BASE = 'https://api.iconify.design'
UA = {'User-Agent': 'sticker-collector/1.0 (personal project)', 'Accept': '*/*'}
ALLOW = {'MIT', 'Apache-2.0', 'CC-BY-4.0', 'CC0-1.0'}
PAUSE = 0.5

WORDS = """coffee=커피
book=책
run=달리기
sleep=잠
cooking=요리
study=공부
laundry=빨래
shower=샤워
walk=산책
meeting=회의
phone=전화
cart=장보기
bus=버스
train=기차
music=음악
pill=약
water=물
plant=식물
broom=청소
mail=메일
calendar=달력
clock=시계
heart=마음
home=집
bag=가방
camera=사진
gift=선물
cake=케이크
pizza=피자
bicycle=자전거
car=자동차
airplane=비행기
umbrella=우산
sun=해
moon=달
cloud=구름
star=별
bell=알림
pencil=쓰기
laptop=노트북
game=게임
dumbbell=운동
bed=침대
tooth=양치
salad=샐러드
wallet=지갑
key=열쇠
trash=쓰레기
lightbulb=아이디어
flag=목표
trophy=성취
smile=웃음
fire=열정
rocket=시작
leaf=잎
tea=차
beer=맥주
shirt=옷
glasses=안경
palette=그림""".strip().splitlines()

# (팩 id, 이름, 가격(원), 설명, 세트, 이름 접미(우선순위), 스타일, 색 목록)
PACKS = [
    ("st_pixel", "도트 일상", 2700, "도트 한 칸 한 칸 찍은 레트로 일상 스티커", "pixelarticons", [""], "pixel",
     ["#ff6b6b", "#ffa94d", "#ffd43b", "#69db7c", "#4dabf7", "#b197fc", "#f783ac"]),
    ("st_pop", "말랑 팝", 2700, "통통 튀는 색에 흰 테두리를 두른 말랑한 일상 스티커", "pepicons-pop", [""], "diecut",
     ["#ff5d8f", "#ff9f1c", "#2ec4b6", "#6c63ff", "#ef476f", "#06d6a0", "#118ab2"]),
    ("st_pencil", "연필 낙서", 2700, "삐뚤빼뚤 연필선 위에 색 얼룩을 깐 손낙서 일상", "pepicons-pencil", [""], "sketch",
     ["#ffe066", "#ffadad", "#bde0fe", "#caffbf", "#ffd6a5", "#e0bbff", "#a0e7e5"]),
    ("st_duo", "파스텔 타일", 2700, "부드러운 파스텔 타일에 두 겹 색으로 칠한 일상", "ph", ["-duotone"], "tile",
     ["#f4a6b8", "#f6c177", "#9ccfd8", "#a6d189", "#b4a7ff", "#f2b5a0", "#8bd3c7"]),
    ("st_badge", "동그라미 배지", 2700, "진한 색 동그라미 배지에 하얀 그림을 박은 일상", "mingcute", ["-fill", ""], "badge",
     ["#e5484d", "#f76b15", "#30a46c", "#0091ff", "#8e4ec6", "#d6409f", "#12a594"]),
    ("st_jelly", "젤리 글로시", 2700, "반짝 광택이 도는 젤리처럼 볼록한 일상", "solar", ["-bold", "-bold-duotone", ""], "jelly",
     ["#ff6fb5", "#ffa63d", "#43d9ad", "#5aa9ff", "#a78bfa", "#ff7a7a", "#35c2c1"]),
]


def get(path, tries=6):
    wait = 0
    for i in range(tries):
        time.sleep(PAUSE + wait)
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=40).read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 6 * (i + 1)
                continue
            if e.code == 404:
                return None
            raise
        except Exception:
            wait = 2 * (i + 1)
    return None


def slug(q):
    return re.sub(r'[^a-z0-9]+', '-', q.lower()).strip('-')


cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}


def find(prefix, query, suffixes):
    k = prefix + '|' + query
    if k in cache:
        return cache[k]
    r = get('/search?' + urllib.parse.urlencode({'query': query, 'limit': 64, 'prefixes': prefix})) or {}
    s = slug(query)
    best = None
    for ic in r.get('icons', []):
        name = ic.split(':', 1)[1].lower()
        for rank, suf in enumerate(suffixes):
            if name == s + suf:
                cand = (rank, 0, len(name), name)
                if best is None or cand < best:
                    best = cand
        if best is None and name.startswith(s) and 'flag' not in name:
            pass
    res = best[3] if best else None
    cache[k] = res
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    return res


def shade(hex_, f):
    h = hex_.lstrip('#')
    r, g, b = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    r, g, b = [max(0, min(255, int(c * f))) for c in (r, g, b)]
    return '#%02x%02x%02x' % (r, g, b)


def tint(hex_, f):  # 흰색 쪽으로
    h = hex_.lstrip('#')
    r, g, b = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02x%02x%02x' % tuple(int(c + (255 - c) * f) for c in (r, g, b))


def bake(style, body, w, h, color, uid):
    """아이콘 본문(currentColor 사용)을 64×64 스티커 SVG 로 굽는다."""
    def icon(fill, x=0, y=0, size=36, extra=''):
        b = body.replace('currentColor', fill)
        return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 {w} {h}" overflow="visible" {extra}>{b}</svg>'
    head = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 64 64">'
    if style == 'pixel':
        bg, ink = tint(color, 0.78), shade(color, 0.55)
        return head + (f'<rect x="4" y="4" width="56" height="56" rx="6" fill="{bg}"/><rect x="4" y="4" width="56" height="56" rx="6" fill="none" stroke="{ink}" stroke-width="3"/>'
                       f'<rect x="8" y="8" width="48" height="5" fill="#fff" opacity=".45"/>'
                       f'{icon(shade(color, 0.35), 14, 15, 36)}{icon(ink, 12, 12, 36)}</svg>')
    if style == 'diecut':
        f = f'<filter id="o{uid}" x="-30%" y="-30%" width="160%" height="160%"><feMorphology in="SourceAlpha" operator="dilate" radius="3.2" result="d"/><feFlood flood-color="#fff"/><feComposite in2="d" operator="in" result="w"/><feGaussianBlur in="d" stdDeviation="1.6" result="b"/><feOffset in="b" dy="2" result="s"/><feFlood flood-color="#000" flood-opacity=".28"/><feComposite in2="s" operator="in" result="sh"/><feMerge><feMergeNode in="sh"/><feMergeNode in="w"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        return head + f'<defs>{f}</defs><g filter="url(#o{uid})">{icon(color, 10, 10, 44)}</g></svg>'
    if style == 'sketch':
        ink = '#2b2b2b'
        blob = f'<path d="M12 22 C14 8 40 6 52 15 C62 24 58 46 46 54 C34 62 12 58 8 42 C6 34 8 28 12 22Z" fill="{color}"/>'
        blob2 = f'<path d="M16 26 C20 14 38 12 48 20" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".5"/>'
        return head + f'{blob}{blob2}{icon(ink, 14, 14, 36)}</svg>'
    if style == 'tile':
        bg, ink = tint(color, 0.7), shade(color, 0.62)
        return head + (f'<rect x="5" y="5" width="54" height="54" rx="16" fill="{bg}"/>'
                       f'<rect x="5" y="5" width="54" height="54" rx="16" fill="none" stroke="{tint(color, .35)}" stroke-width="2"/>'
                       f'<circle cx="49" cy="15" r="4" fill="#fff" opacity=".6"/>{icon(ink, 13, 13, 38)}</svg>')
    if style == 'badge':
        return head + (f'<circle cx="32" cy="33" r="28" fill="{shade(color, .7)}"/><circle cx="32" cy="31" r="28" fill="{color}"/>'
                       f'<circle cx="32" cy="31" r="24" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="2 3" opacity=".8"/>'
                       f'<path d="M12 22 A24 24 0 0 1 32 7" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".35"/>'
                       f'{icon("#ffffff", 15, 14, 34)}</svg>')
    if style == 'jelly':
        g = f'<linearGradient id="g{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{tint(color, .45)}"/><stop offset="1" stop-color="{shade(color, .85)}"/></linearGradient>'
        f = f'<filter id="s{uid}" x="-30%" y="-30%" width="160%" height="160%"><feMorphology in="SourceAlpha" operator="dilate" radius="2.4" result="d"/><feFlood flood-color="#fff"/><feComposite in2="d" operator="in" result="w"/><feOffset in="d" dy="2.5" result="s"/><feFlood flood-color="{shade(color, .5)}" flood-opacity=".45"/><feComposite in2="s" operator="in" result="sh"/><feMerge><feMergeNode in="sh"/><feMergeNode in="w"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        hl = f'<ellipse cx="25" cy="18" rx="11" ry="4" fill="#fff" opacity=".45" transform="rotate(-18 25 18)"/>'
        return head + f'<defs>{g}{f}</defs><g filter="url(#s{uid})">{icon(f"url(#g{uid})", 10, 9, 44)}</g>{hl}</svg>'
    raise SystemExit('모르는 스타일 ' + style)


info = get('/collections?prefixes=' + ','.join(sorted({p[4] for p in PACKS})))
lic = {p: (info[p].get('license') or {}).get('spdx') for p in info}
print('세트 라이선스:', lic)
for p in PACKS:
    assert lic.get(p[4]) in ALLOW, (p[4], lic.get(p[4]))

os.makedirs(OUT, exist_ok=True)
words = [tuple(x.split('=', 1)) for x in WORDS]
packs_out, names, srcs, lics = [], {}, {}, {}
for pid, pname, price, desc, pre, sufs, style, colors in PACKS:
    chosen = []
    for q, ko in words:
        n = find(pre, q, sufs)
        if n:
            chosen.append((q, ko, n))
    print(pid, pname, '찾은 낱말', len(chosen), flush=True)
    # 세트별 묶음 내려받기
    got = {}
    for i in range(0, len(chosen), 10):
        chunk = chosen[i:i + 10]
        r = get(f'/{pre}.json?icons=' + ','.join(n for _, _, n in chunk))
        if not r:
            continue
        dw, dh = r.get('width', 16), r.get('height', 16)
        for q, ko, n in chunk:
            ic = r.get('icons', {}).get(n)
            if not ic:
                al = r.get('aliases', {}).get(n)
                ic = r.get('icons', {}).get(al['parent']) if al else None
            if ic:
                got[n] = (ic['body'], ic.get('width', dw), ic.get('height', dh))
    lst = []
    for idx, (q, ko, n) in enumerate(chosen):
        if n not in got:
            continue
        body, w, h = got[n]
        key = f'{pid}_{slug(q).replace("-", "_")}'
        color = colors[idx % len(colors)]
        svg = bake(style, body, w, h, color, hashlib.md5(key.encode()).hexdigest()[:6])
        open(os.path.join(OUT, key + '.svg'), 'w', encoding='utf-8').write(svg)
        lst.append(key)
        names[key] = ko
        srcs[key] = f'{pre}:{n}'
        lics[key] = lic[pre]
    packs_out.append({'id': pid, 'name': pname, 'price': price, 'desc': desc, 'list': lst, 'style': style})
json.dump({'packs': packs_out, 'names': names, 'src': srcs, 'license': lics}, open(os.path.join(HERE, 'fs_data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
keep = {k + '.svg' for p in packs_out for k in p['list']}
for f in os.listdir(OUT):
    if f not in keep:
        os.remove(os.path.join(OUT, f))
print('그림', sum(len(p['list']) for p in packs_out), '개')
for p in packs_out:
    print(' ', p['id'], p['name'], len(p['list']))
