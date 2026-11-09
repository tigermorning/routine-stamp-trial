// 색연필 팩(docs/sticker-style-guide.md 5절): 빗금 채색, 오른쪽 아래 교차 빗금 그림자, 물건 색의 진한 색으로 두 번 그은 윤곽선, 종이 결.
// 펜 팩과 같은 일정 30개 주제를 «다른 구성»으로 새로 그린다(예: 병원 = 청진기·반창고, 치과 = 칫솔·치약).
const { kit } = require('../parts');

const C = {
  coral: '#f08a7e', ochre: '#f2bf5e', sage: '#94c47d', sky: '#79b8dc', lilac: '#b99ad6', rose: '#f3a3bb', tan: '#d8a274', slate: '#8fa3b8',
  paper: '#dfe5ec', skin: '#f7cfae', navy: '#6f86b8', mint: '#9fdcc4', coffee: '#b9825a',
};
const STYLE = { material: 'pencil', line: '#6e6070', w: 1.6, wd: 1.05, shadeShift: 2.2 };

const ART = {
  hospital: ['병원', K => K.g('rotate(-30 13 37)', K.obj(K.rr(3, 33, 21, 8.4, 4.2), '#f6d2a8') + K.obj(K.rr(10, 33.6, 7, 7.2, 1.4), '#fbe6cf', { shift: .6 }) + K.dot(12, 35.6, .5, '#c9a27a') + K.dot(15, 35.6, .5, '#c9a27a') + K.dot(12, 38.6, .5, '#c9a27a') + K.dot(15, 38.6, .5, '#c9a27a'))
    + K.line('M12 6 Q11 16 17 21 Q23 16 22 6', 2.4, C.slate) + K.line('M17 21 V25 Q17 33 25 35 Q29 36 30 33', 2.4, C.slate)
    + K.obj(K.circ(12, 5.4, 1.8), C.navy, { flat: true }) + K.obj(K.circ(22, 5.4, 1.8), C.navy, { flat: true })
    + K.obj(K.circ(34, 33, 6.6), C.slate) + K.obj(K.circ(34, 33, 3.4), C.paper, { shift: .6 }) + K.heart(40, 12, 3, C.coral)],
  dentist: ['치과', K => K.g('rotate(-38 24 24)', K.obj(K.rr(2, 22, 30, 5.6, 2.8), C.sky) + K.obj(K.rr(8, 23.2, 8, 3.2, 1.6), '#bfe0f2', { flat: true, noline: true })
      + K.obj(K.rr(31, 21.4, 13, 6.8, 2), C.sky, { shift: .6 })
      + K.obj(K.rr(31.6, 13.6, 11.8, 7.8, 1.2), '#ffffff', { shift: .6 }) + K.detail('M34 14.4 V20.6 M36.6 14.4 V20.6 M39.2 14.4 V20.6 M41.6 14.4 V20.6', .7, C.slate)
      + K.obj('M31.4 14 Q32.4 9.4 35.6 11.6 Q37.6 8.6 40 11.4 Q42.6 9.4 43.6 14Z', C.mint, { shift: .5 }))
    + K.obj('M8.6 31 C6.6 31 5.6 33 6 35.4 C6.4 37.6 7.4 38.6 7.8 41.4 C8.2 44 8.8 45.4 10 45.4 C11.4 45.4 11.2 41.8 12.6 41.8 C14 41.8 13.8 45.4 15.2 45.4 C16.4 45.4 17 44 17.4 41.4 C17.8 38.6 18.8 37.6 19.2 35.4 C19.6 33 18.6 31 16.6 31 C14.8 31 14 32 12.6 32 C11.2 32 10.4 31 8.6 31Z', '#fffaf0', { shift: .8 })
    + K.dot(10.6, 36.2, .8) + K.dot(14.6, 36.2, .8) + K.detail('M11.4 38.6 Q12.6 39.8 13.8 38.6', .8)
    + K.sparkle(23, 40, 2.6, C.ochre) + K.sparkle(9, 9, 2.4, C.ochre)],
  pill: ['약 먹기', K => K.obj(K.rr(14, 13, 16, 29, 3), C.ochre) + K.obj(K.rr(12.6, 6, 18.8, 7.6, 2), C.paper)
    + K.detail('M15 8 V11.6 M18 8 V11.6 M21 8 V11.6 M24 8 V11.6 M27 8 V11.6 M29.6 8 V11.6', .7, C.slate)
    + K.obj(K.rr(16.4, 20, 11.2, 13, 1.4), '#fffaf0', { shift: .6 }) + K.line('M22 23.4 V29.6 M18.9 26.5 H25.1', 1.6, C.coral)
    + K.g('rotate(28 37 37)', K.obj('M32 37 V33 A3.6 3.6 0 0 1 39.2 33 V37Z', C.coral, { shift: .5 }) + K.obj('M32 37 V41 A3.6 3.6 0 0 0 39.2 41 V37Z', '#fffaf0', { shift: .5 }))
    + K.obj(K.circ(40, 26, 3.4), C.rose, { shift: .6 }) + K.detail('M37.8 26 H42.2', .7)],
  gym: ['헬스', K => K.obj('M15 22 Q13.6 8.6 24 8.6 Q34.4 8.6 33 22 H28.6 Q29.4 13 24 13 Q18.6 13 19.4 22Z', '#76879b')
    + K.obj(K.circ(24, 30.6, 12.4), C.slate) + K.obj(K.rr(19, 27, 10, 6.6, 1.6), C.ochre, { shift: .6 })
    + K.drop(40, 10, 2.4, C.sky) + K.drop(44, 17, 1.8, C.sky) + K.obj(K.ell(24, 44.4, 12, 1.6), C.paper, { flat: true, noline: true })],
  run: ['러닝', K => K.line('M24.6 17 L18.6 21 L14.6 18.4', 3, C.skin) + K.line('M21.6 30 L17.6 37.4 L11.6 39.6', 3.2, C.skin)
    + K.obj('M23.6 14.6 L30 15.6 L27.6 27.4 L20.6 26.4Z', C.sky)
    + K.obj('M20.6 26 L27.8 27 L27.4 31.4 L19.8 30.4Z', C.navy, { shift: .6 })
    + K.line('M29 17.6 L33.6 22.6 L37.8 20.2', 3, C.skin) + K.line('M26 30.6 L31.4 36 L37 34.4', 3.2, C.skin)
    + K.obj(K.ell(10.4, 40.4, 3.4, 2), C.coral, { shift: .4 }) + K.obj(K.ell(38.4, 34, 3.4, 2), C.coral, { shift: .4 })
    + K.obj(K.circ(28.4, 9.4, 4.8), C.skin) + K.line('M23.8 8 Q28.4 5.4 33 8', 1.8, C.coral) + K.dot(30.4, 9.8, .8)
    + K.motion([[3, 22, 9, 22], [5, 27, 11, 27], [2, 32, 7, 32]], 1.1)],
  yoga: ['요가', K => K.obj(K.rr(4, 38.4, 40, 4.4, 2.2), C.sage)
    + K.obj(K.ell(24, 35, 15, 5.4), C.navy) + K.obj(K.ell(15.6, 34.6, 3, 1.8), C.skin, { shift: .4 }) + K.obj(K.ell(32.4, 34.6, 3, 1.8), C.skin, { shift: .4 })
    + K.obj('M17 19.6 Q24 16 31 19.6 L32.4 31.6 H15.6Z', C.lilac)
    + K.line('M17.6 20.6 Q12.4 26 14 32.4', 3, C.skin) + K.line('M30.4 20.6 Q35.6 26 34 32.4', 3, C.skin)
    + K.obj(K.circ(24, 4.6, 2.6), '#9c6b4a', { shift: .4 }) + K.obj(K.circ(24, 11, 5.4), C.skin) + K.face(24, 11, .62, 'sleep')
    + K.sparkle(8, 12, 2.6, C.ochre) + K.sparkle(41, 16, 2, C.ochre)],
  swim: ['수영', K => K.obj('M2 30 Q7 26.6 12 30 T22 30 T32 30 T42 30 T47 30 V46 H2Z', C.sky)
    + K.detail('M6 35 q3 -2.4 6 0 M24 38 q3 -2.4 6 0 M34 33.4 q3 -2.4 6 0', .9, '#3f84ad')
    + K.line('M9 19.6 Q3.6 20.6 3 26', 2.4, C.coral) + K.line('M39 19.6 Q44.4 20.6 45 26', 2.4, C.coral)
    + K.obj(K.ell(16, 19.6, 7.4, 5.8), '#bfe0f2') + K.obj(K.ell(32, 19.6, 7.4, 5.8), '#bfe0f2') + K.line('M23 19 Q24 17.4 25 19', 2, C.coral)
    + K.hi('M11.6 17.6 Q13 15.6 15.4 15.4', 1.3) + K.hi('M27.6 17.6 Q29 15.6 31.4 15.4', 1.3)
    + K.obj(K.circ(40, 8, 2.4), '#e6f4fb', { flat: true }) + K.obj(K.circ(35.4, 4, 1.5), '#e6f4fb', { flat: true })],
  skin: ['피부관리', K => K.obj(K.circ(24, 28, 13), C.skin)
    + K.obj('M10.4 25 Q9.6 8.6 24 8.6 Q38.4 8.6 37.6 25 Q31 18.6 24 19.6 Q17 18.6 10.4 25Z', C.rose)
    + K.obj(K.ell(24, 7.4, 5.4, 3.4), C.rose, { shift: .6 })
    + K.obj(K.circ(18.6, 27.4, 4.2), C.sage, { shift: .6 }) + K.obj(K.circ(18.6, 27.4, 2.6), '#d6eec8', { flat: true, noline: true })
    + K.obj(K.circ(29.4, 27.4, 4.2), C.sage, { shift: .6 }) + K.obj(K.circ(29.4, 27.4, 2.6), '#d6eec8', { flat: true, noline: true })
    + K.dot(18, 26.6, .5, '#6f9a58') + K.dot(19.4, 28, .5, '#6f9a58') + K.dot(28.8, 26.6, .5, '#6f9a58') + K.dot(30.2, 28, .5, '#6f9a58')
    + K.detail('M21.4 35 Q24 37 26.6 35', 1.1) + K.blush(14, 33, 2.2) + K.blush(34, 33, 2.2) + K.sparkle(42, 13, 3, C.ochre)],
  nail: ['네일', K => K.g('rotate(-38 14 33)', K.obj(K.rr(9, 23, 5.6, 15, 2.8), C.skin) + K.obj(K.rr(9.8, 23.6, 4, 4.6, 2), C.coral, { shift: .3, w: 1 }))
    + K.obj('M13 44 V31 Q13 27 17 27 H31 Q35 27 35 31 V40 Q35 44 31 44Z', C.skin)
    + [[14, 10, 21], [20, 6.4, 24], [26, 8.4, 22], [31.4, 13.4, 17]].map(([x, y, h]) => K.obj(K.rr(x, y, 5.4, h, 2.7), C.skin, { shift: 1 }) + K.obj(K.rr(x + .8, y + .8, 3.8, 4.8, 1.9), C.coral, { shift: .3, w: 1 })).join('')
    + K.hi('M15.6 12 V13.6', 1) + K.hi('M21.6 8.4 V10', 1) + K.hi('M27.6 10.4 V12', 1) + K.sparkle(41.6, 8, 3, C.ochre) + K.sparkle(7, 14, 2, C.ochre)],
  salon: ['미용실', K => K.obj('M17 20 L14 37 Q14 40.4 17 40.4 H20 Q23 40.4 23 37 L25.6 20Z', C.rose)
    + K.obj('M8 14 Q8 7 15 7 H30 Q36.4 7 36.4 14 Q36.4 21 30 21 H15 Q8 21 8 14Z', C.rose)
    + K.obj(K.circ(13.4, 14, 4.2), '#f9d0dc', { shift: .5 }) + K.detail('M11.4 12 L15.4 16 M15.4 12 L11.4 16', .8, '#b46a82')
    + K.obj(K.rr(36.4, 9.6, 6.6, 8.8, 1.6), C.slate, { shift: .5 })
    + K.line('M18.6 40.4 q-3 3.4 0 5 q3 1.4 1 3', 1.3, C.slate)
    + K.detail('M44.4 10 q2 2 0 4 M44.4 15.4 q2 2 0 4', 1, C.sky) + K.hi('M14 9.6 H27', 1.2)],
  meal: ['식사 약속', K => K.line('M30.4 4 L22.6 22', 2.4, C.tan) + K.line('M34.6 5 L25.6 22.4', 2.4, C.tan)
    + K.obj('M6 24 H42 Q41 37 30 40.4 H18 Q7 37 6 24Z', C.coral)
    + K.obj(K.ell(24, 24, 18, 4.2), C.ochre, { shift: .6 })
    + K.detail('M22.4 10.6 q-1.6 3 0 6 q1.6 3 0 6.6 M25 11.4 q-1.4 3 0 6 q1.4 3 0 5.4', 1.2, '#d79a32')
    + K.obj(K.ell(13.6, 23.6, 4.2, 2.4), '#fffaf0', { shift: .4 }) + K.obj(K.circ(13.6, 23.6, 1.5), C.ochre, { flat: true, noline: true })
    + K.dot(31, 23, .9, '#6f9a58') + K.dot(34, 24.4, .9, '#6f9a58') + K.dot(29, 25, .9, '#6f9a58')
    + K.detail('M10 31 H38', .8, '#fbe0da') + K.steam(15, 15, 7) + K.steam(37, 16, 7)],
  cafe: ['카페', K => K.obj('M13 14 H35 L32 43 H16Z', '#e9f1f6')
    + K.obj('M13.9 22 H34.1 L32 43 H16Z', C.coffee, { noline: true }) + K.detail('M15 27 Q24 30 33.4 26.4', 2.2, '#f1dcc4')
    + K.obj(K.rr(16, 15.6, 6, 6, 1.4), '#d9eef8', { shift: .4, w: 1 }) + K.obj(K.rr(24, 16.6, 6, 6, 1.4), '#d9eef8', { shift: .4, w: 1 })
    + K.line('M13 14 H35 L32 43 H16Z', 1.35, '#7d98a8')
    + K.line('M27.4 9.4 L31.6 1.4', 3, C.sage) + K.obj('M11 14 Q11 8.6 16 8.6 H32 Q37 8.6 37 14Z', '#fffaf0')
    + K.drop(11.4, 30, 1.6, '#cfe8f5') + K.drop(37, 36, 1.4, '#cfe8f5') + K.sparkle(42, 8, 2.6, C.ochre)],
  drinks: ['술자리', K => K.obj('M15 6 H21 V12 Q26 15 26 21 V41 Q26 44 23 44 H13 Q10 44 10 41 V21 Q10 15 15 12Z', C.sage)
    + K.obj(K.rr(14.4, 3.4, 7.2, 3.6, 1), C.slate, { shift: .4 }) + K.obj(K.rr(11.6, 25.6, 12.8, 9.4, 1.4), '#fffaf0', { shift: .5 })
    + K.detail('M13.6 30.4 q1.6 -1.6 3.2 0 t3.2 0 t3.2 0', .9, C.sky) + K.hi('M12.6 22 V38', 1.3)
    + K.obj('M29 28.6 H42 L40.6 44 H30.4Z', '#eef5f8') + K.obj('M29.6 34 H41.4 L40.6 44 H30.4Z', '#d8f0e2', { noline: true }) + K.line('M29 28.6 H42 L40.6 44 H30.4Z', 1.35, '#7d98a8')
    + K.motion([[34, 21, 34, 25], [29.4, 22.4, 31, 25.6], [38.6, 22.4, 37, 25.6]], 1.1) + K.sparkle(42, 10, 2.6, C.ochre)],
  birthday: ['생일', K => K.line('M16 24 Q20 34 24 44 M30 22 Q27 33 24 44 M24 29.6 V44', 1, C.slate)
    + K.obj(K.ell(16, 15, 7.4, 9), C.coral) + K.obj(K.ell(31, 13, 7.4, 9), C.sky)
    + K.obj(K.ell(24, 21, 7, 8.6), C.ochre)
    + K.obj('M15 23.6 l1 1.6 h-2Z', C.coral, { flat: true }) + K.obj('M30 21.6 l1 1.6 h-2Z', C.sky, { flat: true }) + K.obj('M23 29.4 l1 1.6 h-2Z', C.ochre, { flat: true })
    + K.hi('M11.6 11 Q12.6 8.4 15 8', 1.3) + K.hi('M26.6 9 Q27.6 6.4 30 6', 1.3) + K.hi('M19.6 17 Q20.6 14.4 23 14', 1.3)
    + K.obj('M24 42 q-5 -3 -5.4 .6 q2 2.4 5.4 -.6 q3.4 3 5.4 .6 q-.4 -3.6 -5.4 -.6Z', C.rose, { shift: .3, w: 1 })],
  date: ['데이트', K => K.g('rotate(-14 16 30)', K.obj('M10.6 24 H22.4 L16.6 44.4Z', C.tan) + K.detail('M12.6 27 L19.6 34 M17.4 25 L20.6 28.6 M14 33 L17.4 37 M21 26 L14 33.6', .8, '#a8784e') + K.obj(K.circ(16.6, 19, 7), C.rose) + K.obj('M10 21 Q11 25 13 22 Q14 26 16 22.4 Q18 26.4 19.4 22.4 Q21 25 23.4 21Z', C.rose, { shift: .4, w: 1 }))
    + K.g('rotate(14 32 30)', K.obj('M25.6 24 H37.4 L31.6 44.4Z', C.tan) + K.detail('M27.6 27 L34.6 34 M32.4 25 L35.6 28.6 M29 33 L32.4 37 M36 26 L29 33.6', .8, '#a8784e') + K.obj(K.circ(31.6, 19, 7), C.mint) + K.dot(29.6, 17, .6, '#5f8f78') + K.dot(33, 20, .6, '#5f8f78'))
    + K.heart(24, 6, 3.4, C.coral) + K.hi('M12.4 15.6 Q13.6 13.4 16 13', 1.2) + K.hi('M27.4 15.6 Q28.6 13.4 31 13', 1.2)],
  meeting: ['회의', K => K.obj('M4 30.6 H44 L41 37 H7Z', '#c7d0da') + K.obj(K.rr(20, 32.4, 8, 2.4, 1), C.slate, { flat: true, noline: true })
    + K.obj(K.rr(9, 8, 30, 21.6, 2.4), C.slate) + K.obj(K.rr(11.6, 10.6, 24.8, 16, 1), '#e9f3f9', { shift: .5 })
    + K.obj(K.circ(19, 18.6, 4.6), C.coral, { shift: .4 }) + K.obj('M19 18.6 V14 A4.6 4.6 0 0 1 23.4 17.4Z', C.ochre, { flat: true, w: .9 })
    + K.obj(K.rr(26.6, 18, 2.6, 5.6, .6), C.sage, { flat: true, w: .8 }) + K.obj(K.rr(30, 15, 2.6, 8.6, .6), C.sage, { flat: true, w: .8 }) + K.obj(K.rr(33.4, 13, 2.6, 10.6, .6), C.sage, { flat: true, w: .8 })
    + K.sparkle(42.6, 7, 2.6, C.ochre)],
  trip: ['출장', K => K.g('rotate(14 32 28)', K.obj(K.rr(19, 16, 24, 15, 2), '#fffaf0') + K.obj(K.rr(19, 16, 24, 4.4, 1.6), C.coral, { shift: .4 }) + `<path d="M35 20.4 V31" stroke="#b9aab0" stroke-width=".9" stroke-dasharray="1.2 1.4"/>` + K.detail('M22 24 H31 M22 27.4 H28', .9, C.slate) + K.obj('M37 25 l3.4 -1 l-.6 1.6 l.6 1.6Z', C.slate, { flat: true, w: .8 }))
    + K.obj(K.rr(6, 9, 22, 31, 2.6), C.navy) + K.obj(K.circ(17, 21.4, 5.4), C.ochre, { shift: .5 })
    + K.detail('M11.6 21.4 H22.4 M17 16 Q13.6 21.4 17 26.8 M17 16 Q20.4 21.4 17 26.8', .8, '#b98a2c')
    + K.detail('M11 32.6 H23 M13 35.6 H21', 1, '#c9d3ee') + K.hi('M8.6 13 V24', 1.2)],
  study: ['공부·시험', K => K.obj(K.rr(10, 6, 26, 37, 2.6), '#fffaf0')
    + [10, 15.4, 20.8, 26.2, 31.6, 37].map(y => K.obj(K.circ(10, y, 1.5), C.slate, { flat: true, w: .8 })).join('')
    + [12.6, 20.6, 28.6].map((y, i) => K.obj(K.rr(14.6, y, 4.4, 4.4, .8), '#ffffff', { flat: true, w: .9 }) + (i < 2 ? K.line(`M15.2 ${y + 2.2} l1.6 1.6 l3.4 -4`, 1.4, C.coral) : '') + K.detail(`M21.6 ${y + 2.2} H32`, .9, C.slate)).join('')
    + K.g('rotate(-22 37 39)', K.obj(K.rr(30, 35.4, 14, 7, 2), C.rose) + K.obj(K.rr(30, 35.4, 6, 7, 1.4), C.sky, { shift: .4 }))
    + K.dot(26, 44.6, .6, '#c99aa6') + K.dot(29, 45.4, .5, '#c99aa6') + K.sparkle(41, 9, 2.6, C.ochre)],
  class: ['수업', K => K.line('M17 10 Q17 4 24 4 Q31 4 31 10', 2.2, '#b5605a')
    + K.obj('M11 17 Q11 8 24 8 Q37 8 37 17 V40 Q37 44 33 44 H15 Q11 44 11 40Z', C.coral)
    + K.obj(K.rr(15, 28, 18, 13, 3), '#f5aea5', { shift: .8 }) + K.obj('M15 31 Q15 27 19 27 H29 Q33 27 33 31 V32 H15Z', '#e27a6e', { shift: .5 })
    + K.obj(K.rr(22, 30.6, 4, 3.6, .8), C.ochre, { shift: .3, w: 1 })
    + K.g('rotate(16 33 10)', K.obj(K.rr(30.6, 3, 4, 13, .6), C.ochre, { shift: .4, w: 1 }) + K.obj('M30.6 3 L32.6 -.6 L34.6 3Z', C.skin, { flat: true, w: .9 }))
    + K.hi('M14 14 V24', 1.3) + K.detail('M24 12 V17', 1, '#b5605a')],
  clean: ['청소', K => K.line('M35 4 L23.4 27', 2.6, C.tan)
    + K.g('rotate(26 22 34)', K.obj(K.rr(15.4, 24.6, 13, 4, 1.2), C.coral, { shift: .4 }) + K.obj('M14.6 28.6 H29 L31 42 Q22 44 12.6 42Z', C.ochre) + K.detail('M17.4 31 L16.6 41.6 M21.8 31 V42.4 M26.4 31 L27.6 41.6', .9, '#c99434'))
    + K.obj('M28 33 H43 L45 44.4 H25.6Z', C.sage) + K.line('M43 33 L46 27', 2.4, C.sage)
    + K.dot(33, 41, .7, '#8a7a6a') + K.dot(36, 42.4, .6, '#8a7a6a') + K.dot(31, 43, .6, '#8a7a6a') + K.sparkle(9, 10, 2.8, C.ochre)],
  laundry: ['빨래', K => K.line('M2 10 Q24 16.4 46 10', 1.2, C.slate)
    + K.obj('M12 13.4 L17 11.6 Q20 14.6 23 11.6 L28 13.4 L31 19 L27.6 21 L26 18.4 V34 H14 V18.4 L12.4 21 L9 19Z', C.sky)
    + K.obj('M33 13 H38.4 V24 Q38.4 27 41.4 27 Q44.4 27 44.4 30 Q44.4 33.4 40.4 33.4 H36 Q33 33.4 33 30Z', C.coral)
    + K.detail('M33.2 17 H38.2 M33.2 20.4 H38.2', 1.2, '#fff4ee')
    + K.obj(K.rr(14.2, 9.6, 2.4, 5, .6), C.tan, { flat: true, w: .9 }) + K.obj(K.rr(24.6, 10.6, 2.4, 5, .6), C.tan, { flat: true, w: .9 }) + K.obj(K.rr(34.6, 11.4, 2.4, 5, .6), C.tan, { flat: true, w: .9 })
    + K.drop(17, 39, 1.6, C.sky) + K.drop(22.6, 42, 1.6, C.sky) + K.hi('M16 21 V30', 1.3)],
  grocery: ['장보기', K => K.obj(K.circ(20, 13, 4.6), C.coral, { shift: .6 }) + K.obj('M20 8.6 Q21.4 5.6 24 6.4 Q22.6 9 20 8.6Z', C.sage, { flat: true, w: .9 })
    + K.obj(K.rr(25.6, 5, 7.6, 10.4, 1), '#fffaf0', { shift: .5 }) + K.obj('M25.6 5 L29.4 1.6 L33.2 5Z', C.sky, { flat: true, w: .9 })
    + K.g('rotate(30 36 10)', K.obj('M34 4 L38 4 L36 17Z', '#f2a65a', { shift: .4, w: 1 }) + K.detail('M34.6 3.6 L33.4 1 M36 3.6 V.6 M37.4 3.6 L38.6 1', 1, '#6f9a58'))
    + K.obj('M10 14.6 H42 L38 30 H14Z', '#c7d0da') + K.detail('M12.6 19.6 H40.6 M13.6 24.6 H39.4 M18 14.6 L19 30 M24 14.6 V30 M30 14.6 L29 30 M36 14.6 L34.4 30', .8, C.slate)
    + K.line('M10 14.6 L7 8.6 H3 M14 30 L15 34.4 H38', 1.8, C.slate)
    + K.obj(K.circ(17, 39, 3), C.slate) + K.obj(K.circ(35, 39, 3), C.slate)],
  parcel: ['택배', K => K.obj(K.rr(8, 16, 32, 26, 2), C.tan) + K.obj('M8 16 L13 10 H35 L40 16Z', '#e8bf92', { shift: .6 })
    + K.line('M24 10 V42 M8 29 H40', 1.6, C.coral)
    + K.obj('M24 12 Q17.6 5.4 16 10.4 Q18 13.4 24 12 Q30 13.4 32 10.4 Q30.4 5.4 24 12Z', C.coral, { shift: .3, w: 1 })
    + K.line('M30 29 Q34 31 36 34', 1, C.slate) + K.g('rotate(-18 37 37)', K.obj(K.rr(33.6, 33.4, 8, 6.4, 1.2), '#fffaf0', { shift: .4, w: 1 }) + K.obj(K.circ(35.4, 36.6, .9), C.slate, { flat: true, noline: true }))
    + K.hi('M10.6 19.6 V36', 1.3) + K.sparkle(43, 8, 2.6, C.ochre)],
  bank: ['은행·공과금', K => K.g('rotate(-12 22 14)', K.obj(K.rr(12, 8, 20, 13, 2), C.sky) + K.obj(K.rr(12, 11, 20, 3, .4), C.navy, { flat: true, noline: true }) + K.obj(K.rr(15, 16.4, 5, 3, .6), C.ochre, { flat: true, w: .8 }))
    + K.obj(K.rr(5, 17, 32, 24, 4), '#c98c64') + K.obj('M5 21 Q5 17 9 17 H37 V27 H9 Q5 27 5 23Z', '#d9a27a', { shift: .6 }) + K.obj(K.rr(29, 22, 8, 7, 3.4), '#b07452', { shift: .4 }) + K.obj(K.circ(33, 25.4, 1.6), C.ochre, { flat: true, w: .8 })
    + [[39.6, 41.6], [39.6, 38.4], [39.6, 35.2]].map(([x, y]) => K.obj(K.ell(x, y, 5.4, 2.2), C.ochre, { shift: .3, w: 1 })).join('')
    + K.hi('M8 30 V37', 1.3) + K.sparkle(42, 8, 2.6, C.ochre)],
  travel: ['여행', K => K.obj('M5 12 L17 8 V36 L5 40Z', '#cfe6bd') + K.obj('M17 8 L31 12 V40 L17 36Z', '#f6dfa8') + K.obj('M31 12 L43 8 V36 L31 40Z', '#c9e2f1')
    + `<path d="M9 33 Q14 26 20 28 Q27 30 30 24 Q32 20 30 16" fill="none" stroke="${C.coral}" stroke-width="1.4" stroke-dasharray="2 1.8" stroke-linecap="round"/>`
    + K.detail('M33 28 q3 -2 6 0 M34 32 q2 -1.4 4 0', .8, '#5d9cc2') + K.detail('M8 20 q3 2 6 0', .8, '#6f9a58')
    + K.obj('M30 3.4 Q36.4 3.4 36.4 9.6 Q36.4 14.6 30 22 Q23.6 14.6 23.6 9.6 Q23.6 3.4 30 3.4Z', C.coral) + K.obj(K.circ(30, 9.6, 2.4), '#fffaf0', { flat: true, w: .9 })],
  movie: ['영화·공연', K => K.obj(K.rr(7, 21, 34, 21, 2.4), '#5e6675')
    + K.g('rotate(-14 8 19)', K.obj(K.rr(7, 13, 34, 6, 1.4), '#fffaf0') + `<path d="M11 13 l4 6 M19 13 l4 6 M27 13 l4 6 M35 13 l4 6" stroke="#5e6675" stroke-width="2.6"/>`)
    + K.obj(K.rr(7, 21, 34, 5, 1), '#fffaf0', { shift: .4 }) + `<path d="M11 21 l4 5 M19 21 l4 5 M27 21 l4 5 M35 21 l4 5" stroke="#5e6675" stroke-width="2.6"/>`
    + K.detail('M12 31 H26 M12 35.6 H22', 1.2, '#e9edf2') + K.obj(K.circ(34, 34, 3.4), C.coral, { shift: .4, w: 1 }) + K.sparkle(42, 8, 3, C.ochre)],
  read: ['독서', K => K.obj('M5 13 Q15 9.4 24 14.4 V39 Q15 34 5 37Z', '#fffaf0') + K.obj('M43 13 Q33 9.4 24 14.4 V39 Q33 34 43 37Z', '#fffaf0')
    + K.line('M4 15 V39 Q14 35.6 24 40.4 Q34 35.6 44 39 V15', 1.6, '#d77f95')
    + K.detail('M8.6 18 Q14 16.6 20 18.4 M8.6 22.6 Q14 21.2 20 23 M8.6 27.2 Q14 25.8 18 27.4', .8, C.slate)
    + K.obj('M27.4 13.6 V25 L29.4 23 L31.4 25 V12.6Z', C.coral, { shift: .3, w: 1 })
    + K.line('M41.6 35.6 Q46.4 35.6 45.6 39 Q45 41.6 41 41', 1.8, '#9eb0c2') + K.obj('M30 33 H42 Q42 44 36 44 Q30 44 30 33Z', '#eef3f7')
    + K.obj(K.ell(36, 33.4, 5.6, 1.4), C.ochre, { flat: true, w: .8 }) + K.steam(34, 30, 6) + K.steam(38, 30, 6)],
  pet: ['반려동물', K => K.line('M34.6 40.4 Q44.6 41 42.6 30.6', 3.4, '#e2a948')
    + K.obj('M14 44 Q10 30 18 24.4 Q24 21.4 30 24.4 Q38 30 34 44Z', C.ochre)
    + K.obj(K.ell(19.6, 43, 3, 2), '#fffaf0', { shift: .3, w: 1 }) + K.obj(K.ell(28.4, 43, 3, 2), '#fffaf0', { shift: .3, w: 1 })
    + K.obj('M14 18 Q14 9 18 5.6 L20.6 10.6 Q24 9.6 27.4 10.6 L30 5.6 Q34 9 34 18 Q34 26 24 26 Q14 26 14 18Z', C.ochre)
    + K.detail('M22 11.6 V14 M24 11.2 V14 M26 11.6 V14', 1, '#c98f2e')
    + K.dot(19.6, 18, 1.2) + K.dot(28.4, 18, 1.2) + K.obj('M23 20.6 H25 L24 21.8Z', C.rose, { flat: true, w: .8 })
    + K.detail('M15 20.6 L10 19.6 M15 22.4 L10 23 M33 20.6 L38 19.6 M33 22.4 L38 23', .7, C.slate)
    + K.line('M17 26.4 Q24 29.4 31 26.4', 2, C.coral) + K.obj(K.circ(24, 29.4, 1.8), C.ochre, { shift: .3, w: .9 })],
  anniversary: ['기념일·결혼식', K => K.obj('M13.6 25 L24 46 L34.4 25Z', '#cfe3f0')
    + K.obj('M15 20 L20 24 L16 26Z', C.sage, { flat: true, w: .9 }) + K.obj('M33 20 L28 24 L32 26Z', C.sage, { flat: true, w: .9 })
    + K.obj(K.circ(17, 17.6, 5.6), C.coral) + K.obj(K.circ(27.6, 14.4, 5.6), C.rose) + K.obj(K.circ(33, 22, 5), C.ochre) + K.obj(K.circ(21.4, 24.6, 4.6), C.lilac)
    + K.detail('M17 17.6 m-1.6 0 a1.6 1.6 0 1 0 1.6 -1.6 a3 3 0 1 1 -3 3', .8, '#b8564c') + K.detail('M27.6 14.4 m-1.6 0 a1.6 1.6 0 1 0 1.6 -1.6 a3 3 0 1 1 -3 3', .8, '#c46f87')
    + K.obj('M24 35 q-6.6 -4.6 -7 .6 q2.6 3 7 -.6 q4.4 3.6 7 .6 q-.4 -5.2 -7 -.6Z', C.rose, { shift: .3, w: 1 })
    + K.heart(41, 8, 3, C.coral) + K.sparkle(7, 8, 2.4, C.ochre)],
  rest: ['휴식·잠', K => K.obj(K.rr(4, 17, 6.4, 26, 2), C.tan) + K.obj(K.rr(8, 29, 36, 8, 2), '#fffaf0')
    + K.obj('M19 25 H40.6 Q44 25 44 29 V37 H19Z', C.lilac) + K.detail('M19 29.4 H44', 1, '#8f6fae')
    + K.obj(K.ell(15, 26.4, 6.2, 3.8), '#fffaf0') + K.line('M9 37 V42.6 M42 37 V42.6', 2, C.tan)
    + K.obj('M39.4 3.6 Q32.6 5 33 11 Q33.6 16.6 40.4 17 Q36.4 14 36.6 10.4 Q36.8 6 39.4 3.6Z', C.ochre, { shift: .4 })
    + K.line('M22 9 H26 L22 14 H26', 1.3) + K.line('M28 15.6 H30.6 L28 18.8 H30.6', 1.1)],
};

function build(prefix = 'cp_') {
  const out = {};
  for (const [key, [name, fn]] of Object.entries(ART)) {
    const K = kit({ ...STYLE, uid: prefix + key });
    out[prefix + key] = { name, svg: K.wrap(fn(K)) };
  }
  return out;
}

module.exports = { build, STYLE, PALETTE: C, ORDER: Object.keys(ART) };
