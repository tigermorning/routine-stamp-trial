"""Iconify(오픈 아이콘 세트 모음)에서 iconify_themes.py 의 질의어마다 그림을 최대 2개(서로 다른 세트) 골라 stk/fv/*.svg 로 만든다.
쓰는 법(저장소 루트에서): python tools/stickers/import_iconify.py
결과: stk/fv/<세트>__<이름>.svg, tools/stickers/fv_data.json(팩 목록·한글 이름·라이선스·출처), tools/stickers/iconify_cache.json(검색 결과)
- 허용 라이선스만 쓴다(MIT, Apache-2.0, CC BY 4.0, CC0). 단색(currentColor) 아이콘과 40KB 넘는 그림은 건너뛴다.
- 서비스에 부담을 주지 않도록: 검색 결과를 저장해 다시 쓰고, 그림은 세트별로 10개씩 묶어 한 번에 받으며, 요청 사이에 쉬고, 429 가 오면 길게 기다린다."""
import json, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from iconify_themes import THEMES2, parse

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'stk', 'fv')
CACHE = os.path.join(HERE, 'iconify_cache.json')
BASE = 'https://api.iconify.design'
UA = {'User-Agent': 'sticker-collector/1.0 (personal project)', 'Accept': '*/*'}
PREFS = ['streamline-plump-color', 'streamline-emojis', 'noto', 'fluent-emoji-flat', 'twemoji', 'emojione', 'fxemoji', 'icon-park',
         'streamline-flex-color', 'streamline-kameleon-color', 'streamline-freehand-color', 'streamline-ultimate-color', 'flat-color-icons']
ALLOW = {'MIT', 'Apache-2.0', 'CC-BY-4.0', 'CC0-1.0'}
MAX_BYTES = 40000
PAUSE = 0.6


def get(path, tries=6):
    wait = 0
    for i in range(tries):
        time.sleep(PAUSE + wait)
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=40).read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 6 * (i + 1)  # 한도에 걸리면 길게 쉰다
                continue
            if e.code == 404:
                return None
            raise
        except Exception:
            wait = 2 * (i + 1)
    return None


def slug(q):
    return re.sub(r'[^a-z0-9]+', '-', q.lower()).strip('-')


info = get('/collections?prefixes=' + ','.join(PREFS))
lic = {p: (info[p].get('license') or {}).get('spdx') for p in PREFS if p in info}
usable = [p for p in PREFS if lic.get(p) in ALLOW]
print('쓸 세트:', {p: lic[p] for p in usable})

cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}


def find(query):
    if query in cache:
        return [tuple(x) for x in cache[query] if 'flag' not in x[1]]  # 국기 그림은 쓰지 않는다(예: dj 질의어가 지부티 국기를 잡음)
    r = get('/search?' + urllib.parse.urlencode({'query': query, 'limit': 64, 'prefixes': ','.join(usable)})) or {}
    s = slug(query)
    words = [w for w in s.split('-') if w]
    cand = []
    for ic in r.get('icons', []):
        pre, name = ic.split(':', 1)
        n = name.lower()
        if n == s:
            sc = 0
        elif n.startswith(s):
            sc = 1
        elif all(w in n for w in words):
            sc = 2
        else:
            continue
        cand.append((sc, usable.index(pre), pre, name))
    cand.sort()
    picked, seen = [], set()
    for sc, pr, pre, name in cand:
        if pre in seen or 'flag' in name:
            continue
        seen.add(pre)
        picked.append((pre, name))
        if len(picked) == 2:
            break
    cache[query] = picked
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    return picked


os.makedirs(OUT, exist_ok=True)
used, names, srcs, lics, miss = set(), {}, {}, {}, []
pack_items = {i: [] for i in range(len(THEMES2))}
to_get = {}
for pi, (pid, pname, price, desc, block) in enumerate(THEMES2):
    for q, ko in parse(block):
        res = find(q)
        if not res:
            miss.append(q)
            continue
        for pre, name in res:
            key = re.sub(r'[^a-z0-9]+', '_', f'{pre}__{name}'.lower()).strip('_')
            if key in used:
                continue
            used.add(key)
            pack_items[pi].append(key)
            names[key] = ko
            srcs[key] = f'{pre}:{name}'
            lics[key] = lic[pre]
            to_get[key] = (pre, name)
    print('검색', pid, len(pack_items[pi]), flush=True)

# 세트별 묶음 내려받기(10개씩)
by_pre = {}
for key, (pre, name) in to_get.items():
    if not os.path.exists(os.path.join(OUT, key + '.svg')):
        by_pre.setdefault(pre, []).append((key, name))
bad = set()
for pre, items in by_pre.items():
    for i in range(0, len(items), 10):
        chunk = items[i:i + 10]
        r = get(f'/{pre}.json?icons=' + ','.join(n for _, n in chunk))
        if not r:
            bad.update(k for k, _ in chunk)
            continue
        dw, dh = r.get('width', 16), r.get('height', 16)
        for key, name in chunk:
            ic = r.get('icons', {}).get(name)
            if not ic:
                al = r.get('aliases', {}).get(name)
                ic = r.get('icons', {}).get(al['parent']) if al else None
            if not ic or 'currentColor' in ic['body']:
                bad.add(key)
                continue
            w, h = ic.get('width', dw), ic.get('height', dh)
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}">{ic["body"]}</svg>'
            if len(svg) > MAX_BYTES:
                bad.add(key)
                continue
            open(os.path.join(OUT, key + '.svg'), 'w', encoding='utf-8').write(svg)
        print('받음', pre, min(i + 10, len(items)), '/', len(items), flush=True)
for key in list(names):
    if not os.path.exists(os.path.join(OUT, key + '.svg')):
        bad.add(key)
packs = []
for pi, items in pack_items.items():
    pid, pname, price, desc, block = THEMES2[pi]
    packs.append({'id': pid, 'name': pname, 'price': price, 'desc': desc, 'list': [k for k in items if k not in bad]})
for k in bad:
    names.pop(k, None), srcs.pop(k, None), lics.pop(k, None)
json.dump({'packs': packs, 'names': names, 'src': srcs, 'license': lics}, open(os.path.join(HERE, 'fv_data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
keep = {k + '.svg' for p in packs for k in p['list']}
for f in os.listdir(OUT):  # 이번 목록에서 빠진 그림 파일은 지운다
    if f not in keep:
        os.remove(os.path.join(OUT, f))
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print('그림', sum(len(p['list']) for p in packs), '개, 합계', total // 1024, 'KB, 건너뜀', len(bad), '개')
for p in packs:
    print(' ', p['id'], p['name'], len(p['list']))
print('결과 없는 질의어', len(miss), ':', ', '.join(miss[:60]))
