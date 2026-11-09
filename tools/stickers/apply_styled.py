"""fs_data.json(import_styled.py 의 결과)을 index.html·server/credits.py·출처 표기에 반영한다. 여러 번 돌려도 같은 결과가 나온다.
쓰는 법(저장소 루트에서): python tools/stickers/apply_styled.py"""
import json, os, re, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
data = json.load(open(os.path.join(ROOT, 'tools', 'stickers', 'fs_data.json'), encoding='utf-8'))
packs, names, src, lic = data['packs'], data['names'], data['src'], data['license']

p = os.path.join(ROOT, 'index.html')
s = open(p, encoding='utf-8').read()

for pk in packs:
    lst = ','.join("'fs:%s'" % k for k in pk['list'])
    entry = "%s:{name:'%s',list:[%s]}" % (pk['id'], pk['name'], lst)
    pat = re.compile(r"%s:\{name:'[^']*',list:\[[^\]]*\]\}" % re.escape(pk['id']))
    if pat.search(s):
        s = pat.sub(lambda m: entry, s, count=1)
    else:
        anchor = "  sticker_highlight:{"
        assert s.count(anchor) == 1
        s = s.replace(anchor, "  " + entry + ",\n" + anchor)

fs_line = 'const FS_NAMES=' + json.dumps(names, ensure_ascii=False) + '; // «fs:팩_이름» = 팩마다 질감·색을 입혀 구운 스티커(stk/fs/*.svg). 출처·라이선스는 tools/stickers/fs_data.json 과 THIRD_PARTY_NOTICES.md. 만드는 도구: tools/stickers/import_styled.py\n'
if 'const FS_NAMES=' in s:
    s = re.sub(r'const FS_NAMES=.*?\n', lambda m: fs_line, s, count=1, flags=re.S)
else:
    m = re.search(r'const FV_NAMES=.*?\n', s, re.S)
    s = s[:m.end()] + fs_line + s[m.end():]

if "e.startsWith('fs:')?`<img" not in s:
    old = "e.startsWith('fv:')?`<img class=\"sv fx\" src=\"/stk/fv/${e.slice(3)}.svg\""
    assert s.count(old) == 1
    s = s.replace(old, "e.startsWith('fs:')?`<img class=\"sv fx\" src=\"/stk/fs/${e.slice(3)}.svg\" alt=\"\" loading=\"lazy\" decoding=\"async\">`:" + old)
if "e.startsWith('fs:')?(FS_NAMES" not in s:
    old = "e.startsWith('fv:')?(FV_NAMES[e.slice(3)]||'스티커')"
    assert s.count(old) == 1
    s = s.replace(old, "e.startsWith('fs:')?(FS_NAMES[e.slice(3)]||'스티커'):" + old)
if "if(e.startsWith('fs:'))return `<img" not in s:
    old = "if(e.startsWith('fv:'))return `<img class=\"${cls}\" src=\"/stk/fv/${esc(e.slice(3))}.svg\""
    assert s.count(old) == 1
    s = s.replace(old, "if(e.startsWith('fs:'))return `<img class=\"${cls}\" src=\"/stk/fs/${esc(e.slice(3))}.svg\" alt=\"\" decoding=\"async\">`;" + old)

# 탭 순서: 스타일 팩은 Iconify 팩(세계 명소…) 바로 앞에 둔다(모양이 눈에 띄게)
m = re.search(r"const STK_ORDER=(\[.*?\]);", s)
order = json.loads(m.group(1))
ids = [pk['id'] for pk in packs]
base = [x for x in order if x not in ids]
at = len([x for x in base if x.startswith('ai_')])  # AI 팩 바로 뒤, 나머지 앞(사용자 2026-11-09)
order = base[:at] + ids + base[at:]
s = s[:m.start()] + 'const STK_ORDER=' + json.dumps(order) + ';' + s[m.end():]

if '파일별 출처는 stk/fv/SOURCES.json' in s and 'Pepicons' not in s:
    s = s.replace('파일별 출처는 stk/fv/SOURCES.json', 'Pepicons Pop·Pepicons Pencil·Solar(CC BY 4.0)와 Pixelarticons·Phosphor(MIT)·MingCute(Apache-2.0)는 색·테두리만 입혀 썼어요 — 파일별 출처는 stk/fv/SOURCES.json, stk/fs 는 tools/stickers/fs_data.json')
open(p, 'w', encoding='utf-8', newline='').write(s)

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
    m = re.search(r'    "sticker_cheer": \{[^\n]*\},\n', c)
    c = c[:m.end()] + '    # 스타일 팩(2026-11-09 사용자 요청: 구글 캘린더식 이모지에서 벗어나 팩마다 질감·색감·모양이 다르게): 도트·말랑·연필·파스텔 타일·배지·젤리\n' + ''.join(new_lines) + c[m.end():]
open(p2, 'w', encoding='utf-8', newline='').write(c)

used = sorted({v.split(':')[0] for v in src.values()})
info = {}
try:
    req = urllib.request.Request('https://api.iconify.design/collections?prefixes=' + ','.join(used), headers={'User-Agent': 'sticker-collector/1.0 (personal project)'})
    info = json.loads(urllib.request.urlopen(req, timeout=40).read().decode('utf-8'))
except Exception as e:
    print('세트 정보를 다시 받지 못했다:', e)
notice = '\n## 스타일 스티커(Iconify 오픈 아이콘 세트에 색·테두리·배경을 입힘)\n- 도트·말랑·연필·파스텔 타일·배지·젤리 팩(`stk/fs`). 그림 내용은 바꾸지 않고 색칠, 흰 테두리, 배경 타일, 그림자만 더했다. 그림 한 개씩의 출처는 `tools/stickers/fs_data.json`.\n'
for u in used:
    i = info.get(u) or {}
    a = i.get('author') or {}
    l = i.get('license') or {}
    notice += f"  - `{u}` — {i.get('name', u)}, 만든 곳: {a.get('name', '?')} ({a.get('url', '')}), 라이선스: {l.get('title', '')} {l.get('url', '')}\n"
np_ = os.path.join(ROOT, 'THIRD_PARTY_NOTICES.md')
n = open(np_, encoding='utf-8').read()
if '\n## 스타일 스티커(' in n:
    a = n.index('\n## 스타일 스티커(')
    nxt = n.find('\n## ', a + 5)
    n = n[:a] + (n[nxt:] if nxt != -1 else '')
n = n.rstrip('\n') + '\n' + notice
open(np_, 'w', encoding='utf-8', newline='').write(n)
print('ok', len(packs), '팩', sum(len(x['list']) for x in packs), '그림')
