"""OpenAI 이미지 API 로 스티커를 만든다(2026-11-09 사용자 요청: 구글 캘린더식 이모지에서 벗어나 팩마다 개성 있는 일러스트).
한 장: python tools/stickers/ai_gen.py <스타일이름> <주제 영어> <저장 파일.png> [quality=low|medium|high] [model]
- 키는 .env 의 OPENAI_API_KEY(또는 ENV_FILE 로 지정한 파일)를 이 프로세스 안에서만 읽는다(출력·기록에 쓰지 않는다).
- 기존 캐릭터·브랜드·로고·실존 인물은 프롬프트에 쓰지 않는다(약관상 상표 침해 면책이 빠질 수 있다).
- 결과 PNG 는 투명 배경. 사용량(토큰)만 출력한다."""
import base64, io, json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
STYLES = {
    'clay3d': 'soft 3D clay figurine look, rounded chunky shapes, pastel colors, gentle studio lighting',
    'watercolor': 'hand-painted watercolor illustration, soft bleeding edges, visible paper grain, muted warm colors',
    'pixel': 'chunky 16-bit pixel art, limited bright palette, crisp pixels',
    'paperfold': 'layered cut-paper craft, visible paper texture, soft drop shadows between layers',
    'crayon': 'child-like crayon drawing, waxy textured strokes, bold primary colors',
    'ink': 'bold black ink outline with flat spot colors, retro screen-print feel',
}
COMMON = ('single die-cut sticker design, centered, one subject only, thick white sticker border, '
          'transparent background, no text, no letters, no watermark, no logo, no brand, no real person, no existing character')


def key():
    for line in open(os.environ.get('ENV_FILE', os.path.join(ROOT, '.env')), encoding='utf-8'):
        if line.startswith('OPENAI_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('.env 에 OPENAI_API_KEY 가 없다')


def generate(style, subject, quality='low', model='gpt-image-1-mini', tries=4):
    """PNG 바이트와 사용량(dict)을 돌려준다. 한도(429)·일시 오류는 기다렸다 다시 부른다."""
    prompt = f'{subject}. {STYLES.get(style, style)}. {COMMON}'
    body = json.dumps({'model': model, 'prompt': prompt, 'size': '1024x1024', 'quality': quality,
                       'background': 'transparent', 'output_format': 'png', 'n': 1}).encode()
    for i in range(tries):
        req = urllib.request.Request('https://api.openai.com/v1/images/generations', body,
                                     {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key()})
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=240).read().decode('utf-8'))
            return base64.b64decode(r['data'][0]['b64_json']), r.get('usage') or {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')[:300]
            if e.code in (429, 500, 502, 503) and i < tries - 1:
                time.sleep(8 * (i + 1))
                continue
            raise SystemExit(f'HTTP {e.code}: {msg}')
        except Exception:
            if i < tries - 1:
                time.sleep(4 * (i + 1))
                continue
            raise


def tidy(png_bytes, size=256, cutoff=100):
    """반투명 번짐(그림자)을 잘라 내고 256px 로 줄여 가볍게 만든다. 돌려주는 값은 PNG 바이트."""
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
    im.putalpha(im.getchannel('A').point(lambda v: 0 if v < cutoff else 255))
    im = im.resize((size, size), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, 'PNG', optimize=True)
    return out.getvalue()


if __name__ == '__main__':
    style, subject, out = sys.argv[1], sys.argv[2], sys.argv[3]
    quality = sys.argv[4] if len(sys.argv) > 4 else 'low'
    model = sys.argv[5] if len(sys.argv) > 5 else 'gpt-image-1-mini'
    png, usage = generate(style, subject, quality, model)
    open(out, 'wb').write(png)
    print('saved', out, len(png) // 1024, 'KB', 'usage', json.dumps(usage, ensure_ascii=False), 'model', model, 'quality', quality)
