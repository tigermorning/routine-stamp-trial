"""fv_data.json(import_iconify.py 의 결과)을 index.html·server/credits.py·출처 표기에 반영한다. 여러 번 돌려도 같은 결과가 나온다.
쓰는 법(저장소 루트에서): python tools/stickers/apply_iconify.py"""
import json, os, re, time, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
data = json.load(open(os.path.join(ROOT, 'tools', 'stickers', 'fv_data.json'), encoding='utf-8'))
packs, names, src, lic = data['packs'], data['names'], data['src'], data['license']

# ---------- index.html ----------
p = os.path.join(ROOT, 'index.html')
s = open(p, encoding='utf-8').read()

for pk in packs:
    lst = ','.join("'fv:%s'" % k for k in pk['list'])
    entry = "%s:{name:'%s',list:[%s]}" % (pk['id'], pk['name'], lst)
    pat = re.compile(r"%s:\{name:'[^']*',list:\[[^\]]*\]\}" % re.escape(pk['id']))
    if pat.search(s):
        s = pat.sub(lambda m: entry, s, count=1)
    else:
        anchor = "  sticker_highlight:{"
        assert s.count(anchor) == 1
        s = s.replace(anchor, "  " + entry + ",\n" + anchor)

fv_line = 'const FV_NAMES=' + json.dumps(names, ensure_ascii=False) + '; // «fv:세트_이름» = Iconify 오픈 아이콘 세트(출처·라이선스는 stk/fv/SOURCES.json 과 THIRD_PARTY_NOTICES.md). 만드는 도구: tools/stickers/import_iconify.py\n'
if 'const FV_NAMES=' in s:
    s = re.sub(r'const FV_NAMES=.*?\n', lambda m: fv_line, s, count=1, flags=re.S)
else:
    m = re.search(r'const FX_NAMES=.*?\n', s, re.S)
    s = s[:m.end()] + fv_line + s[m.end():]

# 그리기·이름·칸 그림
if "e.startsWith('fv:')?`<img" not in s:
    old = "e.startsWith('fx:')?`<img class=\"sv fx\" src=\"/stk/fx/${e.slice(3)}.png\""
    assert s.count(old) == 1
    s = s.replace(old, "e.startsWith('fv:')?`<img class=\"sv fx\" src=\"/stk/fv/${e.slice(3)}.svg\" alt=\"\" loading=\"lazy\" decoding=\"async\">`:" + old)
if "e.startsWith('fv:')?(FV_NAMES" not in s:
    old = "e.startsWith('fx:')?(FX_NAMES[e.slice(3)]||'스티커')"
    assert s.count(old) == 1
    s = s.replace(old, "e.startsWith('fv:')?(FV_NAMES[e.slice(3)]||'스티커'):" + old)
if "if(e.startsWith('fv:'))return `<img" not in s:
    old = "if(e.startsWith('fx:'))return `<img class=\"${cls}\" src=\"/stk/fx/${esc(e.slice(3))}.png\""
    assert s.count(old) == 1
    s = s.replace(old, "if(e.startsWith('fv:'))return `<img class=\"${cls}\" src=\"/stk/fv/${esc(e.slice(3))}.svg\" alt=\"\" decoding=\"async\">`;" + old)

# 탭 순서: 새 팩은 사람들 일상 뒤, 기능 팩(도장·테이프…) 앞
m = re.search(r"const STK_ORDER=(\[.*?\]);", s)
order = json.loads(m.group(1))
for pk in packs:
    if pk['id'] not in order:
        order.insert(order.index('sticker_dojang') + 1 if 'sticker_dojang' in order else len(order), pk['id'])
# 새 팩끼리 THEMES2 순서를 지키도록 다시 정렬
base = [x for x in order if x not in [pk['id'] for pk in packs]]
at = base.index('sticker_dojang') + 1 if 'sticker_dojang' in base else len(base)
order = base[:at] + [pk['id'] for pk in packs] + base[at:]
s = s[:m.start()] + 'const STK_ORDER=' + json.dumps(order) + ';' + s[m.end():]

# 상점 출처 줄
old_credit = '<small>스티커 그림: Microsoft Fluent Emoji 3D (MIT)</small>'
new_credit = '<small>스티커 그림: Microsoft Fluent Emoji(MIT), Google Noto·Mozilla fxemoji·ByteDance IconPark(Apache-2.0), Streamline·Twemoji·EmojiOne(CC BY 4.0) 등 — 파일별 출처는 stk/fv/SOURCES.json</small>'
if old_credit in s:
    s = s.replace(old_credit, new_credit)
