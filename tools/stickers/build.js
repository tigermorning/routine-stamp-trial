// 스티커 팩을 만든다(docs/sticker-style-guide.md 6·7절).
//   node tools/stickers/build.js review <팩>   → tools/stickers/out/<팩>.html 검수 그림판(192px·48px·26px)
//   node tools/stickers/build.js apply <팩>    → index.html 의 그림 묶음과 팩 목록에 넣기
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '../..');
const PACKS = {
  // 팩 이름: [모듈, 그림 id 접두사, 앱 팩 id, 앱 팩 이름]
  pen: ['./packs/pen', 'pn_', 'sticker_sched', '펜 일러스트'],
  pencil: ['./packs/pencil', 'cp_', 'sticker_life', '색연필'],
};
const [, , cmd, packName, only] = process.argv;
const def = PACKS[packName];
if (!def) { console.error('팩 이름: ' + Object.keys(PACKS).join(', ')); process.exit(1); }
const mod = require(def[0]);
const items = mod.build(def[1]);
const ids = Object.keys(items);
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const STICKER_CSS = 'filter:drop-shadow(1.2px 0 0 #fff) drop-shadow(-1.2px 0 0 #fff) drop-shadow(0 1.2px 0 #fff) drop-shadow(0 -1.2px 0 #fff) drop-shadow(0 1px 1.4px rgba(60,40,30,.3))';

if (cmd === 'review') {
  const pick = only ? ids.filter(i => only.split(',').some(k => i.endsWith('_' + k))) : ids;
  const big = pick.map(id => `<figure><svg viewBox="0 0 48 48" class="b">${items[id].svg}</svg><figcaption>${esc(items[id].name)}</figcaption></figure>`).join('');
  const small = pick.map(id => `<svg viewBox="0 0 48 48" class="s">${items[id].svg}</svg>`).join('');
  const mid = pick.map(id => `<svg viewBox="0 0 48 48" class="m">${items[id].svg}</svg>`).join('');
  const html = `<!doctype html><meta charset="utf-8"><title>${packName} 검수</title><style>
body{font-family:sans-serif;background:#f1ece4;margin:16px;color:#4a3a30}
.grid{display:flex;flex-wrap:wrap;gap:10px}figure{margin:0;text-align:center;font-size:13px}
svg{${STICKER_CSS}}.b{width:192px;height:192px;background:#fbf8f2;border-radius:12px}
.m{width:48px;height:48px;margin:4px}.s{width:26px;height:26px;margin:3px}h2{font-size:15px;margin:18px 0 6px}
</style><h2>192px (${pick.length}종)</h2><div class="grid">${big}</div><h2>48px</h2><div>${mid}</div><h2>26px</h2><div>${small}</div>`;
  const out = path.join(__dirname, 'out');
  fs.mkdirSync(out, { recursive: true });
  fs.writeFileSync(path.join(out, packName + '.html'), html);
  console.log('검수 그림판', path.join(out, packName + '.html'), pick.length + '종');
} else if (cmd === 'apply') {
  const p = path.join(ROOT, 'index.html');
  let s = fs.readFileSync(p, 'utf8');
  const crlf = s.includes('\r\n');
  if (crlf) s = s.replace(/\r\n/g, '\n');
  const [, prefix, packId, packLabel] = def;
  // 이 팩이 예전에 쓰던 그림(같은 팩 목록에 있던 sv: id)과 이 접두사의 그림을 지운다
  const m = s.match(new RegExp(`\\n  ${packId}:\\{name:'[^']*',list:\\[([^\\]]*)\\]\\},`));
  if (!m) throw new Error('팩 목록 없음: ' + packId);
  // --keep-old: 예전 그림은 남긴다(이미 달력에 붙여 저장한 스티커가 빈칸이 되지 않게). 팩 목록만 바뀐다.
  const keepOld = process.argv.includes('--keep-old');
  const oldIds = keepOld ? [] : [...m[1].matchAll(/'sv:([a-z0-9_]+)'/g)].map(x => x[1]).filter(i => !i.startsWith(prefix));
  for (const id of new Set([...oldIds, ...ids])) s = s.replace(new RegExp(`<symbol id="sv-${id}" viewBox="0 0 48 48">[\\s\\S]*?</symbol>`), '');
  const sp = s.indexOf('<svg id="svSprite"');
  const spEnd = s.indexOf('</svg>', sp);
  s = s.slice(0, spEnd) + ids.map(id => `<symbol id="sv-${id}" viewBox="0 0 48 48">${items[id].svg}</symbol>`).join('') + s.slice(spEnd);
  s = s.replace(m[0], `\n  ${packId}:{name:'${packLabel}',list:[${ids.map(i => `'sv:${i}'`).join(',')}]},`);
  const nm = s.match(/const SV_NAMES=\{([^\n]*)\};/);
  let inner = nm[1];
  for (const id of new Set([...oldIds, ...ids])) inner = inner.replace(new RegExp(`,? ?"${id}": "[^"]*"`), '');
  inner = inner.replace(/^\s*,\s*/, '').replace(/,\s*$/, '') + ', ' + ids.map(id => `"${id}": "${items[id].name}"`).join(', ');
  s = s.replace(nm[0], `const SV_NAMES={${inner}};`);
  fs.writeFileSync(p, crlf ? s.replace(/\n/g, '\r\n') : s);
  console.log('적용', packId, ids.length + '종, 지운 예전 그림', oldIds.length);
} else {
  console.error('명령: review | apply'); process.exit(1);
}
