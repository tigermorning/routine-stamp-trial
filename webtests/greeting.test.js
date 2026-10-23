// 도우미 첫 인사 테스트.
// 약속: 도우미 창을 열면 도우미가 먼저, 밝고 가볍게 말을 건다. 오늘 칸 상태(없음/일부/전부)에 맞는 말을 하고,
//       점검하거나 탓하는 말투는 쓰지 않는다. (PRD "줄어드는 숫자·연속 끊김 경고 없음", 도우미 규칙 "감시하는 말투 없이")
// 서버·LLM 은 부르지 않는다. 인사는 기기 안에서 규칙으로만 고른다.
// index.html 을 jsdom 으로 열어 저장본을 넣고, 도우미 창 첫 말풍선(사용자가 보는 값)을 확인한다.
// INDEX_HTML 환경변수로 다른 index.html 을 가리키면 일부러 망가뜨린 복사본에도 같은 테스트를 돌려 볼 수 있다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(process.env.INDEX_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');

const pad = (n) => String(n).padStart(2, '0');
const TODAY = (() => {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
})();

const SLOTS = [
  { id: 's1', key: 'wakeup', icon: 'wake', color: '#ffd666' },
  { id: 's2', key: 'breakfast', icon: 'meal', color: '#ffb85c' },
  { id: 's3', key: 'move', icon: 'walkrun', color: '#5fcfb0' },
];

// stamped: 오늘 도장을 찍은 칸 id 목록, names: 칸 이름 직접 지정(기본은 자동 이름)
function openApp({ stamped = [], lang = 'ko', names = {} } = {}) {
  const slots = SLOTS.map((s) => (names[s.id] ? { ...s, name: names[s.id] } : s));
  const log = stamped.length ? { [TODAY]: Object.fromEntries(stamped.map((id) => [id, 1])) } : {};
  const saved = { slots, log, shelf: [], first: TODAY, hint: true, draft: '', gift: false, opened: 3, lang };
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously',
    url: 'http://localhost/',
    beforeParse(w) {
      w.localStorage.setItem('routine-trial-v1', JSON.stringify(saved));
    },
  });
  return dom.window;
}

const firstBubble = (w) => w.document.querySelector('#chLog .bub.a').textContent;
const openChat = (w) => w.document.getElementById('chatFab').click();
const closeChat = (w) => w.document.getElementById('chBack').click();
const labels = (w) => w.eval('S.slots.map(slotLabel)');

// 한국어 인사 문구 모음(상태별). 키 이름: chGrNone*, chGrSome*, chGrAll*
function pool(w, prefix) {
  return w.eval(`Object.keys(T.ko).filter(k=>k.startsWith(${JSON.stringify(prefix)})).map(k=>T.ko[k])`);
}
const fill = (tpl, name) => tpl.split('{slot}').join(name);

// 창은 테스트마다 닫는다(앱이 1분마다 도는 타이머를 걸어 두므로 닫지 않으면 테스트가 끝나지 않는다).
function withApp(opts, fn) {
  const w = openApp(opts);
  try {
    return fn(w);
  } finally {
    w.close();
  }
}

const STATES = [
  { name: '오늘 도장 없음', stamped: [], prefix: 'chGrNone', unstamped: ['s1', 's2', 's3'] },
  { name: '오늘 도장 일부', stamped: ['s1'], prefix: 'chGrSome', unstamped: ['s2', 's3'] },
  { name: '오늘 도장 전부', stamped: ['s1', 's2', 's3'], prefix: 'chGrAll', unstamped: [] },
];

for (const st of STATES) {
  test(`${st.name}: 첫 말풍선이 이 상태의 인사 문구 중 하나다`, () => {
    withApp({ stamped: st.stamped }, (w) => {
      const p = pool(w, st.prefix);
      assert.ok(p.length >= 2, `${st.prefix}* 인사 문구가 2개 이상 있어야 한다(지금 ${p.length}개)`);
      openChat(w);
      const first = firstBubble(w);
      const names = st.unstamped.length ? labels(w).filter((_, i) => st.unstamped.includes(SLOTS[i].id)) : [''];
      const expected = p.flatMap((tpl) => names.map((n) => fill(tpl, n)));
      assert.ok(expected.includes(first), `첫 말풍선이 ${st.prefix}* 문구여야 한다. 실제: ${first}`);
    });
  });
}

test('인사에 {slot} 같은 자리표시가 남지 않고, 칸 이름이 들어가면 아직 안 찍은 칸의 이름이다', () => {
  withApp({ stamped: ['s1'] }, (w) => {
    const all = labels(w);
    const seen = new Set();
    for (let i = 0; i < 6; i++) {
      openChat(w);
      const first = firstBubble(w);
      seen.add(first);
      assert.ok(!/[{}]/.test(first), `자리표시가 남음: ${first}`);
      assert.ok(!first.includes(all[0]), `이미 찍은 칸 '${all[0]}' 이름을 말하면 안 된다: ${first}`);
      closeChat(w);
    }
    assert.ok(seen.size >= 2, '여러 번 열면 문구가 바뀌어야 한다');
  });
});

