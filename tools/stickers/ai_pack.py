"""AI 일러스트 스티커 팩을 만든다(ai_gen.py 로 그림을 만들고 stk/ai/*.png 와 ai_data.json 을 쓴다).
쓰는 법(저장소 루트에서): python tools/stickers/ai_pack.py   (이미 있는 그림은 건너뛴다. 키는 .env 의 OPENAI_API_KEY)
- 팩마다 스타일 하나를 정해 같은 질감·색감으로 만든다. 주제는 일상 낱말이며 기존 캐릭터·브랜드·로고는 쓰지 않는다.
- 사람이 결과를 한 장씩 보고 기존 작품과 닮은 것은 PACKS 에서 빼고 다시 돌린다(약관: 상표 침해 면책 제외 조건)."""
import json, os, re, sys, threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import ai_gen

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(ROOT, 'stk', 'ai')

# (팩 id, 이름, 가격(원), 설명, 스타일, [(영어 주제, 한글 이름)...])
PACKS = [
    ("ai_clay", "점토 일상", 2700, "말랑한 3D 점토로 빚은 하루 소품", "clay3d", [
        ("a steaming coffee cup", "커피"), ("a bar of soap with bubbles", "비누"), ("a cozy bed with a pillow", "잠자리"),
        ("an alarm clock", "알람"), ("a laundry basket", "빨래"), ("a pair of sneakers", "운동화"),
        ("an umbrella", "우산"), ("a backpack", "가방"), ("a desk lamp", "스탠드"),
        ("a pair of headphones", "헤드폰"), ("a small potted plant", "화분"), ("a tea kettle", "주전자"),
        ("a stack of books", "책 더미"), ("a smartphone", "스마트폰"), ("a tear-off desk calendar with a red circle mark", "달력"),
        ("a house key", "열쇠"), ("a shopping basket with vegetables", "장보기"), ("a hot water bottle", "찜질팩"),
    ]),
    ("ai_water", "수채 계절", 2700, "물감이 번지는 수채화로 그린 계절과 자연", "watercolor", [
        ("a cherry blossom branch", "벚꽃"), ("a red maple leaf", "단풍"), ("a snowman", "눈사람"),
        ("a rain cloud with raindrops", "비구름"), ("a sunflower", "해바라기"), ("a rainbow", "무지개"),
        ("a forest mushroom", "버섯"), ("an acorn", "도토리"), ("an ocean wave", "파도"),
        ("a crescent moon with stars", "달밤"), ("a snowflake", "눈송이"), ("a tulip", "튤립"),
        ("a pine tree", "소나무"), ("a butterfly", "나비"), ("a yellow ginkgo leaf", "은행잎"),
        ("a dandelion", "민들레"), ("a tangerine", "귤"), ("a seashell", "조개"),
    ]),
    ("ai_pixel", "도트 간식", 2700, "도트 한 칸씩 찍은 레트로 먹거리", "pixel", [
        ("a bowl of ramen noodles", "라면"), ("a kimbap roll slice", "김밥"), ("a slice of bread with butter", "빵"),
        ("an ice cream cone", "아이스크림"), ("a slice of pizza", "피자"), ("a fried chicken drumstick", "치킨"),
        ("a fried egg", "계란프라이"), ("a bowl of rice", "밥"), ("a red apple", "사과"),
        ("a slice of strawberry cake", "케이크"), ("a glazed donut", "도넛"), ("a sushi piece", "초밥"),
        ("a watermelon slice", "수박"), ("a bubble tea cup", "버블티"), ("a bucket of popcorn", "팝콘"),
        ("a cup of hot cocoa", "코코아"), ("a banana", "바나나"), ("a pair of chopsticks and a spoon", "수저"),
    ]),
    ("ai_paper", "종이접기 동물", 2700, "겹겹이 오려 붙인 종이 공예 동물과 식물", "paperfold", [
        ("a sleeping cat", "고양이"), ("a puppy", "강아지"), ("a rabbit", "토끼"),
        ("a small bird on a branch", "새"), ("a goldfish", "금붕어"), ("a turtle", "거북이"),
        ("a cactus in a pot", "선인장"), ("a sprout in a pot", "새싹"), ("a whale", "고래"),
        ("a hedgehog", "고슴도치"), ("a panda bear", "판다"), ("a ladybug", "무당벌레"),
        ("a snail", "달팽이"), ("a bee on a flower", "벌"), ("a penguin", "펭귄"),
        ("a fox", "여우"), ("a monstera leaf", "몬스테라"), ("a bouquet of flowers", "꽃다발"),
    ]),
    ("ai_crayon", "크레용 놀이", 2700, "크레용으로 쓱쓱 그린 신나는 하루", "crayon", [
        ("a smiling sun", "해"), ("a school bus", "스쿨버스"), ("a pencil", "연필"),
        ("a lunch box", "도시락"), ("a jump rope", "줄넘기"), ("a kite in the sky", "연"),
        ("a bunch of balloons", "풍선"), ("a soccer ball", "축구공"), ("a swing", "그네"),
        ("a sand castle", "모래성"), ("an ice pop", "아이스바"), ("a camping tent", "텐트"),
        ("fireworks", "불꽃놀이"), ("a birthday cake with candles", "생일 케이크"), ("a paint palette and brush", "물감"),
        ("a school backpack", "책가방"), ("a rain boot", "장화"), ("a snail on a leaf", "달팽이 잎"),
    ]),
    ("ai_ink", "잉크 여행", 2700, "굵은 선과 평평한 색으로 찍은 레트로 탈것과 여행", "ink", [
        ("a bicycle", "자전거"), ("a city bus", "버스"), ("a steam train", "기차"),
        ("an airplane", "비행기"), ("a sailing boat", "돛단배"), ("a hot air balloon", "열기구"),
        ("a suitcase", "여행 가방"), ("a vintage camera", "필름 카메라"), ("a folded paper map", "지도"),
        ("a compass", "나침반"), ("a lighthouse", "등대"), ("a mountain with a flag", "등산"),
        ("a rowing boat on a lake", "노 젓는 배"), ("a train ticket", "기차표"), ("a rocket", "로켓"),
        ("a helicopter", "헬리콥터"), ("a camping lantern", "랜턴"), ("a backpacker's boots", "등산화"),
    ]),
]


