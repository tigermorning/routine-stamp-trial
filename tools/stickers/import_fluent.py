"""Fluent Emoji(microsoft/fluentui-emoji, MIT) 3D 그림을 내려받아 128px PNG 로 줄여 stk/fx/ 에 둔다.
쓰는 법(저장소 루트에서): python tools/stickers/import_fluent.py
- fluent_themes.py 의 이름이 실제 Fluent 폴더에 없으면 목록을 출력하고 멈춘다(오타 확인용).
- 결과: stk/fx/<key>.png, tools/stickers/fx_data.json(팩 목록과 한글 이름)
"""
import io, json, os, re, subprocess, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from fluent_themes import THEMES, parse
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'stk', 'fx')
SIZE = 128
RAW = 'https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/'


def slug(name):
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


tree = json.loads(subprocess.run(['gh', 'api', 'repos/microsoft/fluentui-emoji/git/trees/main?recursive=1'],
                                 capture_output=True, text=True, encoding='utf-8').stdout)['tree']
paths = [t['path'] for t in tree if t['type'] == 'blob' and '/3D/' in t['path'] and t['path'].endswith('.png')]
by_name = {}
for p in paths:
    parts = p.split('/')
    name = parts[1]
    # 사람 그림은 피부색 폴더(Default, Light, ...)가 있다. Default 만 쓴다
    if len(parts) == 5 and parts[2] != 'Default':
        continue
    by_name[name] = p
# Fluent 폴더 이름은 대소문자·공백이 영어 이름과 같다(예: "Hot beverage")

packs, names, need, missing, used = [], {}, {}, [], set()  # used: 같은 그림이 두 팩에 들어가지 않게(앞선 팩이 먼저 가진다)
# 겹치는 그림은 작은 팩이 먼저 가져간다(중복을 없앴을 때 팩 크기가 고르게 남도록). 결과 팩 순서는 THEMES 순서를 지킨다
PRIORITY = ['sticker_love', 'sticker_beauty', 'sticker_money', 'sticker_plant', 'sticker_party', 'sticker_dojang', 'sticker_felt',
            'sticker_glossy', 'sticker_round', 'sticker_office', 'sticker_daily', 'sticker_doodle', 'sticker_fruit',
            'sticker_life', 'sticker_sched', 'sticker_cafe']
_order = {pid: i for i, pid in enumerate(PRIORITY)}
for pid, pname, price, desc, block in sorted(THEMES, key=lambda t: _order[t[0]]):
    keys, seen = [], set()
    for en, ko in parse(block):
        if en not in by_name:
            missing.append((pid, en))
            continue
        k = slug(en)
        if k in seen or k in used:
            continue
        seen.add(k)
        used.add(k)
        keys.append(k)
        names.setdefault(k, ko)
        need[k] = by_name[en]
    packs.append({'id': pid, 'name': pname, 'price': price, 'desc': desc, 'list': keys})

packs.sort(key=lambda p: [t[0] for t in THEMES].index(p['id']))

if missing:
    print('Fluent 에 없는 이름:', *missing, sep='\n  ')
    sys.exit(1)

os.makedirs(OUT, exist_ok=True)


def fetch(item):
    k, p = item
    dst = os.path.join(OUT, k + '.png')
    if os.path.exists(dst):
        return k, os.path.getsize(dst)
    data = urllib.request.urlopen(RAW + urllib.parse.quote(p), timeout=60).read()
    im = Image.open(io.BytesIO(data)).convert('RGBA')
    im.thumbnail((SIZE, SIZE), Image.LANCZOS)
    # 256색으로 줄여 크기를 약 27%로 만든다(26~48px 로 쓰므로 눈에 띄는 차이가 없다)
    im.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(dst, 'PNG', optimize=True)
    return k, os.path.getsize(dst)


with ThreadPoolExecutor(8) as ex:
    sizes = dict(ex.map(fetch, need.items()))
total = sum(sizes.values())
json.dump({'packs': packs, 'names': names}, open(os.path.join(os.path.dirname(__file__), 'fx_data.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('팩', len(packs), '개, 그림', len(need), '개, 합계', total // 1024, 'KB, 평균', total // max(1, len(need)), 'B')
for p in packs:
    print(' ', p['id'], p['name'], len(p['list']))
