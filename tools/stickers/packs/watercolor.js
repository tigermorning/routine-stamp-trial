// 수채 팩(docs/sticker-style-guide.md 5절): 반투명 물감 겹, 번진 가장자리와 물감 고임, 오른쪽 아래 덧칠, 군데군데 끊긴 가는 잉크 선.
// 펜·색연필과 같은 일정 30개 주제를 «셋째 구성»으로 새로 그린다. 수채의 강점인 풍경·물·빛을 살린다.
const { kit } = require('../parts');

const C = {
  rose: '#f28b82', yellow: '#f6c453', green: '#7cc4a4', leaf: '#8cbf6a', blue: '#6fa8dc', sky: '#a9d3ee', violet: '#a78bd4',
  orange: '#f4a259', pink: '#ec9fb6', sepia: '#c49a6c', gray: '#a8b4c0', skin: '#f5c9a6', paper: '#f4f1ea', sand: '#ecd29b',
  wine: '#b5475a', coffee: '#a87452', cork: '#e3c08d',
};
const STYLE = { material: 'watercolor', line: '#5a4a42', ink: '#5a4a42', w: 1.1, wd: .9, shadeShift: 2.4, bleed: 1.8 };

const ART = {
  hospital: ['병원', K => K.line('M30 6 V42 M22 43.4 H38 M30 6 H20', 1.8, C.gray)
    + K.obj('M14 8 H26 Q27 8 27 9 V22 Q27 26 23 26 H17 Q13 26 13 22 V9 Q13 8 14 8Z', '#e3eef6')
    + K.obj('M13.4 14 H26.6 V22 Q26.6 25.6 23 25.6 H17 Q13.4 25.6 13.4 22Z', C.sky, { noline: true })
    + K.line('M20 15.6 V20.4 M17.6 18 H22.4', 1.4, C.rose)
    + K.obj(K.rr(18.4, 26, 3.2, 4.6, 1), '#e3eef6', { shift: .4 }) + K.detail('M20 30.6 Q20 40 30 36', .9, C.gray)
    + K.heart(39, 14, 3, C.pink)],
  dentist: ['치과', K => K.obj('M15 11 C11 11 9 15 10 19.6 C11 24 12.6 26.4 13.6 31.6 C14.6 37.4 15.8 41 18.6 41 C21.4 41 21.2 33.6 24 33.6 C26.8 33.6 26.6 41 29.4 41 C32.2 41 33.4 37.4 34.4 31.6 C35.4 26.4 37 24 38 19.6 C39 15 37 11 33 11 C29.4 11 27.6 13.2 24 13.2 C20.4 13.2 18.6 11 15 11Z', C.paper)
    + K.g('rotate(-35 31 18)', K.obj(K.rr(24, 15, 14, 6, 3), C.sand, { shift: .6 }) + K.obj(K.rr(28.6, 15.6, 4.8, 4.8, .8), '#f6e6c2', { flat: true, w: .7 }))
    + K.dot(18.6, 23, 1.2) + K.detail('M26.6 22 l2.4 1.2 l-2.4 1.2', .9) + K.detail('M19.6 28.4 q1.8 -1.6 3.6 0 q1.8 1.6 3.6 0', .9)
    + K.drop(8.4, 15, 2.2, C.sky) + K.wash(K.ell(16, 26.4, 2.4, 1.4), C.pink, .5)],
  pill: ['약 먹기', K => K.g('rotate(-12 22 25)', K.obj(K.rr(8, 9, 28, 32, 3), '#d9dfe6')
      + [16, 23, 30, 37].map(y => [15, 29].map(x => (x === 29 && y === 37) ? K.detail(K.rr(x - 5, y - 2.8, 10, 5.6, 2.8), .8, C.gray) : K.obj(K.rr(x - 5, y - 2.8, 10, 5.6, 2.8), y % 2 ? C.pink : C.sky, { shift: .6, w: .9 })).join('')).join(''))
    + K.sparkle(41, 9, 2.6, C.yellow)],
  gym: ['헬스', K => {
    // 앞에서 본 아령 두 개를 쌓은 모습(둥근 원판이 보이게) + 땀방울
    const bell = (y, c) => K.obj(K.rr(14, y - 1.8, 20, 3.6, 1.4), C.gray, { shift: .5 })
      + K.obj(K.ell(12, y, 4.4, 7.4), c) + K.obj(K.ell(36, y, 4.4, 7.4), c)
      + K.obj(K.ell(12, y, 1.6, 2.8), '#f4f1ea', { flat: true, w: .7 }) + K.obj(K.ell(36, y, 1.6, 2.8), '#f4f1ea', { flat: true, w: .7 });
    return K.wash(K.ell(24, 43, 17, 2.2), C.gray, .45) + bell(34.6, C.violet) + bell(20.6, C.rose)
      + K.drop(40, 7, 2.2, C.sky) + K.drop(44.4, 12.6, 1.6, C.sky) + K.sparkle(8, 8, 2.6, C.yellow);
  }],
  run: ['러닝', K => K.wash(K.circ(10, 10, 5), C.yellow, .7)
    + K.obj('M2 30 Q14 18 26 26 Q36 20 46 26 V46 H2Z', C.leaf, { noline: true })
    + K.wash('M2 36 Q16 30 30 36 Q38 33 46 35 V46 H2Z', C.green, .55)
    + K.line('M10 46 Q20 39 16 33 Q12 27 22 23 Q29 20 28 15', 4, C.sand)
    + [[14.6, 41.6, -40], [17.6, 37.4, -60], [14.2, 31.6, 30], [16.4, 27, 40], [21.4, 24, 70]].map(([x, y, r], i) => K.g(`rotate(${r} ${x} ${y})`, K.wash(K.ell(x + (i % 2 ? 1.2 : -1.2), y, 1, 1.7), '#7a5a40', .75))).join('')
    + K.line('M28 15 V4', 1.2, '#5a4a42') + K.obj('M28 4 H37 V10 H28Z', C.paper, { flat: true, w: .8 })
    + `<path d="M28 4 h3 v3 h-3Z M34 4 h3 v3 h-3Z M31 7 h3 v3 h-3Z" fill="#5a4a42" opacity=".75"/>`],
  yoga: ['요가', K => K.obj('M3 36 Q24 29 45 36 Q24 44 3 36Z', C.sky, { noline: true })
    + K.detail('M8 40 q4 -2 8 0 M30 41 q4 -2 8 0', .8, C.blue)
    + K.obj('M13 39 a6 3.2 0 1 0 12 0 a6 3.2 0 1 0 -12 0Z', C.leaf, { shift: .6 })
    + K.obj('M24 34 Q12 32 9 20 Q19 22 24 34Z', '#f4b6c8') + K.obj('M24 34 Q36 32 39 20 Q29 22 24 34Z', '#f4b6c8')
    + K.obj('M24 34 Q15 26 17 15 Q23 22 24 34Z', C.pink) + K.obj('M24 34 Q33 26 31 15 Q25 22 24 34Z', C.pink)
    + K.obj('M24 12 Q30.4 22 24 34 Q17.6 22 24 12Z', '#e9849f') + K.sparkle(40, 9, 2.6, C.yellow)],
  swim: ['수영', K => K.obj(K.rr(2, 24, 44, 3.4, 1), C.paper, { flat: true })
    + K.line('M14 30 V10 Q14 5 19 5 Q22 5 22 8', 2.4, C.gray) + K.line('M28 30 V10 Q28 5 33 5 Q36 5 36 8', 2.4, C.gray)
    + K.line('M14 15 H28 M14 21 H28', 2, C.gray)
    + K.obj('M2 28 Q8 26 14 28 T26 28 T38 28 T46 28 V46 H2Z', C.blue, { noline: true, alpha: .7 })
    + K.detail('M6 34 q3 -2 6 0 M24 38 q3 -2 6 0 M34 32 q3 -2 6 0', .9, '#e7f3fb') + K.detail('M8 42 H40', .6, '#e7f3fb')
    + K.sparkle(40, 10, 2.6, C.yellow)],
  skin: ['피부관리', K => K.obj(K.rr(13, 8, 16, 4, 1), C.gray, { shift: .4 })
    + K.obj('M13.4 12 H28.6 L27 37 Q26.8 39 24.8 39 H17.2 Q15.2 39 15 37Z', C.pink)
    + K.obj(K.rr(16.6, 39, 8.8, 5, 1.4), C.paper, { shift: .4 }) + K.obj(K.rr(15.6, 19, 11, 9, 1), C.paper, { flat: true, w: .8 })
    + K.obj('M34 44 Q33 30 30 20 Q36 28 36.6 44Z', C.green) + K.obj('M37.2 44 Q38 28 44 18 Q41 31 39.6 44Z', C.green) + K.obj('M35.6 44 Q34.4 34 38 26 Q39.2 36 37.8 44Z', C.leaf)
    + K.drop(32, 13, 2.2, C.sky) + K.sparkle(8, 10, 2.4, C.yellow)],
  nail: ['네일', K => K.wash('M7 12 Q20 4 36 9 Q37.4 12 34 13 Q20 9 9 15.4 Q5.6 15 7 12Z', C.rose, .6)
    + [[6, 28, 11, 13, C.rose], [18.4, 24, 12, 17, C.violet], [31.6, 30, 11, 12, C.orange]].map(([x, y, w, h, c]) => K.obj(K.rr(x + w / 2 - 2.4, y - 7, 4.8, 7.4, 1.2), '#6b5f66', { shift: .4 }) + K.obj(K.rr(x, y, w, h, 3.2), c) + K.hi(`M${x + 2.4} ${y + 3} V${y + h - 3}`, 1.1)).join('')
    + K.sparkle(42, 20, 2.6, C.yellow)],
  salon: ['미용실', K => K.g('rotate(-30 34 30)', K.obj(K.rr(31.6, 30, 4.8, 16, 2.4), C.sepia) + K.obj(K.ell(34, 23.4, 6.6, 8.4), '#d9b48c') + [[-2.6, -4], [0, -4], [2.6, -4], [-2.6, 0], [0, 0], [2.6, 0], [-2.6, 4], [0, 4], [2.6, 4]].map(([a, b]) => K.dot(34 + a, 23.4 + b, .7)).join(''))
    + K.g('rotate(25 17 27)', K.obj(K.rr(14.6, 26, 4.8, 17, 2.4), C.pink))
    + K.obj(K.circ(17, 16, 10.4), C.pink) + K.obj(K.circ(17, 16, 7.6), '#e3f1fa', { shift: .6 }) + K.hi('M12.6 13 Q14 10 17 9.6', 1.3)
    + K.sparkle(42, 6, 2.4, C.yellow)],
  meal: ['식사 약속', K => K.line('M6 12 V40 M4 12 V18 Q6 21 8 18 V12', 1.6, C.gray)
    + K.obj(K.rr(40, 12, 3.6, 28, 1.8), C.gray, { shift: .4 })
    + K.obj(K.circ(23.6, 26, 15), C.paper) + K.obj(K.circ(23.6, 26, 10.6), '#fbf9f4', { shift: .8 })
    + K.obj('M16 28 Q18 20 24 21 Q30 19 31 27 Q26 32 22 31 Q18 32 16 28Z', C.leaf)
    + K.obj(K.circ(21, 25, 2.6), C.rose, { shift: .4, w: .8 }) + K.obj(K.circ(27, 27, 2.4), C.rose, { shift: .4, w: .8 }) + K.wash(K.ell(24, 29, 3, 1.4), C.yellow, .7)],
  cafe: ['카페', K => K.obj(K.circ(20, 23, 14), C.paper) + K.obj(K.rr(29, 20.4, 6.4, 4.4, 2), C.paper, { shift: .4 })
    + K.obj(K.circ(20, 23, 9.4), '#fbf9f4') + K.obj(K.circ(20, 23, 7), C.coffee, { shift: 1 })
    + K.detail('M17 21 q3 -2 5 1 q1 3 -2 3', 1, '#e9cfae')
    + K.obj('M28 41 Q30 31 40 31 Q46.4 33 45 39 Q42 35 38 36 Q34 37 33 42Z', '#e9b35f') + K.detail('M33 33 L35 38 M38 31.6 L38.6 36 M42 32.6 L41 36.4', .8)],
  drinks: ['술자리', K => {
    const g = (t) => K.g(t, K.obj('M10 8 H24 Q24 22 17 23 Q10 22 10 8Z', '#eef3f7', { alpha: .55 })
      + K.obj('M10.5 13 H23.5 Q23 22 17 22.6 Q11 22 10.5 13Z', C.wine, { noline: true })
      + K.line('M17 22.6 V37.4', 2.2, '#9aa6b2') + K.obj(K.ell(17, 38.4, 6, 1.8), '#dfe7ee', { flat: true, w: .9 }) + K.hi('M12.4 10 Q12 15 13.6 19', 1));
    return g('rotate(-14 17 28) translate(-1 2)') + g('rotate(14 31 28) translate(15 2)')
      + K.drop(24, 7, 1.6, C.wine) + K.drop(20.6, 10, 1.2, C.wine) + K.drop(27.4, 10, 1.2, C.wine) + K.sparkle(42, 6, 2.4, C.yellow);
  }],
  birthday: ['생일', K => K.obj('M12 28 H36 L33 43 H15Z', C.sky) + K.detail('M16 29 L17.4 43 M20 29 L20.8 43 M24 29 V43 M28 29 L27.2 43 M32 29 L30.6 43', .8, '#4f86b5')
    + K.obj('M10 28 Q8 20 16 19.6 Q16 13 24 13 Q32 13 32 19.6 Q40 20 38 28Z', C.pink)
    + K.detail('M15 24 l2 1 M22 18 l1.4 1.4 M29 23 l2 -1 M33 26 l1 1.6 M19 26.6 l-1.4 1', 1.2, C.violet)
    + K.obj(K.rr(22.4, 6.6, 3.2, 7, 1), C.yellow, { shift: .4, w: .8 }) + K.wash('M24 1.6 Q27 4.8 24 6.6 Q21 4.8 24 1.6Z', C.orange, .9)
    + K.sparkle(41, 10, 2.4, C.yellow) + K.sparkle(7, 14, 2, C.yellow)],
  date: ['데이트', K => K.line('M14 24 Q24 6 34 24', 2.2, C.sepia)
    + K.g('rotate(-30 30 14)', K.obj(K.rr(22, 12, 16, 4.6, 2.3), '#e8c38f', { shift: .5 }))
    + K.obj('M8 24 H40 L37 42 H11Z', C.sepia)
    + K.detail('M10 30 H38 M10.6 36 H37.4 M16 24 L17 42 M24 24 V42 M32 24 L31 42', .8, '#8a6440')
    + K.obj('M9 24 L15 31 L21 24Z', C.rose, { shift: .5 }) + K.detail('M12 24 L15 27.4 M18 24 L15 27.4', .7, C.paper)
    + K.heart(24, 8, 3.2, C.rose)],
  meeting: ['회의', K => K.obj(K.rr(5, 7, 38, 32, 2), C.cork) + K.line(K.rr(5, 7, 38, 32, 2), 1.6, C.sepia)
    + [[9, 11, 13, 11, -6, C.yellow], [25, 11.6, 13, 11, 5, C.pink], [11, 25, 13, 11, 4, C.leaf], [27, 26, 12, 10, -5, C.sky]].map(([x, y, w, h, r, c]) => K.g(`rotate(${r} ${x + w / 2} ${y + h / 2})`, K.obj(K.rr(x, y, w, h, .8), c, { shift: .6, w: .9 }) + K.detail(`M${x + 2.4} ${y + 4.4} H${x + w - 2.4} M${x + 2.4} ${y + 7.4} H${x + w - 4.6}`, .7)) + K.dot(x + w / 2, y + 1.4, 1.2, C.rose)).join('')
    + K.line('M12 39 L9 45 M36 39 L39 45', 1.6, C.sepia)],
  trip: ['출장', K => K.line('M2 38.6 H46', 1.2, C.gray) + K.detail('M6 41 V38.6 M14 41 V38.6 M22 41 V38.6 M30 41 V38.6 M38 41 V38.6', 1.6, C.sepia)
    + K.obj('M4 15 H34 Q44.6 15 44.6 26 V32 H4Z', C.paper) + K.obj(K.rr(4, 23, 40.4, 3.2, .6), C.blue, { flat: true, noline: true })
    + [7, 14, 21].map(x => K.obj(K.rr(x, 17.4, 5, 4, 1), C.sky, { flat: true, w: .7 })).join('') + K.obj('M33 17.4 H35 Q41 17.4 42 22 H33Z', C.sky, { flat: true, w: .7 })
    + K.obj(K.circ(11, 34, 3), C.gray, { shift: .4 }) + K.obj(K.circ(34, 34, 3), C.gray, { shift: .4 }) + K.motion([[1, 20, 3, 20], [0.6, 26, 3, 26]], .8)],
  study: ['공부·시험', K => K.wash('M38 22 L20 41 L46 41Z', '#fbe7a1', .5)
    + K.obj(K.rr(5, 34, 21, 6.4, 1), C.blue) + K.obj(K.rr(7, 28, 19, 6, 1), C.rose)
    + K.obj(K.ell(33, 42, 7, 2), C.gray, { shift: .4 }) + K.line('M33 42 L27 28 L35 16', 1.8, C.gray)
    + K.obj('M31 11 L43 15 L39 24 Q33 21 31 11Z', C.yellow) + K.obj(K.circ(36.6, 13.4, 1.6), C.gray, { flat: true, w: .7 })],
  class: ['수업', K => K.obj(K.ell(24, 42.4, 9, 2.4), C.sepia, { shift: .5 }) + K.line('M24 35 V40.6', 1.8, C.sepia)
    + K.obj(K.circ(24, 21.4, 13), C.sky)
    + K.obj('M15 14 Q19 11 22 15 Q20 20 16 19 Q13 18 15 14Z', C.leaf, { flat: true, w: .7 }) + K.obj('M26 22 Q31 19 34 24 Q32 30 27 28 Q24 26 26 22Z', C.leaf, { flat: true, w: .7 }) + K.obj('M17 27 Q20 26 21 29 Q19 32 17 30Z', C.leaf, { flat: true, w: .7 })
    + K.detail('M11 21.4 H37 M24 8.4 Q17 21.4 24 34.4 M24 8.4 Q31 21.4 24 34.4', .6, '#4f86b5')
    + K.line('M34 10.6 A14.6 14.6 0 0 1 13 33.4', 1.8, C.sepia) + K.sparkle(42, 8, 2.4, C.yellow)],
  clean: ['청소', K => K.line('M20 30 Q24 6 32 12 Q36 16 40 38', 2, C.gray)
    + K.obj(K.rr(34, 38, 12, 4.4, 2), C.gray, { shift: .4 })
    + K.obj(K.ell(14, 33, 10, 8), C.rose) + K.obj(K.circ(12, 40, 3), C.gray, { shift: .4 }) + K.hi('M8 29 Q10 26 14 25.6', 1.2)
    + K.sparkle(43, 8, 2.4, C.yellow) + K.sparkle(37, 30, 1.8, C.yellow)],
  laundry: ['빨래', K => K.obj(K.rr(14, 8, 20, 6, 2), C.leaf) + K.obj(K.rr(12, 13, 24, 6, 2), C.yellow) + K.obj(K.rr(10, 18, 28, 6, 2), C.pink)
    + K.obj('M7 24 H41 L38 43 H10Z', '#e3eef6')
    + [[13, 29], [19, 29], [25, 29], [31, 29], [15, 35], [21, 35], [27, 35], [33, 35]].map(([x, y]) => K.wash(K.ell(x + 1.4, y, 1.8, 1.2), C.gray, .6)).join('')
    + K.wash(K.circ(41, 9, 2.6), '#d8ecf8', .9) + K.wash(K.circ(44, 15, 1.6), '#d8ecf8', .9)],
  grocery: ['장보기', K => K.obj(K.rr(13, 14, 7, 10, 1), C.paper) + K.obj('M13 14 L16.5 10.4 L20 14Z', C.sky, { flat: true, w: .7 })
    + K.obj(K.ell(28, 16, 6.4, 4), '#d9a66b') + K.obj('M33 18 Q34 8 38 6 Q37 13 35 18Z', C.leaf, { flat: true, w: .7 })
    + K.line('M14 22 Q14 10 20 12 M34 22 Q34 10 28 12', 1.8, '#c95f58')
    + K.obj('M9 22 H39 L36 40 H12Z', C.rose)
    + [[13, 26], [19, 26], [25, 26], [31, 26], [14, 32], [20, 32], [26, 32]].map(([x, y]) => K.obj(K.rr(x, y, 4, 3.4, .8), '#f9d3cf', { flat: true, noline: true })).join('')],
  parcel: ['택배', K => K.wash('M4 44 Q14 38 24 42 Q34 39 44 44Z', C.leaf, .7)
    + K.obj(K.rr(22, 28, 4, 16, 1), C.sepia, { shift: .5 })
    + K.obj(K.rr(25, 10, 12, 6, 1), '#f7f2e8', { shift: .4, w: .8 })
    + K.obj('M10 14 Q10 6 20 6 H30 Q38 6 38 14 V28 H10Z', C.rose)
    + K.detail('M10 16 H38', .8) + K.line('M38 12 H42 V6 H46 V10 H42', 1.2, C.yellow)
    + K.obj('M14 20 H24 V26 H14Z', C.paper, { flat: true, w: .8 }) + K.detail('M14 20 L19 23.6 L24 20', .7)],
  bank: ['은행·공과금', K => K.obj('M12 14 H36 V40 Q36 44 32 44 H16 Q12 44 12 40Z', '#e3eef6', { alpha: .6 })
    + [[24, 41, 9], [24, 37.6, 8.6], [22.6, 34.2, 8], [25.4, 30.8, 7.4]].map(([x, y, r]) => K.obj(K.ell(x, y, r, 2.2), C.yellow, { shift: .4, w: .8 })).join('')
    + K.obj(K.rr(11, 9, 26, 5, 1.6), C.sepia, { shift: .5 }) + K.detail('M20 11.4 H28', 1.4)
    + K.obj(K.circ(24, 4.6, 3.2), C.yellow, { shift: .4, w: .9 }) + K.hi('M15 18 V36', 1.2)],
  travel: ['여행', K => K.wash('M2 2 H46 V24 H2Z', '#f7c59f', .55) + K.wash('M2 2 H46 V12 H2Z', '#f2a7b5', .4)
    + K.wash('M23 24 A7 7 0 0 1 37 24Z', C.yellow, .9)
    + K.obj('M2 24 H46 V35 H2Z', C.blue, { noline: true, alpha: .6 }) + K.detail('M26 27 H34 M28 30 H33', .8, '#fbe7a1')
    + K.wash('M2 33 Q24 30 46 34 V46 H2Z', C.sand, .8)
    + K.line('M10 44 Q12 30 8 18', 2.4, C.sepia)
    + K.obj('M8 18 Q14 12 20 16 Q14 15 8 18Z', C.leaf, { w: .8 }) + K.obj('M8 18 Q2 12 -1 17 Q4 15 8 18Z', C.leaf, { w: .8 }) + K.obj('M8 18 Q10 10 16 9 Q11 12 8 18Z', C.green, { w: .8 }) + K.obj('M8 18 Q5 10 1 10 Q6 13 8 18Z', C.green, { w: .8 })
    + K.detail('M33 10 q2 -2 4 0 q2 -2 4 0', .9)],
  movie: ['영화·공연', K => K.wash('M24 10 L13 44 H35Z', '#fbe7a1', .6)
    + K.obj('M3 4 H19 Q15 22 19 44 H3Z', C.rose) + K.obj('M45 4 H29 Q33 22 29 44 H45Z', C.rose)
    + K.detail('M8 10 Q7 26 9 44 M13 10 Q11.6 26 14 44 M40 10 Q41 26 39 44 M35 10 Q36.4 26 34 44', .7, '#b5475a')
    + K.obj('M3 3 H45 V9 Q40 12.4 35 9 Q29.6 12.4 24 9 Q18.4 12.4 13 9 Q8 12.4 3 9Z', '#d9606b')
    + K.sparkle(24, 30, 4, C.yellow)],
  read: ['독서', K => K.line(K.rr(5, 6, 38, 38, 1.6), 1.8, C.sepia) + K.line('M5 20 H43 M5 32 H43', 1.8, C.sepia)
    + [[8, 9.6, 3.4, C.blue], [11.8, 11, 3, C.rose], [15.2, 10, 3.6, C.yellow], [19.2, 12, 3, C.green]].map(([x, y, w, c]) => K.obj(K.rr(x, y, w, 20 - y, .6), c, { shift: .4, w: .8 })).join('')
    + K.obj(K.rr(32, 14, 8, 6, 1.2), C.orange, { shift: .4, w: .9 }) + K.obj('M36 14 Q31 6 34 4 Q37 8 36 14Z M36 14 Q41 6 43 8 Q40 12 36 14Z', C.leaf, { flat: true, w: .7 })
    + [[8, 22.4, 3.2, C.violet], [11.6, 23.6, 3.2, C.sky], [15.2, 22, 3.6, C.pink]].map(([x, y, w, c]) => K.obj(K.rr(x, y, w, 32 - y, .6), c, { shift: .4, w: .8 })).join('')
    + K.g('rotate(-14 33 26)', K.obj(K.rr(28, 22.4, 3.2, 9.6, .6), C.leaf, { shift: .4, w: .8 }))
    + K.obj(K.rr(26, 36, 13, 8, 1), C.sand, { shift: .4, w: .8 })],
  pet: ['반려동물', K => K.obj('M10 16 Q4 26 10 36 Q16 44 24 44 Q32 44 38 36 Q44 26 38 16Z', '#e3eef6', { alpha: .45 })
    + K.wash('M8.2 22 Q24 18 39.8 22 Q42 30 37 36 Q32 43 24 43 Q16 43 11 36 Q6 30 8.2 22Z', C.sky, .65)
    + K.obj(K.ell(24, 16, 14, 3), C.paper, { flat: true, w: .9 })
    + K.obj('M28 30 L34 25 L34 35Z', C.orange, { shift: .4 }) + K.obj(K.ell(21.6, 30, 7, 4.6), C.orange) + K.dot(17.6, 29, .9)
    + K.detail('M12 40 Q14 34 13 30 M14 40 Q17 35 18 32', .9, C.leaf)
    + K.wash(K.circ(30, 20, 1.4), '#ffffff', .9) + K.wash(K.circ(33, 15, 1), '#ffffff', .9) + K.dot(20, 41, 1, C.rose) + K.dot(27, 41.4, 1, C.yellow) + K.dot(31, 40.4, 1, C.violet)],
  anniversary: ['기념일·결혼식', K => K.obj(K.ell(24, 43, 18, 2.6), '#e3eef6', { shift: .4 })
    + K.obj(K.rr(9, 32, 30, 11, 2), C.paper) + K.obj(K.rr(13, 22, 22, 10, 2), C.paper) + K.obj(K.rr(17, 13, 14, 9, 2), C.paper)
    + K.detail('M9 35 q2.5 2 5 0 t5 0 t5 0 t5 0 t5 0 t5 0 M13 25 q2.75 2 5.5 0 t5.5 0 t5.5 0 t5.5 0', .8, C.sky)
    + [[13, 38], [24, 38.6], [35, 38], [17, 28], [31, 28], [24, 18]].map(([x, y]) => K.wash(K.circ(x, y, 1.8), C.pink, .9)).join('')
    + K.heart(21, 8, 2.6, C.rose) + K.heart(27, 8.4, 2.4, C.pink)],
  rest: ['휴식·잠', K => K.wash('M2 40 Q24 36 46 40 V46 H2Z', C.leaf, .6)
    + K.obj(K.rr(5, 10, 4, 34, 2), C.sepia) + K.obj(K.rr(39, 10, 4, 34, 2), C.sepia)
    + K.obj('M1 12 Q2 4 9 4 Q15 5 14 12 Q9 15 1 12Z', C.green, { w: .8 }) + K.obj('M34 12 Q34 4 41 4 Q48 5 47 12 Q40 15 34 12Z', C.green, { w: .8 })
    + K.line('M9 18 L13 22 M39 18 L35 22', 1, '#5a4a42')
    + K.obj('M13 22 Q24 40 35 22 Q24 32 13 22Z', C.rose) + K.detail('M18 27.4 Q24 33 30 27.4', .8, C.yellow)
    + K.wash('M27 4 Q21.6 6 22 11 Q22.6 15 28 15.6 Q24.6 13 24.8 9.6 Q25 6 27 4Z', C.yellow, .9) + K.sparkle(32, 8, 1.6, C.yellow) + K.sparkle(17, 6, 1.4, C.yellow)],
};

function build(prefix = 'wc_') {
  const out = {};
  let i = 0;
  for (const [key, [name, fn]] of Object.entries(ART)) {
    const K = kit({ ...STYLE, uid: prefix + key, seed: 3 + (i++ % 7) });
    out[prefix + key] = { name, svg: K.wrap(fn(K)) };
  }
  return out;
}

module.exports = { build, STYLE, PALETTE: C, ORDER: Object.keys(ART) };
