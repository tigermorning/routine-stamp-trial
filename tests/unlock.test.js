// 칸 열림 일정 테스트.
// 근거: README "도장 찍은 날이 3일, 28일, 60일이 되면 칸이 하나씩 열림 (최대 6칸). 한 번 열린 칸은 일정이 바뀌어도 닫히지 않음",
//       README "처음 여는 사람에게는 새 칸 열기에 1일을 미리 채워 줌", PRD "칸 열림 일정" (2026-10-21 변경: 3·7·14일 → 3·28·60일).
// index.html 을 jsdom 으로 열어 저장본을 넣고, 사용자가 보는 값(새 칸 추가 버튼이 보이는지, 열린 칸 수)을 확인한다.
// INDEX_HTML 환경변수로 다른 index.html 을 가리키면 일부러 망가뜨린 복사본에도 같은 테스트를 돌려 볼 수 있다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(process.env.INDEX_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');

const SLOTS = [
  { id: 's1', key: 'wakeup', icon: 'wake', color: '#ffd666' },
  { id: 's2', key: 'breakfast', icon: 'meal', color: '#ffb85c' },
  { id: 's3', key: 'move', icon: 'walkrun', color: '#5fcfb0' },
  { id: 's4', key: 'extra4', icon: 'wake', color: '#ffd666' },
  { id: 's5', key: 'extra5', icon: 'wake', color: '#ffd666' },
  { id: 's6', key: 'extra6', icon: 'wake', color: '#ffd666' },
];

function stampedDays(n) {
  const log = {};
  const d = new Date(Date.UTC(2026, 0, 1));
  for (let i = 0; i < n; i++) {
    log[d.toISOString().slice(0, 10)] = { s1: 1 };
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return log;
}

// opened 를 넣어 두지 않으면 앱이 예전 일정(3·7·14일)으로 먼저 열어 버리므로, 항상 칸 수에 맞춰 넣는다.
function open({ slots, days, gift = false, opened = slots }) {
  const saved = {
    slots: SLOTS.slice(0, slots),
    log: stampedDays(days),
    shelf: [],
    first: '2026-01-01',
    hint: true,
    draft: '',
    gift,
    opened,
    lang: 'ko',
  };
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously',
    url: 'http://localhost/',
    beforeParse(w) {
      w.localStorage.setItem('routine-trial-v1', JSON.stringify(saved));
    },
  });
  const w = dom.window;
  try {
    const capacity = w.eval('capacity()');
    w.document.getElementById('editBtn').click();
    const canAdd = !w.document.getElementById('addSlot').hidden;
    return { capacity, canAdd };
  } finally {
    // 앱이 1분마다 도는 타이머를 걸어 두므로 닫지 않으면 테스트가 끝나지 않는다.
    w.close();
  }
}

const cases = [
  { name: '칸 3개, 도장 2일: 아직 안 열림', input: { slots: 3, days: 2 }, capacity: 3, canAdd: false },
  { name: '칸 3개, 도장 3일: 4번째 칸이 열림', input: { slots: 3, days: 3 }, capacity: 4, canAdd: true },
  { name: '첫 도장 선물: 도장 2일 + 선물 1일이면 4번째 칸이 열림', input: { slots: 3, days: 2, gift: true }, capacity: 4, canAdd: true },
  { name: '칸 4개, 도장 27일: 아직 안 열림', input: { slots: 4, days: 27 }, capacity: 4, canAdd: false },
  { name: '칸 4개, 도장 28일: 5번째 칸이 열림', input: { slots: 4, days: 28 }, capacity: 5, canAdd: true },
  { name: '칸 5개, 도장 59일: 아직 안 열림', input: { slots: 5, days: 59 }, capacity: 5, canAdd: false },
  { name: '칸 5개, 도장 60일: 6번째 칸이 열림', input: { slots: 5, days: 60 }, capacity: 6, canAdd: true },
  { name: '칸 6개: 최대라서 더는 안 열림', input: { slots: 6, days: 100 }, capacity: 6, canAdd: false },
  { name: '한 번 열린 칸은 닫히지 않음: 열린 칸 5개, 도장 3일이어도 5칸 유지', input: { slots: 3, days: 3, opened: 5 }, capacity: 5, canAdd: true },
];

for (const c of cases) {
  test(c.name, () => {
    const r = open(c.input);
    assert.equal(r.capacity, c.capacity, '열린 칸 수');
    assert.equal(r.canAdd, c.canAdd, '새 칸 추가 버튼이 보이는지');
  });
}