def slug(s):
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')[:40]


def main():
    os.makedirs(OUT, exist_ok=True)
    jobs, names, packs_out = [], {}, []
    for pid, pname, price, desc, style, items in PACKS:
        lst = []
        for en, ko in items:
            key = f'{pid}_{slug(en)}'
            lst.append(key)
            names[key] = ko
            if not os.path.exists(os.path.join(OUT, key + '.png')):
                jobs.append((key, style, en))
        packs_out.append({'id': pid, 'name': pname, 'price': price, 'desc': desc, 'style': style, 'list': lst})
    print('만들 그림', len(jobs), '개', flush=True)
    lock, tot = threading.Lock(), {'out': 0, 'in': 0, 'done': 0, 'fail': []}

    def work(job):
        key, style, en = job
        try:
            png, usage = ai_gen.generate(style, en, 'low')
            open(os.path.join(OUT, key + '.png'), 'wb').write(ai_gen.tidy(png))
            with lock:
                tot['out'] += usage.get('output_tokens', 0)
                tot['in'] += usage.get('input_tokens', 0)
                tot['done'] += 1
                if tot['done'] % 10 == 0:
                    print('완료', tot['done'], flush=True)
        except BaseException as e:  # 한 장이 실패해도 나머지는 계속
            with lock:
                tot['fail'].append((key, str(e)[:120]))

    with ThreadPoolExecutor(max_workers=6) as ex:
        list(ex.map(work, jobs))
    json.dump({'packs': packs_out, 'names': names}, open(os.path.join(HERE, 'ai_data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cost = tot['out'] / 1e6 * 8 + tot['in'] / 1e6 * 2  # 공식 가격표(gpt-image-1-mini: 이미지 출력 100만 토큰 $8, 텍스트 입력 $2)로 계산한 추정
    print('끝: 만든 것', tot['done'], '실패', len(tot['fail']), '출력토큰', tot['out'], '입력토큰', tot['in'], '추정비용 $%.3f' % cost)
    for f in tot['fail']:
        print(' 실패', f)


main()
