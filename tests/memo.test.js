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

test('스티커 분류: 일정 30종은 주제로, 나머지는 팩으로 나뉜다', () => {
  const { w } = open();
  try {
    const f = (e) => w.eval(`stkCat(${JSON.stringify(e)})`);
    assert.equal(f('sv:pn_gym'), 'health');
    assert.equal(f('sv:cp_hospital'), 'schedule');
    assert.equal(f('sv:wc_study'), 'study');
    assert.equal(f('sv:wc_rest'), 'daily');
    assert.equal(f('sv:fw_rain'), 'weather');
    assert.equal(f('hl:marker'), 'deco');
  } finally { w.close(); }
});

test('모든 스티커가 분류에 들어간다(빠진 주제 없음)', () => {
  const { w } = open();
  try {
    const bad = w.eval(`Object.values(STICKER_PACKS).flatMap(p=>p.list).filter(e=>!['daily','schedule','health','study','weather','deco'].includes(stkCat(e)))`);
    assert.deepEqual([...bad], []);
    const topics = w.eval("STICKER_PACKS.sticker_sched.list.map(e=>e.replace(/^sv:pn_/,''))");
    const missing = [...topics].filter((t) => !w.eval(`TOPIC_CAT[${JSON.stringify(t)}]`));
    assert.deepEqual(missing, [], '일정 주제 분류 누락');
  } finally { w.close(); }
});
