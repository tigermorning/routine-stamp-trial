// 한국어 고정(KO_ONLY) 시험. 근거: 2026-11-09 사용자 결정 «한국어판이 완성될 때까지 다른 언어는 숨긴다(지우지 않는다)».
// 브라우저 언어가 영어이고 저장해 둔 언어가 en 이어도 화면은 한국어이고, 설정의 언어 선택은 숨겨진다. 번역 데이터(T, LANGS)는 그대로 남아 있다.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const HTML = fs.readFileSync(process.env.INDEX_HTML || path.join(__dirname, '..', 'index.html'), 'utf8');

function open({ browserLang, savedLang }) {
  const saved = {
    slots: [{ id: 's1', key: 'wakeup', icon: 'wake', color: '#ffd666' }, { id: 's2', key: 'breakfast', icon: 'meal', color: '#ffb85c' }, { id: 's3', key: 'move', icon: 'walkrun', color: '#5fcfb0' }],
    log: {}, shelf: [], first: '2026-01-01', hint: true, draft: '', gift: false, lang: savedLang,
  };
  const dom = new JSDOM(HTML, {
    runScripts: 'dangerously',
    url: 'http://localhost/',
    beforeParse(w) {
      Object.defineProperty(w.navigator, 'language', { value: browserLang, configurable: true });
      w.localStorage.setItem('routine-trial-v1', JSON.stringify(saved));
    },
  });
  return dom.window;
}

test('영어 브라우저에 영어가 저장돼 있어도 한국어로 보인다', () => {
  const w = open({ browserLang: 'en-US', savedLang: 'en' });
  try {
    assert.equal(w.eval('KO_ONLY'), true);
    assert.equal(w.eval('lang'), 'ko');
    assert.equal(w.eval("t('h1')"), w.eval("T.ko.h1"));
  } finally { w.close(); }
});

test('설정에서 언어 선택이 숨겨진다', () => {
  const w = open({ browserLang: 'ja-JP', savedLang: undefined });
  try {
    w.eval('renderSettings()');
    assert.equal(w.document.getElementById('langRow').hidden, true);
  } finally { w.close(); }
});

test('번역 데이터와 언어 목록은 지우지 않고 남아 있다(다시 켤 수 있다)', () => {
  const w = open({ browserLang: 'ko-KR', savedLang: 'ko' });
  try {
    assert.equal(w.eval('LANGS.length'), 10);
    assert.ok(w.eval("Object.keys(T.en).length") > 150);
  } finally { w.close(); }
});
