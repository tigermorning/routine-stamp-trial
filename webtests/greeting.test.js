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
  const BANNED = ['안 했', '안했', '못 했', '못했', '아직', '왜 ', '놓쳤', '밀렸', '끊', '연속', '실패', '게으', '해야', '반드시'];
  withApp({}, (w) => {
    const all = pool(w, 'chGr');
    assert.ok(all.length >= 8, `chGr* 인사 문구가 8개 있어야 한다(지금 ${all.length}개)`);
    for (const tpl of all) {
      for (const b of BANNED) assert.ok(!tpl.includes(b), `금지 표현 '${b}' 이(가) 있음: ${tpl}`);
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