test('모든 한국어 인사 문구에 점검하거나 탓하는 표현이 없다', () => {
  // '아직'은 사용자가 직접 정한 문구("아직 찍은 도장이 없네요")에 들어 있어 목록에서 뺐다. 탓하는 말투는 나머지 표현으로 계속 막는다.
  const BANNED = ['안 했', '안했', '못 했', '못했', '왜 ', '놓쳤', '밀렸', '끊', '연속', '실패', '게으', '해야', '반드시'];
  withApp({}, (w) => {
    const all = pool(w, 'chGr');
    assert.ok(all.length >= 8, `chGr* 인사 문구가 8개 있어야 한다(지금 ${all.length}개)`);
    for (const tpl of all) {
      for (const b of BANNED) assert.ok(!tpl.includes(b), `금지 표현 '${b}' 이(가) 있음: ${tpl}`);
    }
  });
});

test('모든 인사는 사용자의 요청을 살피는 배려 문장으로 끝난다', () => {
  // 마지막 문장에 이 중 하나가 들어 있어야 한다: 무엇을 도와드릴지·궁금한 점·필요한 점을 묻거나, 도장을 찍어 달라고 청하는 말
  const CLOSERS = ['도와드릴까요', '궁금', '필요한', '말씀해', '물어보세요', '찍어 주세요'];
  withApp({}, (w) => {
    const all = pool(w, 'chGr');
    assert.ok(all.length >= 8, `chGr* 인사 문구가 8개 있어야 한다(지금 ${all.length}개)`);
    for (const tpl of all) {
      const last = tpl.trim().split(/(?<=[.!?])\s+/).pop();
      assert.ok(CLOSERS.some((c) => last.includes(c)), `마지막 문장이 요청을 살피는 말이 아님: ${last}`);
    }
  });
});

test('인사 문구는 짧고(두세 줄), 질문은 하나 이하이며, 숫자가 없다', () => {
  withApp({}, (w) => {
    const all = pool(w, 'chGr');
    assert.ok(all.length >= 8, `chGr* 인사 문구가 8개 있어야 한다(지금 ${all.length}개)`);
    for (const tpl of all) {
      const longest = fill(tpl, '가'.repeat(14)); // 칸 이름은 최대 14글자
      assert.ok(longest.length <= 90, `너무 길다(${longest.length}자): ${tpl}`);
      assert.ok((tpl.match(/\?/g) || []).length <= 1, `질문이 둘 이상: ${tpl}`);
      assert.ok(!/\d/.test(tpl), `숫자가 있음: ${tpl}`);
    }
  });
});

test('같은 날 같은 상태에서 창을 닫았다 다시 열면 다른 인사가 나온다', () => {
  withApp({}, (w) => {
    openChat(w);
    const a = firstBubble(w);
    closeChat(w);
    openChat(w);
    const b = firstBubble(w);
    assert.notEqual(a, b, '연달아 같은 인사가 나오면 안 된다');
  });
});

test('한국어가 아니면 한국어 인사가 새어 나오지 않고 기존 인사를 쓴다', () => {
  withApp({ lang: 'en' }, (w) => {
    openChat(w);
    assert.equal(firstBubble(w), w.eval('T.en.chHello'));
  });
});

test('칸 이름에 HTML 을 넣어도 화면에 요소로 만들어지지 않는다', () => {
  withApp({ names: { s2: '<img src=x onerror=alert(1)>' } }, (w) => {
    for (let i = 0; i < 4; i++) {
      openChat(w);
      assert.equal(w.document.querySelectorAll('#chLog img').length, 0, '도우미 말풍선에 img 요소가 생기면 안 된다');
      closeChat(w);
    }
  });
});

// 새 하루가 되면 새 대화로 시작하고, 지난 대화는 기기 안에 날짜별로 보관한다.
test('날이 바뀌면 도우미 대화가 새로 시작되고 지난 대화는 보관된다', () => {
  const w = openApp({ stamped: [] });
  const old = [{ r: 'u', c: '어제 얘기' }, { r: 'a', c: '어제 답' }];
  w.eval(`S.chat={day:'2020-01-01',msgs:${JSON.stringify(old)},todos:[]}`);
  openChat(w);
  const log = w.document.getElementById('chLog').textContent;
  assert.ok(!log.includes('어제 얘기'), '지난 대화가 오늘 화면에 이어지면 안 된다');
  assert.equal(w.eval('S.chat.msgs.length'), 0);
  assert.deepEqual(JSON.parse(JSON.stringify(w.eval('S.chat.past'))), [{ d: '2020-01-01', msgs: old }]);
  assert.equal(w.eval('S.chat.day'), TODAY);
  w.close();
});

test('날짜 표시가 없는 옛 저장본의 대화도 한 번 지난 대화로 넘어간다', () => {
  const w = openApp({ stamped: [] });
  w.eval(`S.chat={msgs:[{r:'u',c:'옛 대화'}],todos:[]}`);
  openChat(w);
  assert.ok(!w.document.getElementById('chLog').textContent.includes('옛 대화'));
  assert.equal(w.eval('S.chat.past.length'), 1);
  w.close();
});

