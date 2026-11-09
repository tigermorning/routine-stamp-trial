"""fx_data.json(import_fluent.py 의 결과)을 index.html 과 server/credits.py 에 반영한다. 여러 번 돌려도 같은 결과가 나온다.
- index.html: STICKER_PACKS 의 테마 팩 목록을 'fx:이름' 으로 바꾸고, FX_NAMES·stkFace·stkName·테마 탭을 고친다.
- server/credits.py: 팩 상품의 이름·설명·가격을 새 테마로 바꾸고 새 팩 4종을 더한다.
- 옛 코드 그림(svSprite 의 sv: 그림)은 이미 붙여 둔 스티커가 깨지지 않도록 지우지 않는다. 목록에서만 뺀다.
"""
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
data = json.load(open(os.path.join(ROOT, 'tools', 'stickers', 'fx_data.json'), encoding='utf-8'))
packs, names = data['packs'], data['names']

# ---------- index.html ----------
p = os.path.join(ROOT, 'index.html')
s = open(p, encoding='utf-8').read()

# 1) 테마 팩 목록. 기존 팩은 자리에서 바꾸고, 새 팩은 하이라이트 줄 앞에 더한다
for pk in packs:
    lst = ','.join("'fx:%s'" % k for k in pk['list'])
    entry = "sticker_%s:{name:'%s',list:[%s]}" % (pk['id'][len('sticker_'):], pk['name'], lst)
    pat = re.compile(r"%s:\{name:'[^']*',list:\[[^\]]*\]\}" % re.escape(pk['id']))
    if pat.search(s):
        s = pat.sub(lambda m: entry, s, count=1)
    else:
        anchor = "  sticker_highlight:{"
        assert s.count(anchor) == 1
        s = s.replace(anchor, "  " + entry + ",\n" + anchor)

# 2) 그림 이름 사전(FX_NAMES)
fx_line = 'const FX_NAMES=' + json.dumps(names, ensure_ascii=False) + '; // «fx:영어이름» = Microsoft Fluent Emoji 3D(MIT) 128px, stk/fx/ 에서 서빙. 만드는 도구: tools/stickers/import_fluent.py\n'
if 'const FX_NAMES=' in s:
    s = re.sub(r'const FX_NAMES=.*?\n', lambda m: fx_line, s, count=1, flags=re.S)
else:
    m = re.search(r'const SV_NAMES=\{.*?\};\n', s, re.S)
    s = s[:m.end()] + fx_line + s[m.end():]

# 3) 그리기·이름
old = "e.startsWith('sv:')?`<svg class=\"sv pk-${PK_OF[e]||'x'}\""
new = "e.startsWith('fx:')?`<img class=\"sv fx\" src=\"/stk/fx/${e.slice(3)}.png\" alt=\"\" loading=\"lazy\" decoding=\"async\">`:e.startsWith('sv:')?`<svg class=\"sv pk-${PK_OF[e]||'x'}\""
if "e.startsWith('fx:')?`<img" not in s:
    assert s.count(old) == 1
    s = s.replace(old, new)
old = "e.startsWith('sv:')?(SV_NAMES[e.slice(3)]||'스티커'):e;"
new = "e.startsWith('fx:')?(FX_NAMES[e.slice(3)]||'스티커'):e.startsWith('sv:')?(SV_NAMES[e.slice(3)]||'스티커'):e;"
if "e.startsWith('fx:')?(FX_NAMES" not in s:
    assert s.count(old) == 1
    s = s.replace(old, new)

