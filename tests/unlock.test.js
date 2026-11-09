// 칸 늘리기 일정 테스트.
// 근거: README "칸은 처음 3개이고, 도장 찍은 날이 28일이면 칸 늘리기(최대 12칸)", 처음 여는 사람의 첫 방문 선물 1일은 도장 일수에 더해 센다,
//       이미 더 많은 칸을 가진 사람의 칸은 줄이지 않는다. PRD "단계 구조 개편"(2026-11-05).
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
  ...Array.from({ length: 6 }, (_, i) => ({ id: 's' + (7 + i), key: 'extra' + (7 + i), icon: 'wake', color: '#ffd666' })),
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

function open({ slots, days, gift = false }) {
  const saved = {
    slots: SLOTS.slice(0, slots),
    log: stampedDays(days),
    shelf: [],
    first: '2026-01-01',
    hint: true,
    draft: '',
    gift,
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
  { name: '칸 3개, 도장 2일: 아직 안 늘어남', input: { slots: 3, days: 2 }, capacity: 3, canAdd: false },
  { name: '칸 3개, 도장 3일: 3일에는 기록이 열리고 칸은 그대로', input: { slots: 3, days: 3 }, capacity: 3, canAdd: false },
  { name: '칸 3개, 도장 27일: 아직 안 늘어남', input: { slots: 3, days: 27 }, capacity: 3, canAdd: false },
  { name: '칸 3개, 도장 28일: 칸을 늘릴 수 있음(최대 12칸)', input: { slots: 3, days: 28 }, capacity: 12, canAdd: true },
  { name: '첫 도장 선물: 도장 27일 + 선물 1일이면 28일로 쳐서 칸을 늘릴 수 있음', input: { slots: 3, days: 27, gift: true }, capacity: 12, canAdd: true },
  { name: '칸 11개, 도장 100일: 12번째 칸까지 늘릴 수 있음', input: { slots: 11, days: 100 }, capacity: 12, canAdd: true },
  { name: '칸 12개: 최대라서 더는 안 늘어남', input: { slots: 12, days: 100 }, capacity: 12, canAdd: false },
  { name: '이미 칸이 많은 사람은 줄지 않음: 칸 6개, 도장 3일이어도 6칸 유지', input: { slots: 6, days: 3 }, capacity: 6, canAdd: false },
];

for (const c of cases) {
  test(c.name, () => {
    const r = open(c.input);
    assert.equal(r.capacity, c.capacity, '열린 칸 수');
    assert.equal(r.canAdd, c.canAdd, '새 칸 추가 버튼이 보이는지');
  });
}