open(p, 'w', encoding='utf-8', newline='').write(s)

# ---------- server/credits.py ----------
p2 = os.path.join(ROOT, 'server', 'credits.py')
c = open(p2, encoding='utf-8').read()
new_lines = []
for pk in packs:
    line = '    "%s": {"id": "%s", "kind": "sticker", "name": "%s 스티커 팩", "amount": %d, "desc": "%s — 스티커 %d개"},\n' % (pk['id'], pk['id'], pk['name'], pk['price'], pk['desc'], len(pk['list']))
    pat = re.compile(r'    "%s": \{[^\n]*\},\n' % re.escape(pk['id']))
    if pat.search(c):
        c = pat.sub(lambda m: line, c, count=1)
    else:
        new_lines.append(line)
if new_lines:
    m = re.search(r'    "sticker_plant": \{[^\n]*\},\n', c)
    c = c[:m.end()] + '    # 취미·여행 확장(2026-11-09 사용자 요청): 세계 명소·음악·게임·그림·영화·독서·캠핑·정원·사진·응원 팩(Iconify 오픈 아이콘 세트)\n' + ''.join(new_lines) + c[m.end():]
open(p2, 'w', encoding='utf-8', newline='').write(c)

# ---------- 출처 표기 ----------
used_sets = sorted({v.split(':')[0] for v in src.values()})
info = {}
try:
    req = urllib.request.Request('https://api.iconify.design/collections?prefixes=' + ','.join(used_sets), headers={'User-Agent': 'sticker-collector/1.0 (personal project)'})
    info = json.loads(urllib.request.urlopen(req, timeout=40).read().decode('utf-8'))
except Exception as e:
    print('세트 정보를 다시 받지 못했다:', e)
sources = {k: {'name': names[k], 'from': src[k], 'license': lic[k]} for k in sorted(src)}
json.dump({'sets': {u: {'name': (info.get(u) or {}).get('name'), 'author': ((info.get(u) or {}).get('author') or {}), 'license': ((info.get(u) or {}).get('license') or {})} for u in used_sets},
           'stickers': sources}, open(os.path.join(ROOT, 'stk', 'fv', 'SOURCES.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
notice = '\n## 스티커 그림(Iconify 오픈 아이콘 세트)\n- 모은 곳: Iconify(https://iconify.design) — 세트마다 만든 사람과 라이선스가 다르다. 그림 한 개씩의 출처는 `stk/fv/SOURCES.json`.\n- 쓴 세트와 라이선스(상업 사용이 되는 MIT·Apache-2.0·CC BY 4.0만 골랐다):\n'
for u in used_sets:
    i = info.get(u) or {}
    a = (i.get('author') or {})
    l = (i.get('license') or {})
    notice += f"  - `{u}` — {i.get('name', u)}, 만든 곳: {a.get('name', '?')} ({a.get('url', '')}), 라이선스: {l.get('title', lic.get(next((k for k, v in src.items() if v.startswith(u + ':')), ''), ''))} {l.get('url', '')}\n"
notice += '- CC BY 4.0 그림은 출처를 밝히는 조건이 있어 상점 «스티커» 탭 설명에 세트 이름을 적는다. 바꾼 점: 그림 안의 내용은 바꾸지 않고 SVG 로 내려받아 그대로 쓴다.\n\n## 오늘의 한마디(한국어) 문장\n- 공개 저장소의 MIT 라이선스 영어 문장을 골라 한국어로 옮겼다. 원문·출처는 `server/affirmations_sources.json`.\n  - annthurium/affirmations — MIT, Copyright (c) 2019 Tilde Ann Thurium (https://github.com/annthurium/affirmations)\n  - cvcpatton/positive-affirmation-bot — MIT, Copyright (c) 2026 Catherine Patton (https://github.com/cvcpatton/positive-affirmation-bot)\n- MIT License: 이 문장과 이 고지가 모든 사본에 들어 있는 한, 제한 없이 사용·복사·수정·배포할 수 있다. 소프트웨어는 «있는 그대로» 제공되며 보증하지 않는다.\n'
np_ = os.path.join(ROOT, 'THIRD_PARTY_NOTICES.md')
n = open(np_, encoding='utf-8').read()
if '## 스티커 그림(Iconify' in n:
    n = n[:n.index('\n## 스티커 그림(Iconify')]
n = n.rstrip('\n') + '\n' + notice
open(np_, 'w', encoding='utf-8', newline='').write(n)
print('ok', len(packs), '팩', sum(len(x['list']) for x in packs), '그림', '세트', used_sets)
