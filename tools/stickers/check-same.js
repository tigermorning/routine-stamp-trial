// 부품을 고친 뒤 이미 앱에 들어간 팩의 그림이 그대로인지 확인한다: node tools/stickers/check-same.js <팩모듈> <접두사>
const fs = require('fs');
const path = require('path');
const [, , mod, prefix] = process.argv;
const items = require(path.resolve(__dirname, mod)).build(prefix);
const html = fs.readFileSync(path.resolve(__dirname, '../../index.html'), 'utf8');
const diff = [];
for (const [id, v] of Object.entries(items)) {
  const a = html.indexOf(`<symbol id="sv-${id}" viewBox="0 0 48 48">`);
  const b = html.indexOf('</symbol>', a);
  const cur = a < 0 ? null : html.slice(a + `<symbol id="sv-${id}" viewBox="0 0 48 48">`.length, b);
  if (cur !== v.svg) diff.push(id);
}
console.log(`같음 ${Object.keys(items).length - diff.length}/${Object.keys(items).length}` + (diff.length ? ' 다름: ' + diff.join(',') : ''));
process.exit(diff.length ? 1 : 0);
