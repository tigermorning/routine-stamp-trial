// 스티커 부품 라이브러리(docs/sticker-style-guide.md 6절). 팩 화풍을 받아 반복되는 조각을 같은 규칙으로 그린다.
// 그림 판은 48x48. 빛은 왼쪽 위에서 온다.

function hexToRgb(h) { return [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)); }
function rgbToHex(a) { return '#' + a.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join(''); }
const mix = (h, t, w) => rgbToHex(hexToRgb(h).map((v, i) => v + (hexToRgb(t)[i] - v) * w));
const darken = (h, w = .2) => mix(h, '#3a2018', w);
const lighten = (h, w = .5) => mix(h, '#ffffff', w);
const r1 = n => +n.toFixed(2);

// style: { line, w, wd(디테일 선), shadeShift, shadeAmt, uid }
function kit(style) {
  const L = style.line, W = style.w, WD = style.wd ?? W * .7;
  let n = 0;
  const uid = style.uid;
  const stroke = (w = W, c = L) => `fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"`;
  const pencil = style.material === 'pencil';
  const defs = new Map();
  // 색연필: 같은 색의 빗금 무늬(바탕은 옅게), 그림자용 교차 빗금
  const hatch = (c, angle, dens = 1.9, w = 1.05, base = .3) => {
    const id = `${uid}h${c.slice(1)}${angle < 0 ? 'n' : 'p'}`;
    if (!defs.has(id)) defs.set(id, `<pattern id="${id}" patternUnits="userSpaceOnUse" width="${dens}" height="${dens}" patternTransform="rotate(${angle})">${base ? `<rect width="${dens}" height="${dens}" fill="${c}" opacity="${base}"/>` : ''}<line x1="0" y1="0" x2="0" y2="${dens}" stroke="${c}" stroke-width="${w}"/></pattern>`);
    return `url(#${id})`;
  };
  // 색연필 윤곽선: 물건 색의 진한 색으로, 살짝 어긋난 두 번 선
  const sketch = (d, c, w) => `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" opacity=".92"/><path d="${d}" fill="none" stroke="${c}" stroke-width="${r1(w * .55)}" stroke-linecap="round" stroke-linejoin="round" opacity=".45" transform="translate(.45 -.35)"/>`;
  const K = {
    darken, lighten, mix,
    pencil,
    // 그림 전체 감싸기: 색연필이면 무늬 정의와 종이 결 필터를 붙인다
    wrap(inner) {
      if (!pencil) return inner;
      const f = `${uid}grain`;
      return `<defs>${[...defs.values()].join('')}<filter id="${f}" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="${style.grain ?? .95}" numOctaves="2" seed="${style.seed ?? 7}" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -${style.grainK ?? 1} ${style.grainB ?? 1.3}" result="a"/><feComposite in="SourceGraphic" in2="a" operator="in"/></filter></defs><g filter="url(#${f})">${inner}</g>`;
    },
    // 작은 보조 요소의 면(반짝이·하트·물방울)
    acc(d, c) {
      if (!pencil) return `<path d="${d}" fill="${c}" ${stroke(WD * .85).replace('fill="none" ', '')}/>`;
      return `<path d="${d}" fill="${c}" opacity=".85"/>` + sketch(d, darken(c, .4), .9);
    },
    // 면 하나: 그림자 색을 깔고, 밝은 색을 왼쪽 위로 옮겨 모양 안에서만 덮은 뒤 윤곽선을 그린다(자동 2톤).
    obj(d, fill, o = {}) {
      if (pencil) {
        const id = `${uid}m${++n}`;
        const s = o.shift ?? style.shadeShift ?? 2.2;
        const edge = o.edge ?? darken(fill, .42);
        let body = `<path d="${d}" fill="${hatch(fill, o.angle ?? 38, o.dens ?? 1.7, 1.05, o.base ?? style.base ?? .55)}"/>`;
        if (!o.flat) body += `<mask id="${id}"><path d="${d}" fill="#fff"/><path d="${d}" fill="#000" transform="translate(${-s} ${-s})"/></mask><path d="${d}" fill="${hatch(darken(fill, .3), -42, 1.7, .95, 0)}" mask="url(#${id})"/>`;
        return body + (o.noline ? '' : sketch(d, edge, o.w ?? W));
      }
      const id = `${uid}c${++n}`;
      const s = o.shift ?? style.shadeShift ?? 1.7;
      const shade = o.shade ?? darken(fill, style.shadeAmt ?? .2);
      const body = o.flat ? `<path d="${d}" fill="${fill}"/>`
        : `<clipPath id="${id}"><path d="${d}"/></clipPath><path d="${d}" fill="${shade}"/><g clip-path="url(#${id})"><path d="${d}" fill="${fill}" transform="translate(${-s} ${-s})"/></g>`;
      return body + (o.noline ? '' : `<path d="${d}" ${stroke(o.w ?? W)}/>`);
    },
    // 원·타원·둥근 사각형을 path 로 바꿔 obj 로 그린다
    circ(cx, cy, r) { return `M${r1(cx - r)} ${cy} a${r} ${r} 0 1 0 ${r1(r * 2)} 0 a${r} ${r} 0 1 0 ${r1(-r * 2)} 0Z`; },
    ell(cx, cy, rx, ry) { return `M${r1(cx - rx)} ${cy} a${rx} ${ry} 0 1 0 ${r1(rx * 2)} 0 a${rx} ${ry} 0 1 0 ${r1(-rx * 2)} 0Z`; },
    rr(x, y, w, h, r) { r = Math.min(r, w / 2, h / 2); return `M${x + r} ${y} H${r1(x + w - r)} Q${x + w} ${y} ${x + w} ${y + r} V${r1(y + h - r)} Q${x + w} ${y + h} ${r1(x + w - r)} ${y + h} H${x + r} Q${x} ${y + h} ${x} ${r1(y + h - r)} V${y + r} Q${x} ${y} ${x + r} ${y}Z`; },
    line(d, w = W, c = L) { return pencil ? sketch(d, c, w) : `<path d="${d}" ${stroke(w, c)}/>`; },
    detail(d, w = WD, c = L) { return pencil ? sketch(d, c, w) : `<path d="${d}" ${stroke(w, c)}/>`; },
    dot(x, y, r = 1.3, c = L) { return `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`; },
    // 흰 하이라이트 획(왼쪽 위 면에)
    hi(d, w = 1.5) { return `<path d="${d}" ${stroke(w, '#ffffff')} opacity=".9"/>`; },
    g(t, inner) { return `<g transform="${t}">${inner}</g>`; },
    // ---- 보조 요소 ----
    sparkle(x, y, s = 3.2, c = '#ffd35c') {
      const k = s * .28;
      return K.acc(`M${x} ${r1(y - s)} Q${r1(x + k)} ${r1(y - k)} ${r1(x + s)} ${y} Q${r1(x + k)} ${r1(y + k)} ${x} ${r1(y + s)} Q${r1(x - k)} ${r1(y + k)} ${r1(x - s)} ${y} Q${r1(x - k)} ${r1(y - k)} ${x} ${r1(y - s)}Z`, c);
    },
    heart(x, y, s = 3, c = '#ff8fab') {
      return K.acc(`M${x} ${r1(y + s)} C${r1(x - s * 2.1)} ${r1(y - s * .1)} ${r1(x - s * 1)} ${r1(y - s * 1.9)} ${x} ${r1(y - s * .55)} C${r1(x + s * 1)} ${r1(y - s * 1.9)} ${r1(x + s * 2.1)} ${r1(y - s * .1)} ${x} ${r1(y + s)}Z`, c);
    },
    drop(x, y, s = 2.4, c = '#7cc6f2') {
      return K.acc(`M${x} ${r1(y - s * 1.6)} Q${r1(x + s * 1.2)} ${r1(y - s * .1)} ${r1(x + s)} ${r1(y + s * .4)} A${s} ${s} 0 0 1 ${r1(x - s)} ${r1(y + s * .4)} Q${r1(x - s * 1.2)} ${r1(y - s * .1)} ${x} ${r1(y - s * 1.6)}Z`, c);
    },
    steam(x, y, h = 8) { return K.detail(`M${x} ${y} q-2.2 ${r1(-h / 4)} 0 ${r1(-h / 2)} q2.2 ${r1(-h / 4)} 0 ${r1(-h / 2)}`); },
    // 움직임 선: [x1,y1,x2,y2] 목록
    motion(list, w = WD) { return list.map(([a, b, c, d]) => K.detail(`M${a} ${b} L${c} ${d}`, w)).join(''); },
    blush(x, y, r = 2) { return `<ellipse cx="${x}" cy="${y}" rx="${r}" ry="${r1(r * .7)}" fill="#ff8fab" opacity=".55"/>`; },
    // 얼굴 표정: smile | happy(눈 감고 웃음) | sleep | wow
    face(cx, cy, s = 1, kind = 'smile') {
      const ex = 4.6 * s, ey = 0;
      let eyes, mouth;
      if (kind === 'happy') eyes = K.detail(`M${r1(cx - ex - 1.6 * s)} ${cy} q${r1(1.6 * s)} ${r1(-1.8 * s)} ${r1(3.2 * s)} 0 M${r1(cx + ex - 1.6 * s)} ${cy} q${r1(1.6 * s)} ${r1(-1.8 * s)} ${r1(3.2 * s)} 0`, WD);
      else if (kind === 'sleep') eyes = K.detail(`M${r1(cx - ex - 1.6 * s)} ${cy} q${r1(1.6 * s)} ${r1(1.8 * s)} ${r1(3.2 * s)} 0 M${r1(cx + ex - 1.6 * s)} ${cy} q${r1(1.6 * s)} ${r1(1.8 * s)} ${r1(3.2 * s)} 0`, WD);
      else eyes = K.dot(r1(cx - ex), cy + ey, 1.35 * s) + K.dot(r1(cx + ex), cy + ey, 1.35 * s) + `<circle cx="${r1(cx - ex - .45 * s)}" cy="${r1(cy - .5 * s)}" r="${r1(.45 * s)}" fill="#fff"/><circle cx="${r1(cx + ex - .45 * s)}" cy="${r1(cy - .5 * s)}" r="${r1(.45 * s)}" fill="#fff"/>`;
      if (kind === 'wow') mouth = `<ellipse cx="${cx}" cy="${r1(cy + 3.6 * s)}" rx="${r1(1.4 * s)}" ry="${r1(1.8 * s)}" fill="${L}"/>`;
      else if (kind === 'sleep') mouth = K.detail(`M${r1(cx - 1 * s)} ${r1(cy + 3.4 * s)} q${r1(1 * s)} ${r1(.8 * s)} ${r1(2 * s)} 0`, WD);
      else mouth = K.detail(`M${r1(cx - 2 * s)} ${r1(cy + 2.6 * s)} q${r1(2 * s)} ${r1(2.4 * s)} ${r1(4 * s)} 0`, WD);
      return eyes + mouth + K.blush(r1(cx - ex - 2 * s), r1(cy + 2.4 * s), 1.9 * s) + K.blush(r1(cx + ex + 2 * s), r1(cy + 2.4 * s), 1.9 * s);
    },
  };
  return K;
}

module.exports = { kit, darken, lighten, mix };
