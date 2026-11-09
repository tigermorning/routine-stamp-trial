// 메몽식 메모지·형광펜, 네이버 캘린더식 스티커 카테고리 탭 시험.
// 근거: docs/BENCHMARK_STICKER_AND_MEMO_SPEC.md 2~4절. 해금은 기존 일정을 그대로 쓴다(기록 3일, 형광펜 도구 28일, 사용자 결정 2026-11-09).
// index.html 을 jsdom 으로 열어 사용자가 보는 값(편집 영역, 형광펜 줄, 탭 줄)과 저장 글 변환을 확인한다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM, VirtualConsole } = require('jsdom');

const HTML = fs.readFileSync(process.env.INDEX_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');

function stampedDays(n) {
  const log = {};
  const d = new Date(Date.UTC(2026, 0, 1));
  for (let i = 0; i < n; i++) {
    log[d.toISOString().slice(0, 10)] = { s1: 1 };
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return log;
}

function open({ days = 0, diary = {} } = {}) {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on('jsdomError', (e) => errors.push(String(e.message || e)));
  const saved = {
    slots: [{ id: 's1', key: 'wakeup', icon: 'wake', color: '#ffd666' }, { id: 's2', key: 'breakfast', icon: 'meal', color: '#ffb85c' }, { id: 's3', key: 'move', icon: 'walkrun', color: '#5fcfb0' }],
    log: stampedDays(days), shelf: [], first: '2026-01-01', hint: true, draft: '', gift: false, lang: 'ko', diary,
  };
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously', url: 'http://localhost/', virtualConsole: vc,
    beforeParse(w) { w.localStorage.setItem('routine-trial-v1', JSON.stringify(saved)); },
  });
  return { w: dom.window, errors };
}

test('화면을 여는 동안 스크립트 오류가 없다', () => {
  const { w, errors } = open({ days: 30 });
  try { assert.deepEqual(errors, []); } finally { w.close(); }
});

test('저장 글 변환: 칠한 글자만 ==색:글자==로 저장하고 다시 읽으면 같다', () => {
  const { w } = open();
  try {
    const src = '앞 ==노랑== 중간 ==p:분홍== ==v:보라== 끝';
    const r = w.eval(`(()=>{const q=mhParse(${JSON.stringify(src)});return {t:q.t,c:q.c,back:mhPack(q.t,q.c)}})()`);
    assert.equal(r.t, '앞 노랑 중간 분홍 보라 끝');
    assert.equal(r.back, src);
    assert.deepEqual([r.c[2], r.c[3], r.c[8], r.c[12]].map(Number), [1, 1, 2, 5]);
  } finally { w.close(); }
});

test('평문 메모와 글자 속 ==는 깨지지 않는다', () => {
  const { w } = open();
  try {
    const r = w.eval(`(()=>{const a=mhParse('그냥 메모\\n둘째 줄');const b=mhParse('a == b');return {a:mhPack(a.t,a.c),at:a.t,bt:b.t,bpack:mhPack(b.t,b.c)}})()`);
    assert.equal(r.a, '그냥 메모\n둘째 줄');
    assert.equal(r.at, '그냥 메모\n둘째 줄');
    assert.equal(r.bt, 'a == b');
    assert.equal(w.eval(`mhParse(${JSON.stringify(r.bpack)}).t`), 'a == b'.replace('==', '=​='));
  } finally { w.close(); }
});

test('편집 영역에 칠한 글자는 mark 로 그려지고 읽으면 색이 돌아온다', () => {
  const { w } = open();
  try {
    const r = w.eval(`(()=>{const ed=document.createElement('div');mhRender(ed,'가 ==나== ==b:다==');const marks=[...ed.querySelectorAll('mark')].map(m=>m.className+':'+m.textContent);const q=mhRead(ed,true);return {marks,pack:mhPack(q.t,q.c)}})()`);
    assert.deepEqual([...r.marks], ['mh mh-yellow:나', 'mh mh-blue:다']);
    assert.equal(r.pack, '가 ==나== ==b:다==');
  } finally { w.close(); }
});

test('형광펜 줄: 도장 27일에는 없고 28일에는 5색과 지우개가 보인다', () => {
  for (const [days, expect] of [[27, false], [28, true]]) {
    const { w } = open({ days });
    try {
      w.eval('dyMode="day";renderDiary()');
      const bar = w.document.getElementById('dyHl');
      assert.equal(!bar.hidden, expect, `${days}일`);
      if (expect) assert.equal(bar.querySelectorAll('button').length, 6);
    } finally { w.close(); }
  }
});

test('메모지 속지 4종은 새 이름이고 기본이 아닌 속지에는 마스킹 테이프가 붙는다', () => {
  const { w } = open({ days: 30 });
  try {
    assert.deepEqual([...w.eval("['lined','grid','dot','biggrid'].map(id=>PAPERS.find(p=>p.id===id).name)")], ['핑크 줄노트', '연노랑 모눈', '라벤더 도트', '민트 무지']);
    w.eval("dyMode='day';renderDiary()");
    assert.equal(w.document.querySelector('.dyarea').classList.contains('taped'), false, '기본 속지는 테이프 없음');
    w.eval("OWNED.add('paper_notes');S.dyPaper='grid';renderDiary()");
    assert.equal(w.document.querySelector('.dyarea').classList.contains('taped'), true);
    assert.ok(w.document.querySelector('.dyedit.paper-grid'));
  } finally { w.close(); }
});

test('스티커 탭: 산 팩 하나가 탭 하나이고 전체가 맨 앞이다', () => {
  const { w } = open();
  try {
    const r = w.eval(`(()=>{OWNED.add('sticker_sched');OWNED.add('sticker_life');const box=document.createElement('div');const pool=ownedStickers();stkTab='all';stkTabsDraw(box,pool,()=>{});return {tabs:[...box.querySelectorAll('button')].map(b=>b.textContent),hidden:box.hidden,inSched:stkIn('fx:hospital','sticker_sched'),inLife:stkIn('fx:hospital','sticker_life'),all:stkIn('fx:hospital','all')}})()`);
    assert.deepEqual([...r.tabs], ['전체', '건강·병원', '운동·활동']);
    assert.equal(r.hidden, false);
    assert.equal(r.inSched, true);
    assert.equal(r.inLife, false);
    assert.equal(r.all, true);
  } finally { w.close(); }
});

test('산 팩이 하나뿐이면 탭 줄을 숨긴다', () => {
  const { w } = open();
  try {
    const hidden = w.eval(`(()=>{OWNED.add('sticker_sched');const box=document.createElement('div');stkTab='all';stkTabsDraw(box,ownedStickers(),()=>{});return box.hidden})()`);
    assert.equal(hidden, true);
  } finally { w.close(); }
});

test('외부 일러스트 팩의 그림 파일과 이름이 모두 있다', () => {
  const { w } = open();
  try {
    const keys = [...w.eval(`Object.values(STICKER_PACKS).flatMap(p=>p.list).filter(e=>e.startsWith('fx:')).map(e=>e.slice(3))`)];
    assert.ok(keys.length >= 600, '그림 수 ' + keys.length);
    const missing = keys.filter((k) => !fs.existsSync(path.join(__dirname, '..', 'stk', 'fx', k + '.png')));
    assert.deepEqual(missing, [], '그림 파일 없음');
    const noName = keys.filter((k) => !w.eval(`!!FX_NAMES[${JSON.stringify(k)}]`));
    assert.deepEqual(noName, [], '한글 이름 없음');
    assert.equal(new Set(keys).size, keys.length, '팩끼리 같은 그림이 겹침');
  } finally { w.close(); }
});
