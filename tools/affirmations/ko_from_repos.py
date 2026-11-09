"""오늘의 한마디(한국어) 확언을 라이선스가 명확한 공개 저장소에서 가져와 한국어로 옮긴다(2026-11-09 사용자 요청: «클로드가 아무렇게나 쓴 문장 같다, 저장소에서 가져와라»).
- 출처: A = annthurium/affirmations (MIT, (c) 2019 Tilde Ann Thurium), C = cvcpatton/positive-affirmation-bot (MIT, (c) 2026 Catherine Patton)
- 고른 기준: 이 앱의 대상(ADHD가 있거나 습관 만들기가 어려운 사람, 실패를 자주 겪어 자포자기한 사람, 의욕이 없는 사람)에게 믿을 수 있는 작은 말.
  과장(풍요·우주·끌어당김·무한한 힘)과 자기 평가를 키우는 큰 선언은 뺐다. 자기 연민, 허락, 작은 진전, 실패를 배움으로 보는 말을 골랐다.
- 번역은 원문의 뜻을 살려 해요체 한 줄로 옮겼다(사람 검수는 아직 없음).
쓰는 법(저장소 루트에서): python tools/affirmations/ko_from_repos.py  → server/affirmations.json 의 ko 와 server/affirmations_sources.json 을 갱신한다."""
import json, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = {'A': 'annthurium/affirmations (MIT)', 'C': 'cvcpatton/positive-affirmation-bot (MIT)'}
ITEMS = [
    # 작은 진전·시작
    ('A', 'Small progress is still progress', '작은 진전도 진전이에요.'),
    ('A', 'Starting is the most difficult step - but you can do it', '시작이 가장 어려운 걸음이에요. 그래도 할 수 있어요.'),
    ('A', 'It is not a sprint, it is a marathon. One step at a time', '단거리 달리기가 아니라 마라톤이에요. 한 번에 한 걸음씩 가요.'),
    ('C', 'I make progress with every small step.', '작은 한 걸음마다 나는 나아가고 있어요.'),
    ('C', 'I celebrate each step forward as a victory.', '앞으로 내딛는 걸음마다 작은 승리로 쳐 줘요.'),
    ('C', 'I embrace progress over perfection on my journey to success.', '완벽함보다 나아가는 쪽을 택해요.'),
    ('C', 'I celebrate my growth and successes, big and small.', '크든 작든 해낸 일을 스스로 축하해요.'),
    ('C', 'I honor my progress, no matter how small.', '아무리 작아도 내가 해낸 진전을 인정해요.'),
    ('C', 'I create momentum through consistent action.', '꾸준한 작은 행동이 흐름을 만들어요.'),
    ('C', 'I show up and give my best effort.', '오늘도 나타나서 할 수 있는 만큼 해요.'),
    ('C', 'I take consistent steps toward my goals.', '목표를 향해 꾸준히 한 걸음씩 가요.'),
    ('A', 'I admire you for taking this on', '이 일을 시작한 것만으로도 대단해요.'),
    ('A', "You'll find a way", '차근차근 하다 보면 길을 찾게 될 거예요.'),
    # 실패·실수를 배움으로
    ('A', "Struggling is part of learning", '버벅대는 것도 배우는 과정이에요.'),
    ('A', "Mistakes don't make you less capable", '실수한다고 덜 유능해지는 건 아니에요.'),
    ('A', "It's not a mistake, it's a learning opportunity", '실수가 아니라 배울 기회예요.'),
    ('A', 'Failure is just another way to learn how to do something right', '실패는 제대로 하는 법을 배우는 또 다른 길이에요.'),
    ('A', 'The past does not equal the future', '과거가 곧 미래는 아니에요.'),
    ('C', 'My past does not define my present.', '과거가 지금의 나를 정하지는 않아요.'),
    ('A', "Don't worry if you find flaws in your past creations, it's because you've evolved", '예전 작업에서 흠이 보인다면, 그만큼 자랐다는 뜻이에요.'),
    ('A', 'You know more than you knew yesterday', '어제보다 아는 게 늘었어요.'),
    ('A', 'We are all works in progress', '우리는 모두 만들어 가는 중이에요.'),
    ('C', 'I grow through what I go through.', '겪는 일을 통해 조금씩 자라요.'),
    ('C', 'Every experience helps me evolve and improve.', '모든 경험이 나를 조금씩 나아지게 해요.'),
    ('C', 'I am capable of rising again and again.', '나는 몇 번이고 다시 일어설 수 있어요.'),
    ('C', 'I have the strength to keep moving forward.', '계속 나아갈 힘이 내게 있어요.'),
    ('C', 'I persist with determination and hope.', '희망을 놓지 않고 계속해 봐요.'),
    ('C', 'I am braver than my fears.', '두려움보다 내가 더 용감해요.'),
    # 자기 연민·허락
    ('A', 'I give myself permission to do what is right for me', '나에게 맞는 선택을 해도 된다고 스스로 허락해요.'),
    ('C', 'I give myself permission to feel and to heal.', '느끼고 회복해도 된다고 나에게 허락해요.'),
    ('C', 'I allow myself to heal at my own pace.', '내 속도로 회복해도 괜찮아요.'),
    ('C', 'I honor my emotions without judgment.', '내 감정을 판단하지 않고 받아들여요.'),
    ('C', 'My emotions are valid and worthy of compassion.', '내 감정은 타당하고, 다정하게 대할 가치가 있어요.'),
    ('C', 'I am gentle with myself as I heal.', '회복하는 동안 나에게 다정해요.'),
    ('C', 'I treat my heart with kindness and patience.', '내 마음을 친절과 인내로 대해요.'),
    ('C', 'I trust the natural rhythm of my healing.', '회복에는 저마다의 리듬이 있어요.'),
    ('C', 'I embrace myself with compassion and gentle understanding.', '나를 다정한 이해로 안아 줘요.'),
    ('C', 'I treat myself with the same kindness I offer the world.', '세상에 건네는 친절을 나에게도 건네요.'),
    ('C', 'I deserve the same love I freely give to others.', '남에게 주는 사랑을 나도 받을 자격이 있어요.'),
    ('C', 'I bloom in my own time, and that is enough.', '나는 내 때에 피어나요. 그거면 충분해요.'),
    ('C', 'I am patient with myself as I grow.', '자라는 동안 나 자신에게 인내심을 가져요.'),
    ('C', 'I celebrate the person I am becoming.', '되어 가는 나를 응원해요.'),
    # 마음 가라앉히기·집중
    ('C', 'I release overwhelm and embrace mental peace.', '압도되는 마음을 내려놓고 차분해져요.'),
    ('C', 'I return to my breath and center myself.', '숨으로 돌아와 마음을 가다듬어요.'),
    ('C', 'I breathe in peace and exhale tension.', '숨을 들이쉬며 평온을, 내쉬며 긴장을 보내요.'),
    ('C', 'I let go of what I cannot control and embrace peace.', '내가 어쩔 수 없는 일은 내려놓고 마음을 편히 가져요.'),
    ('C', 'I am at peace with where I am right now.', '지금 있는 자리에서 편안해도 괜찮아요.'),
    ('C', 'I approach each task with calm concentration.', '일을 하나씩, 차분하게 집중해서 해요.'),
    ('C', 'I direct my attention to what truly matters.', '정말 중요한 것에 주의를 돌려요.'),
    ('C', 'I am present and grateful for this moment.', '지금 이 순간에 머물며 고마워해요.'),
    ('C', 'I experience life one moment at a time.', '삶은 한 순간씩 지나가는 거예요.'),
    ('C', 'I notice and celebrate small joys.', '작은 기쁨을 알아차리고 즐겨요.'),
    ('C', 'I appreciate the simple and meaningful moments.', '소박하지만 의미 있는 순간들을 소중히 여겨요.'),
    ('C', 'I trust myself to handle whatever comes my way.', '무슨 일이 와도 하나씩 해 나갈 수 있다고 나를 믿어요.'),
    ('C', 'I honor my needs and boundaries in relationships.', '관계에서도 내 필요와 선을 지켜요.'),
    ('C', 'I choose understanding over conflict.', '다툼보다 이해를 택해요.'),
]
assert len({k[2] for k in ITEMS}) == len(ITEMS), '한국어 문장이 겹친다'
ko = [k[2] for k in ITEMS]
p = os.path.join(ROOT, 'server', 'affirmations.json')
d = json.load(open(p, encoding='utf-8'))
d['ko'] = ko
json.dump(d, open(p, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=2)
open(p, 'a', encoding='utf-8').write('\n')
src = [{'ko': k[2], 'en': k[1], 'source': SRC[k[0]]} for k in ITEMS]
json.dump(src, open(os.path.join(ROOT, 'server', 'affirmations_sources.json'), 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
print('한국어 확언', len(ko), '개 — 출처', {v: sum(1 for k in ITEMS if SRC[k[0]] == v) for v in SRC.values()})
