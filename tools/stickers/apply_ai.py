"""ai_data.json(ai_pack.py 의 결과)을 index.html·server/credits.py·출처 표기에 반영한다. 여러 번 돌려도 같은 결과가 나온다.
쓰는 법(저장소 루트에서): python tools/stickers/apply_ai.py"""
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
data = json.load(open(os.path.join(ROOT, 'tools', 'stickers', 'ai_data.json'), encoding='utf-8'))
packs, names = data['packs'], data['names']
# 파일이 실제로 있는 그림만 쓴다(실패한 것·뺀 것 제외)
have = {f[:-4] for f in os.listdir(os.path.join(ROOT, 'stk', 'ai')) if f.endswith('.png')}
for pk in packs:
    pk['list'] = [k for k in pk['list'] if k in have]
names = {k: v for k, v in names.items() if k in have}

p = os.path.join(ROOT, 'index.html')
s = open(p, encoding='utf-8').read()

for pk in packs:
    lst = ','.join("'ai:%s'" % k for k in pk['list'])
    entry = "%s:{name:'%s',list:[%s]}" % (pk['id'], pk['name'], lst)
    pat = re.compile(r"%s:\{name:'[^']*',list:\[[^\]]*\]\}" % re.escape(pk['id']))
    if pat.search(s):
        s = pat.sub(lambda m: entry, s, count=1)
    else:
        anchor = "  sticker_highlight:{"
        assert s.count(anchor) == 1
        s = s.replace(anchor, "  " + entry + ",\n" + anchor)

ai_line = 'const AI_NAMES=' + json.dumps(names, ensure_ascii=False) + '; // «ai:팩_이름» = OpenAI 이미지 모델로 만든 스티커(stk/ai/*.png). 만드는 도구: tools/stickers/ai_pack.py, 출처 고지는 THIRD_PARTY_NOTICES.md\n'
if 'const AI_NAMES=' in s:
    s = re.sub(r'const AI_NAMES=.*?\n', lambda m: ai_line, s, count=1, flags=re.S)
else:
    m = re.search(r'const FS_NAMES=.*?\n', s, re.S)
    s = s[:m.end()] + ai_line + s[m.end():]

if "e.startsWith('ai:')?`<img" not in s:
    old = "e.startsWith('fs:')?`<img class=\"sv fx\" src=\"/stk/fs/${e.slice(3)}.svg\""
    assert s.count(old) == 1
    s = s.replace(old, "e.startsWith('ai:')?`<img class=\"sv fx\" src=\"/stk/ai/${e.slice(3)}.png\" alt=\"\" loading=\"lazy\" decoding=\"async\">`:" + old)
if "e.startsWith('ai:')?(AI_NAMES" not in s:
    old = "e.startsWith('fs:')?(FS_NAMES[e.slice(3)]||'스티커')"
    assert s.count(old) == 1
    s = s.replace(old, "e.startsWith('ai:')?(AI_NAMES[e.slice(3)]||'스티커'):" + old)
if "if(e.startsWith('ai:'))return `<img" not in s:
    old = "if(e.startsWith('fs:'))return `<img class=\"${cls}\" src=\"/stk/fs/${esc(e.slice(3))}.svg\""
    assert s.count(old) == 1
    s = s.replace(old, "if(e.startsWith('ai:'))return `<img class=\"${cls}\" src=\"/stk/ai/${esc(e.slice(3))}.png\" alt=\"\" decoding=\"async\">`;" + old)

# 탭 순서: AI 팩은 스타일 팩(st_*) 바로 앞에 둔다(가장 눈에 띄게)
m = re.search(r"const STK_ORDER=(\[.*?\]);", s)
order = json.loads(m.group(1))
ids = [pk['id'] for pk in packs]
base = [x for x in order if x not in ids]
at = 0  # 가장 앞(사용자 2026-11-09: 개성 있는 새 팩이 먼저 보이게)
order = base[:at] + ids + base[at:]
s = s[:m.start()] + 'const STK_ORDER=' + json.dumps(order) + ';' + s[m.end():]

if 'AI 일러스트' not in s and 'Pepicons Pop' in s:
    s = s.replace('Pepicons Pop·Pepicons Pencil', 'AI 일러스트(OpenAI 이미지 모델로 생성)·Pepicons Pop·Pepicons Pencil', 1)
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
    m = re.search(r'    "st_jelly": \{[^\n]*\},\n', c)
    c = c[:m.end()] + '    # AI 일러스트 팩(2026-11-09 사용자 요청: 팩마다 스타일이 다른 일러스트): 점토·수채·도트·종이접기·크레용·잉크\n' + ''.join(new_lines) + c[m.end():]
open(p2, 'w', encoding='utf-8', newline='').write(c)

notice = '\n## AI 일러스트 스티커(OpenAI 이미지 모델로 생성)\n- 팩 6개(`ai_clay`·`ai_water`·`ai_pixel`·`ai_paper`·`ai_crayon`·`ai_ink`, `stk/ai`). 모델 `gpt-image-1-mini`, 팩마다 스타일 문장 하나로 만들었다(`tools/stickers/ai_gen.py` 의 STYLES, 주제 목록은 `tools/stickers/ai_pack.py`).\n- 프롬프트에는 기존 캐릭터·브랜드·로고·실존 인물을 쓰지 않았고, 만든 뒤 사람이 확인했다. 생성 이미지는 AI 가 만든 것이다.\n- 권리: OpenAI 서비스 계약 4.1절은 «고객이 모든 출력물을 소유한다»고 한다. 다만 출력물이 고유하지 않을 수 있고(4.4절), 상업적 이용에 따른 상표 분쟁은 OpenAI 면책에서 빠질 수 있다(서비스 약관 1(a)). 키는 기관에서 받은 것이라 기관 정책 확인이 필요하다.\n'
np_ = os.path.join(ROOT, 'THIRD_PARTY_NOTICES.md')
n = open(np_, encoding='utf-8').read()
if '\n## AI 일러스트 스티커(' in n:
    a = n.index('\n## AI 일러스트 스티커(')
    nxt = n.find('\n## ', a + 5)
    n = n[:a] + (n[nxt:] if nxt != -1 else '')
n = n.rstrip('\n') + '\n' + notice
open(np_, 'w', encoding='utf-8', newline='').write(n)
print('ok', len(packs), '팩', sum(len(x['list']) for x in packs), '그림')