# 4) 테마 탭: 산 팩 하나가 탭 하나(네이버 캘린더식). 옛 5분류(일상·약속·운동·공부·날씨)는 팩이 테마별로 나뉘어 필요 없다
a = min(s.index(m0) for m0 in ('/* 스티커 카테고리 탭(사양서 2절', '/* 스티커 테마 탭(네이버') if m0 in s)
b = s.index('const stkFadeIn=')
tabs = """/* 스티커 테마 탭(네이버 캘린더식): 산 팩 하나가 탭 하나이고 «전체»는 산 팩의 모든 그림이다. 테마는 건강·운동·집안일·음식·일·기념일·여행·취미·날씨·동물·기분·쇼핑·미용·만남·식물·사람 등(tools/stickers/fluent_themes.py) */
const STK_ORDER=%s; // 탭 순서(건강→운동→생활→음식→일→기념일→여행→취미→날씨→동물→기분→쇼핑→미용→만남→식물→사람, 그다음 도장·테이프 같은 기능 팩)
const stkRank=id=>{const i=STK_ORDER.indexOf(id);return i<0?999:i};
let stkTab='all';
const stkIn=(e,tab)=>tab==='all'||!!(STICKER_PACKS[tab]&&STICKER_PACKS[tab].list.includes(e));
function stkTabsDraw(box,pool,redraw){ // 탭 줄을 그린다. 산 팩이 둘 이상일 때만 보이고, 고른 탭이 없어졌으면 «전체»로 돌아간다
  const ids=Object.keys(STICKER_PACKS).filter(id=>OWNED.has(id)&&STICKER_PACKS[id].list.some(e=>pool.includes(e))).sort((a,b)=>stkRank(a)-stkRank(b));
  if(stkTab!=='all'&&!ids.includes(stkTab))stkTab='all';
  box.hidden=ids.length<2;
  box.innerHTML=[['all','전체']].concat(ids.map(id=>[id,STICKER_PACKS[id].name])).map(([id,n])=>`<button type="button" role="tab" class="stkchip" data-c="${id}" aria-selected="${stkTab===id}">${esc(n)}</button>`).join('');
  box.querySelectorAll('button').forEach(bt=>bt.onclick=()=>{stkTab=bt.dataset.c;redraw()});
}
"""
order = [pk['id'] for pk in packs] + ['sticker_seal', 'sticker_washi', 'sticker_dday', 'sticker_letter', 'sticker_marker', 'sticker_highlight']
s = s[:a] + (tabs % json.dumps(order)) + s[b:]
s = s.replace("if(stkTab!=='all'&&stkCat(e)!==stkTab)return;", "if(!stkIn(e,stkTab))return;")
s = s.replace("pool.filter(e=>stkTab==='all'||stkCat(e)===stkTab)", "pool.filter(e=>stkIn(e,stkTab))")
assert 'stkCat' not in s, 'stkCat 이 남아 있다'

# 5) 그림 크기
css_anchor = ".stkgrid{display:grid!important;"
fx_css = ".sv.fx{object-fit:contain}.stkgrid .sv.fx{width:36px;height:36px}\n"
if '.sv.fx{' in s:
    i0 = s.index('.sv.fx{')
    i1 = s.index('\n', i0) + 1
    s = s[:i0] + fx_css + s[i1:]
else:
    assert s.count(css_anchor) == 1
    s = s.replace(css_anchor, fx_css + css_anchor)
open(p, 'w', encoding='utf-8', newline='').write(s)

# ---------- server/credits.py ----------
p = os.path.join(ROOT, 'server', 'credits.py')
c = open(p, encoding='utf-8').read()
new_lines = []
for pk in packs:
    line = '    "%s": {"id": "%s", "kind": "sticker", "name": "%s 스티커 팩", "amount": %d, "desc": "%s — 스티커 %d개"},\n' % (
        pk['id'], pk['id'], pk['name'], pk['price'], pk['desc'], len(pk['list']))
    pat = re.compile(r'    "%s": \{[^\n]*\},\n' % re.escape(pk['id']))
    if pat.search(c):
        c = pat.sub(lambda m: line, c, count=1)
    else:
        new_lines.append(line)
if new_lines:
    m = re.search(r'    "sticker_marker": \{[^\n]*\},\n', c)
    c = c[:m.end()] + '    # 일상 테마 확장(2026-11-09 사용자 요청): 쇼핑·미용·만남·식물 팩\n' + ''.join(new_lines) + c[m.end():]
open(p, 'w', encoding='utf-8', newline='').write(c)
print('ok', len(packs), '팩', sum(len(x['list']) for x in packs), '그림')