test('같은 날 다시 열면 오늘 대화가 그대로 이어진다', () => {
  const w = openApp({ stamped: [] });
  w.eval(`S.chat={day:${JSON.stringify(TODAY)},msgs:[{r:'u',c:'오늘 얘기'}],todos:[]}`);
  openChat(w);
  assert.ok(w.document.getElementById('chLog').textContent.includes('오늘 얘기'));
  assert.equal(w.eval('S.chat.past.length'), 0);
  w.close();
});

// 지난 대화 한 줄 꺼내기: 가장 최근 지난 날짜의 마지막 사용자 말을 시간 표현과 함께 첫 인사 뒤에 말한다.
const daysAgo = (n) => {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const recallOf = (past, { lang = 'ko', msgs = [] } = {}) => {
  const w = openApp({ lang });
  w.eval(`S.chat={day:${JSON.stringify(TODAY)},msgs:${JSON.stringify(msgs)},past:${JSON.stringify(past)},todos:[]}`);
  openChat(w);
  const bubs = [...w.document.querySelectorAll('#chLog .bub.a')].map((b) => b.textContent);
  w.close();
  return bubs;
};
const day = (d, ...us) => ({ d, msgs: us.flatMap((c) => [{ r: 'u', c }, { r: 'a', c: '답' }]) });

test('어제 대화가 있으면 첫 인사 뒤에 "어제 ○○ 이야기"를 한 줄 꺼낸다', () => {
  const b = recallOf([day(daysAgo(1), '아침 스트레칭', '물 마시기가 어려워요')]);
  assert.equal(b.length, 2);
  assert.match(b[1], /^어제 '물 마시기가 어려워요' 이야기를 나눴었죠/);
  assert.match(b[1], /궁금해요\.$/);
});

test('시간 표현이 날짜 차이에 맞는다(그저께·N일 전·지난주쯤·N주쯤 전)', () => {
  const when = (n) => recallOf([day(daysAgo(n), '운동')])[1].split(' ')[0];
  assert.equal(when(2), '그저께');
  assert.match(recallOf([day(daysAgo(4), '운동')])[1], /^4일 전 /);
  assert.match(recallOf([day(daysAgo(8), '운동')])[1], /^지난주쯤 /);
  assert.match(recallOf([day(daysAgo(21), '운동')])[1], /^3주쯤 전 /);
});

test('가장 최근 날짜를 쓰고, 오늘 이미 말했거나 쓸 수 없는 기록이면 꺼내지 않는다', () => {
  const past = [day(daysAgo(5), '옛날 얘기'), day(daysAgo(2), '최근 얘기')];
  assert.match(recallOf(past)[1], /^그저께 '최근 얘기'/);
  assert.equal(recallOf(past, { msgs: [{ r: 'u', c: '오늘 말함' }] }).length, 1, '오늘 대화 중이면 꺼내지 않는다');
  assert.equal(recallOf([{ d: '', msgs: [{ r: 'u', c: '날짜 모름' }] }]).length, 1);
  assert.equal(recallOf([{ d: daysAgo(1), msgs: [{ r: 'u', c: '위기 표현', x: true }] }]).length, 1);
  assert.equal(recallOf([day(daysAgo(1), '운동')], { lang: 'en' }).length, 1, '한국어가 아니면 말하지 않는다');
});

test('긴 말은 24자에서 줄이고 태그는 글자로만 보인다', () => {
  const b = recallOf([day(daysAgo(1), '<b>' + '가'.repeat(40))]);
  assert.ok(b[1].includes('<b>가'), '태그가 글자 그대로 보인다');
  assert.ok(b[1].includes('…'));
});

test('한 달이 넘은 대화는 꺼내지 않는다', () => {
  assert.equal(recallOf([day(daysAgo(45), '운동')]).length, 1);
});

// 도우미에게 보내는 값에 지금 시(hour)와 칸별 '몇 시까지'(until)가 들어간다(서버가 지난 시간대 칸을 권하지 않게 하는 재료).
test('도우미 요청에 hour 와 칸별 until 이 실려 간다(기본 칸만 시간대가 있다)', async () => {
  const w = openApp({ stamped: [] });
  w.eval(`S.slots.push({id:'s9',name:'내 칸',icon:'meal',color:'#ccc'})`);
  w.eval(`window.__b=null;window.fetch=(u,o)=>{window.__b=JSON.parse(o.body);return Promise.reject(new Error('x'))}`);
  await w.eval(`sendChat('안녕')`);
  const ctx = w.eval('JSON.parse(JSON.stringify(window.__b.context))');
  assert.equal(JSON.stringify(ctx.until), '[11,11,null,null]'); // 일어나기·아침 먹기는 11시까지, 몸 움직이기·내 칸은 하루 종일
  assert.equal(ctx.hour, new Date().getHours());
  w.close();
});
