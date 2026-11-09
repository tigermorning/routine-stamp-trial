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
    assert.deepEqual([...w.eval("['lined','grid','dot','biggrid'].map(id=>PAPERS.find(p=>p.id===id).name)")], ['줄노트', '모눈', '도트', '큰 모눈']);
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

test('배경색: 고른 색이 모든 속지 메모 칸에 적용되고 잘못된 값은 무시한다', () => {
  const { w } = open({ days: 30 });
  try {
    const run = (color, paper) => w.eval(`(()=>{S.dyBg=${JSON.stringify(color)};OWNED.add('paper_notes');OWNED.add('paper_mood');S.dyPaper=${JSON.stringify(paper)};dyMode='day';renderDiary();const ed=document.querySelector('.dyedit');return {cls:ed.className,style:ed.getAttribute('style')||''}})()`);
    for (const paper of ['plain', 'lined', 'grid', 'dot', 'biggrid', 'kraft', 'sticky', 'oxford', 'wash']) {
      const r = run('#dbeeff', paper);
      assert.ok(r.cls.includes('paper-' + paper), paper);
      assert.ok(r.style.includes('--pbg') && r.style.includes('#dbeeff'), paper + ' ' + r.style);
    }
    assert.ok(!run('red', 'lined').style.includes('--pbg'), '잘못된 색은 무시');
    assert.ok(run('#10131a', 'grid').style.includes('color'), '어두운 색은 글자를 밝게');
  } finally { w.close(); }
});

test('배경색 색상표: 기본·12색·직접 고르기가 꾸미기 패널에 있고 고르면 저장된다', () => {
  const { w } = open({ days: 30 });
  try {
    w.eval("dyDeco=true;dyMode='day';renderDiary()");
    const doc = w.document;
    assert.equal(doc.querySelectorAll('#dyBg .dybg').length, 13);
    assert.ok(doc.getElementById('dyBgIn'));
    doc.querySelectorAll('#dyBg .dybg')[8].click();
    assert.equal(w.eval('S.dyBg'), '#e9e0ff');
    assert.ok((doc.querySelector('.dyedit').getAttribute('style') || '').includes('#e9e0ff'));
    doc.querySelector('#dyBg .dybg.none').click();
    assert.equal(w.eval("S.dyBg===undefined"), true);
  } finally { w.close(); }
});

test('크라프트지는 질감 없이 색만 쓴다(질감은 나무처럼 보여 뺐다)', () => {
  const rule = HTML.slice(HTML.indexOf('#dyBody .paper-kraft{'), HTML.indexOf('#dyBody .paper-kraft{') + 200);
  assert.ok(!rule.includes('feTurbulence') && !rule.includes('url('), '질감 없음');
  assert.ok(rule.includes('var(--pbg,#d8b88a)'), '크라프트 기본색');
});

test('모든 스티커를 할 일 칸 그림으로 고를 수 있다(외부 일러스트 포함, 하이라이트만 제외)', () => {
  const { w } = open({ days: 30 });
  try {
    const r = w.eval(`(()=>{['sticker_sched','sticker_highlight','icons_cute'].forEach(x=>OWNED.add(x));stkTab='all';editOpen=true;pickFor=0;renderEdit();
      const btns=[...document.querySelectorAll('#picker .pka')];const keys=btns.map(b=>b.dataset.a);
      const fx=btns.find(b=>b.dataset.a==='fx:hospital');if(fx)fx.click();
      const art=S.slots[0].art;const icon=iconOf(S.slots[0]);
      return {keys:keys.length,hasFx:keys.some(k=>k.startsWith('fx:')),hasIg:keys.some(k=>k.startsWith('ig:')),hasHl:keys.some(k=>k.startsWith('hl:')),art,icon}})()`);
    assert.equal(r.hasFx, true, '외부 일러스트가 고르기에 나온다');
    assert.equal(r.hasIg, true, '예전 아이콘 글리프도 나온다');
    assert.equal(r.hasHl, false, '날짜 하이라이트는 그림이 아니라서 뺀다');
    assert.equal(r.art, 'fx:hospital');
    assert.ok(r.icon.includes('<img') && r.icon.includes('/stk/fx/hospital.png'), '칸 그림이 외부 일러스트 그림 파일을 그린다: ' + r.icon);
  } finally { w.close(); }
});

test('상점 탭은 스티커 하나뿐이고 아이콘 팩 구분이 없다', () => {
  const { w } = open();
  try {
    const tabs = [...w.document.querySelectorAll('#shopTabs button')].map((b) => b.textContent);
    assert.ok(tabs.includes('스티커') && !tabs.some((x) => x.includes('아이콘')), tabs.join(','));
    assert.equal(w.eval("Object.keys(STICKER_PACKS).filter(id=>id.startsWith('icons_')).length"), 3);
  } finally { w.close(); }
});

test('Iconify 팩(fv:)의 그림 파일·이름·출처가 모두 있고 허용 라이선스만 쓴다', () => {
  const { w } = open();
  try {
    const keys = [...w.eval(`Object.values(STICKER_PACKS).flatMap(p=>p.list).filter(e=>e.startsWith('fv:')).map(e=>e.slice(3))`)];
    assert.ok(keys.length >= 350, '그림 수 ' + keys.length);
    const sources = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'stk', 'fv', 'SOURCES.json'), 'utf8'));
    for (const k of keys) {
      assert.ok(fs.existsSync(path.join(__dirname, '..', 'stk', 'fv', k + '.svg')), '그림 파일 ' + k);
      assert.ok(w.eval(`!!FV_NAMES[${JSON.stringify(k)}]`), '이름 ' + k);
      assert.ok(['MIT', 'Apache-2.0', 'CC-BY-4.0', 'CC0-1.0'].includes((sources.stickers[k] || {}).license), '라이선스 ' + k);
    }
    assert.equal(new Set(keys).size, keys.length, '팩끼리 겹침');
    const html = w.eval(`artSVG('fv:${keys[0]}','x')`);
    assert.ok(html.includes('/stk/fv/' + keys[0] + '.svg'), '칸 그림으로도 그려진다');
    assert.ok(w.eval(`stkFace('fv:${keys[0]}')`).includes('/stk/fv/'));
  } finally { w.close(); }
});

test('상점 번들 미리 보기 안에서는 그 번들의 메모지 4종만 보이고, «모든 메모지»로 돌아간다', () => {
  const { w, errors } = open({ days: 30 });
  try {
    w.eval("dyDeco=true;dyBundlePv='paper_mood';dyPaperPv='kraft';renderDyDeco()");
    const names = [...w.document.querySelectorAll('#dyPapers button')].map((b) => b.textContent.replace('🔒 ', ''));
    assert.deepEqual(names, ['‹ 모든 메모지', '크라프트', '포스트잇', '옥스포드 노트', '수채']);
    w.eval("dyBundlePv='paper_notes';dyPaperPv='lined';renderDyDeco()");
    assert.deepEqual([...w.document.querySelectorAll('#dyPapers button')].map((b) => b.textContent.replace('🔒 ', '')), ['‹ 모든 메모지', '줄노트', '모눈', '도트', '큰 모눈']);
    w.document.querySelector('#dyPapers button').click();
    assert.equal(w.document.querySelectorAll('#dyPapers button').length, 9);
    assert.deepEqual(errors, []);
  } finally { w.close(); }
});
