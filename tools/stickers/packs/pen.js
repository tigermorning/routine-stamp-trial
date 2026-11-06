// 펜 일러스트 팩(docs/sticker-style-guide.md 5절): 갈색 파인라이너 + 마커 채색, 자동 2톤 그림자, 흰 하이라이트, 보조 요소 1~2개.
const { kit } = require('../parts');

const C = {
  cream: '#fff4e2', apricot: '#ffb58a', pink: '#ff8fab', red: '#ef5b5b', yellow: '#ffd35c',
  green: '#9ad672', sky: '#7cc6f2', purple: '#b49cf0',
  // 중립색(재료 표현용): 흰색, 은색, 나무, 종이 상자, 칠판, 피부
  white: '#fffdf8', silver: '#dfe4ea', wood: '#d9a06a', kraft: '#e7c08f', board: '#4f8f6e', skin: '#ffe0c2', coffee: '#c98a5a',
};
const STYLE = { line: '#5b3a2e', w: 1.6, wd: 1.1, shadeShift: 1.7, shadeAmt: .2 };
// 작은 비행기(출장·여행이 함께 쓴다): 둥근 몸통, 위 날개, 꼬리 날개, 창문 점. 원점 기준 약 20x12.
const plane = (K, t) => K.g(t, K.obj('M3 4.6 L1 0 H4.4 L8 4.2Z', C.sky, { shift: .4, w: 1.2 })
  + K.obj('M9 7 L13.4 13 H16 L14.6 7Z', C.sky, { shift: .4, w: 1.2 })
  + K.obj('M1.6 6.6 Q1.6 4 4.4 4 H15 Q19.4 4 20.6 6.6 Q19.4 9.2 15 9.2 H4.4 Q1.6 9.2 1.6 6.6Z', C.white, { shift: .5, w: 1.2 })
  + K.dot(8, 6.4, .7) + K.dot(10.6, 6.4, .7) + K.dot(13.2, 6.4, .7) + K.obj('M17.4 5 Q19.6 5.4 20.4 6.6 H17.4Z', C.sky, { flat: true, noline: true }));

const ART = {
  hospital: ['병원', K => {
    const t = K.g('rotate(28 39 12)', K.obj(K.rr(37, 2, 4.4, 15, 2.2), C.white) + K.obj(K.circ(39.2, 17.6, 2.8), C.red) + K.line('M39.2 6 V15', 1.4, C.red));
    return K.obj('M17 17 V13 Q17 9 21 9 H27 Q31 9 31 13 V17 H28 V13.5 Q28 12 26.5 12 H21.5 Q20 12 20 13.5 V17Z', '#8a5a44')
      + K.obj(K.rr(6, 17, 36, 25, 4.5), C.red)
      + K.detail('M6 25.5 H42') + K.obj(K.rr(21, 23, 6, 5, 1.2), C.yellow, { shift: .8 })
      + K.obj(K.circ(24, 34.5, 6.2), C.cream, { shift: 1 })
      + `<path d="M22.4 30.6 h3.2 v2.3 h2.3 v3.2 h-2.3 v2.3 h-3.2 v-2.3 h-2.3 v-3.2 h2.3Z" fill="${C.red}"/>`
      + K.hi('M9.5 29 V37') + t + K.sparkle(7, 9, 2.6);
  }],
  dentist: ['치과', K => K.obj('M14 9 C9.5 9 7.5 13.5 8.6 18.6 C9.6 23.4 11.6 26 12.6 32 C13.6 38.4 15 42.5 18 42.5 C21.2 42.5 21 34.5 24 34.5 C27 34.5 26.8 42.5 30 42.5 C33 42.5 34.4 38.4 35.4 32 C36.4 26 38.4 23.4 39.4 18.6 C40.5 13.5 38.5 9 34 9 C30 9 28 11.4 24 11.4 C20 11.4 18 9 14 9Z', C.white)
    + K.face(24, 21.5, 1, 'smile') + K.hi('M12.2 15.4 Q13.6 12.2 17 12.2') + K.sparkle(41.5, 9, 3.4) + K.sparkle(6, 34, 2.2)],
  pill: ['약 먹기', K => K.obj('M27 17 H42 L40 42 H29Z', '#eaf6fd')
    + K.obj('M27.75 25 H41.25 L40 42 H29Z', C.sky, { noline: true }) + K.line('M27 17 H42 L40 42 H29Z') + K.detail('M27.7 25 H41.3')
    + K.hi('M30.2 19.5 L31.3 38') + K.g('rotate(35 16 26)', K.obj('M11 26 V19 A5 5 0 0 1 21 19 V26Z', C.pink) + K.obj('M11 26 V33 A5 5 0 0 0 21 33 V26Z', C.cream) + K.hi('M13.4 18.5 V24'))
    + K.obj(K.circ(9.6, 40.6, 4.2), C.white) + K.detail('M6.8 40.6 H12.4') + K.sparkle(37, 9, 2.8)],
  gym: ['헬스', K => K.g('rotate(-28 24 26)', K.obj(K.rr(16, 24, 16, 4.4, 1.4), C.silver)
      + K.obj(K.rr(5, 15, 6.4, 22, 2.6), C.red) + K.obj(K.rr(11.4, 18, 4.6, 16, 1.6), C.red)
      + K.obj(K.rr(32, 18, 4.6, 16, 1.6), C.red) + K.obj(K.rr(36.6, 15, 6.4, 22, 2.6), C.red)
      + K.hi('M7.4 18 V24') + K.hi('M39 18 V24'))
    + K.drop(39, 7, 2.2) + K.drop(44, 14, 1.8)],
  run: ['러닝', K => K.obj('M5 34 V22 Q5 17 10 17.4 L14.6 18 Q16.6 18.2 17.6 16 L20.4 11.2 Q22.4 9.8 24.2 11.6 L28 18 Q34.4 20 40 23.4 Q44.2 26.4 43.6 34Z', C.pink)
    + K.obj('M5 30 V22 Q5 17.6 9.4 17.4 L11.4 27.4Q8 30.6 5 30Z', C.red, { shift: .5, w: 1.3 })
    + K.obj('M35.6 34 Q35 27.4 39.6 25 Q43.8 27 43.6 34Z', C.cream, { shift: .5, w: 1.3 })
    + [0, 1, 2].map(i => { const d = `M${19.4 + i * 3.6} ${15.4 + i * 2} l4.4 3`; return K.line(d, 3.4) + K.line(d, 1.6, '#ffffff'); }).join('')
    + K.obj('M4.4 33 H44.4 V35.6 Q44.4 38.6 41.4 38.6 H7.4 Q4.4 38.6 4.4 35.6Z', C.white, { shift: .8 })
    + K.detail('M10 36 H14 M18 36 H22 M26 36 H30 M34 36 H38', 1)
    + K.obj(K.circ(22, 27.6, 3), C.yellow, { shift: .4, w: 1.2 })
    + K.hi('M14 21.4 Q15.6 21.2 16.6 20') + K.hi('M30.6 23.6 Q34.6 24.6 36.6 26')
    + K.motion([[0.6, 24, 3.4, 24], [0.4, 29, 2.8, 29]], 1.3) + K.sparkle(41, 13, 2.6)],
  yoga: ['요가', K => K.obj('M11 20 H37 Q41.4 20 41.4 27 Q41.4 34 37 34 H11Z', C.purple)
    + K.obj(K.ell(11, 27, 5, 7), K.lighten(C.purple, .35), { shift: .8 })
    + K.detail('M11 27 m-1.6 0 a1.6 1.6 0 1 0 1.6 -1.6 a3.2 3.2 0 1 1 -3.2 3.2')
    + K.obj(K.rr(22.5, 18.6, 5, 16.8, 1.2), C.yellow, { shift: .8 })
    + K.hi('M15 22.6 H21') + K.obj('M33 15 Q34.6 7 43 7.4 Q41.4 15.4 33 15Z', C.green) + K.detail('M34.6 13.4 Q37.6 10.4 41 9')
    + K.sparkle(7, 11, 2.4)],
  swim: ['수영', K => `<circle cx="24" cy="23" r="15" fill="${C.white}"/>`
    + `<circle cx="24" cy="23" r="10.5" fill="none" stroke="${C.red}" stroke-width="9" stroke-dasharray="8.25 8.25" transform="rotate(10 24 23)"/>`
    + `<path d="M24 8 a15 15 0 0 1 0 30" fill="none" stroke="#000" stroke-opacity=".12" stroke-width="5"/>`
    + K.obj(K.circ(24, 23, 6), C.sky, { shift: -1 }) + K.line(K.circ(24, 23, 15))
    + K.hi('M12.4 17 Q15 11.4 20.6 9.6')
    + K.obj('M2 34 Q7 31 12 34 T22 34 T32 34 T42 34 T47 34 V46 H2Z', C.sky) + K.hi('M6 36.4 Q8.6 35 11 36.4') + K.hi('M27 37.4 Q29.6 36 32 37.4')
    + K.sparkle(42, 8, 3)],
  skin: ['피부관리', K => K.obj('M13 6.5 Q13 3 16 3 Q19 3 19 6.5 V11 H13Z', C.pink)
    + K.obj(K.rr(11.6, 11, 8.8, 3.6, 1.2), C.yellow, { shift: .6 })
    + K.obj(K.rr(9.6, 14.4, 12.8, 29, 3.4), C.apricot) + K.obj(K.rr(12, 23, 8, 10, 1.4), C.cream, { shift: .6 })
    + K.hi('M12.2 17.6 V22') + K.obj(K.rr(25, 24.6, 18, 6.4, 2.2), C.pink) + K.obj(K.rr(26, 31, 16, 12, 2.8), C.cream)
    + K.detail('M26.4 35.4 H41.6') + K.hi('M28.4 27 H33') + K.sparkle(35, 14, 3.2) + K.sparkle(43, 19, 2)],
  nail: ['네일', K => K.obj(K.rr(18, 4, 12, 15, 2.6), '#7a4f3c') + K.hi('M20.6 6.6 V15.6')
    + K.obj(K.rr(20, 19, 8, 3.4, 1), C.cream, { shift: .5 })
    + K.obj('M12.6 26 Q12.6 22.4 16.2 22.4 H31.8 Q35.4 22.4 35.4 26 V38.6 Q35.4 43 31 43 H17 Q12.6 43 12.6 38.6Z', C.red)
    + K.hi('M16 27 V37') + K.detail('M16.4 39.6 H31.6', .9) + K.sparkle(40.6, 12, 3.2) + K.sparkle(7.4, 15, 2.2) + K.heart(41, 36, 2.4)],
  salon: ['미용실', K => K.obj('M16 18.6 L40.6 27 Q42.6 28.4 40.4 29.4 L15.4 22Z', C.silver)
    + K.obj('M15.4 30.6 L40.6 13 Q42.6 12.4 41.6 14.6 L17.4 33.6Z', C.silver)
    + K.obj(K.circ(11, 19, 4.8), C.red) + K.obj(K.circ(11, 19, 2.2), '#fff', { flat: true, noline: false, w: 1.1 })
    + K.obj(K.circ(12.4, 33, 4.8), C.red) + K.obj(K.circ(12.4, 33, 2.2), '#fff', { flat: true, w: 1.1 })
    + K.obj(K.circ(27, 23.3, 1.6), C.yellow, { shift: .3 })
    + K.g('rotate(-24 35 40)', K.obj(K.rr(24, 35, 22, 5, 1.8), C.purple) + K.detail('M26.6 40 V44.4 M29.4 40 V44.4 M32.2 40 V44.4 M35 40 V44.4 M37.8 40 V44.4 M40.6 40 V44.4 M43.4 40 V44.4', 1.2) + K.hi('M27 36.8 H33', 1.2))
    + K.sparkle(42, 6, 2.8)],
  meal: ['식사 약속', K => K.line('M30.4 3 L44 21.4', 3.8) + K.line('M30.4 3 L44 21.4', 1.8, C.wood)
    + K.line('M34.4 2 L46.4 18', 3.8) + K.line('M34.4 2 L46.4 18', 1.8, C.wood)
    + K.obj('M17.4 41 H30.6 L29.6 44.4 H18.4Z', C.white, { shift: .5 })
    + K.obj('M7 24 H41 Q41 37.6 30.4 41 H17.6 Q7 37.6 7 24Z', C.white)
    + K.obj('M9 24.4 Q11.4 14.4 24 14.4 Q36.6 14.4 39 24.4Z', C.cream, { shift: 1 })
    + K.detail('M9.4 30.4 H38.6', .9) + K.detail('M15 20 l1 .6 M21 17.6 l1 .4 M27.4 18.6 l1 -.4 M32 21 l1 .4', 1)
    + K.hi('M11 27.4 Q12.4 33 17 36') + K.steam(18, 12, 8) + K.steam(25, 11, 8)],
  cafe: ['카페', K => K.obj(K.ell(23, 38.4, 18.4, 5), C.cream)
    + K.line('M35.6 24.4 Q43.4 24.4 42.4 30 Q41.4 34.4 34.6 33.6', 4.2) + K.line('M35.6 24.4 Q43.4 24.4 42.4 30 Q41.4 34.4 34.6 33.6', 2, C.white)
    + K.obj('M8 21.6 H37.6 Q37.6 36.6 26.6 39 H19 Q8 36.6 8 21.6Z', C.white)
    + K.obj(K.ell(22.8, 21.8, 14.4, 4), C.coffee, { shift: .7 }) + K.heart(22.8, 21.6, 2.6, '#fff4e2')
    + K.hi('M11 25.6 Q12 32.6 17 35.6') + K.steam(17, 14, 8) + K.steam(25, 13, 8) + K.sparkle(42, 8, 2.6)],
  drinks: ['술자리', K => {
    const mug = (flip) => {
      const handle = flip ? 'M23 21.4 Q29.6 21.4 29.4 27 Q29.2 33 23 32.6' : 'M7 21.4 Q0.4 21.4 0.6 27 Q0.8 33 7 32.6';
      return K.line(handle, 4.2) + K.line(handle, 2, C.yellow)
        + K.obj(K.rr(7, 15, 16, 28, 3), C.yellow)
        + K.obj('M5.6 17.4 Q5.6 12 10 12.8 Q12 8.6 16 10.6 Q20.4 8.4 22.4 12.8 Q26 12.6 24.6 17.4 Q20 19.4 15 17.6 Q10 19.6 5.6 17.4Z', C.white, { shift: .8 })
        + `<circle cx="12" cy="27" r="1.2" fill="#fff" opacity=".9"/><circle cx="17" cy="33" r="1.4" fill="#fff" opacity=".9"/><circle cx="13.4" cy="37" r="1" fill="#fff" opacity=".9"/>`
        + K.hi('M10 21 V39');
    };
    return K.g('rotate(-14 15 29) translate(-1 0)', mug(false)) + K.g('rotate(14 33 29) translate(18 0)', mug(true))
      + K.motion([[24, 3, 24, 7.4], [18.6, 4.4, 20.6, 8.2], [29.4, 4.4, 27.4, 8.2]], 1.4);
  }],
  birthday: ['생일', K => K.obj(K.ell(24, 41.6, 19, 3.6), C.white, { shift: .6 })
    + K.obj(K.rr(8, 23, 32, 18, 3.2), C.pink)
    + K.obj('M8 27 Q8 22.6 12 22.6 H36 Q40 22.6 40 27 V28.6 Q38 32 36 28.6 Q34 33 31.4 28.6 Q29 33 26.6 28.6 Q24 33 21.4 28.6 Q19 33 16.6 28.6 Q14 33 12 28.6 Q10 32 8 28.6Z', C.white, { shift: .6 })
    + [[14.4, 20.4], [33.6, 20.4]].map(([x, y]) => K.obj(`M${x} ${y - 3.6} Q${x + 3.4} ${y - 3.4} ${x + 2.8} ${y} Q${x + 1.6} ${y + 2.8} ${x} ${y + 2.6} Q${x - 1.6} ${y + 2.8} ${x - 2.8} ${y} Q${x - 3.4} ${y - 3.4} ${x} ${y - 3.6}Z`, C.red, { shift: .5 }) + K.detail(`M${x - 1.2} ${y - 3.4} l1.2 -1.4 l1.2 1.4`, .9)).join('')
    + K.obj(K.rr(19.4, 11, 3.6, 11.6, 1), C.yellow, { shift: .5 }) + K.obj(K.rr(25, 11, 3.6, 11.6, 1), C.sky, { shift: .5 })
    + K.obj('M21.2 4 Q24 7.6 21.2 9.6 Q18.4 7.6 21.2 4Z', '#ffa24c', { shift: .4 }) + K.obj('M26.8 4 Q29.6 7.6 26.8 9.6 Q24 7.6 26.8 4Z', '#ffa24c', { shift: .4 })
    + K.hi('M11 33 V37.6') + K.sparkle(42, 10, 2.8) + K.sparkle(6, 12, 2.2)],
  date: ['데이트', K => K.line('M17 24 V13 L22.4 8.6', 3.6) + K.line('M17 24 V13 L22.4 8.6', 1.8, C.white)
    + K.line('M31 24 V13 L25.6 8.6', 3.6) + K.line('M31 24 V13 L25.6 8.6', 1.8, C.white)
    + K.obj('M9 19.6 H23 L21 42.6 H11Z', '#fde3ea') + K.obj('M9.6 26 H22.4 L21 42.6 H11Z', C.pink, { noline: true }) + K.line('M9 19.6 H23 L21 42.6 H11Z')
    + K.obj('M25 19.6 H39 L37 42.6 H27Z', '#fff3cf') + K.obj('M25.6 26 H38.4 L37 42.6 H27Z', C.yellow, { noline: true }) + K.line('M25 19.6 H39 L37 42.6 H27Z')
    + K.obj(K.rr(12.6, 28, 5, 5, 1), '#ffffff', { flat: true, w: 1 }) + K.obj(K.rr(29.6, 30, 5, 5, 1), '#ffffff', { flat: true, w: 1 })
    + K.hi('M11.6 22.6 L12.8 39') + K.hi('M27.6 22.6 L28.8 39') + K.heart(24, 4.6, 3.2, C.red)],
  meeting: ['회의', K => K.obj('M5 9.4 Q5 5 9.4 5 H29.6 Q34 5 34 9.4 V20.6 Q34 25 29.6 25 H15.6 L9.4 30.4 V25 Q5 25 5 20.6Z', C.sky)
    + K.detail('M10.4 11.6 H28.6 M10.4 17.4 H22', 1.4)
    + K.obj('M17 23.4 Q17 19 21.4 19 H38.6 Q43 19 43 23.4 V32.6 Q43 37 38.6 37 H36 V42.6 L30.6 37 H21.4 Q17 37 17 32.6Z', C.yellow)
    + K.dot(24.6, 28, 1.8) + K.dot(30, 28, 1.8) + K.dot(35.4, 28, 1.8) + K.hi('M8.4 21 V11') + K.hi('M20.4 33 V25') + K.sparkle(41.6, 9, 2.8)],
  trip: ['출장', K => K.obj('M17 18 V13.6 Q17 10.6 20 10.6 H28 Q31 10.6 31 13.6 V18 H28 V14.2 Q28 13.6 27.4 13.6 H20.6 Q20 13.6 20 14.2 V18Z', '#8a5a44')
    + K.obj(K.rr(5, 18, 38, 24, 4), C.wood) + K.detail('M5 27 H43')
    + K.obj(K.rr(11, 25, 5, 5, 1), C.yellow, { shift: .5 }) + K.obj(K.rr(32, 25, 5, 5, 1), C.yellow, { shift: .5 })
    + K.hi('M8.4 31 V38.4') + plane(K, 'translate(26 1) rotate(-14 10 6)')
    + `<path d="M25 11 Q16 8 9 12" fill="none" stroke="${STYLE.line}" stroke-width="1" stroke-dasharray="1.6 2" stroke-linecap="round"/>`],
  study: ['공부·시험', K => K.obj('M3 16 V41.6 Q14 37.6 24 41.6 Q34 37.6 45 41.6 V16 Q34 12.6 24 16 Q14 12.6 3 16Z', C.sky)
    + K.obj('M5 14.6 Q14.4 11 24 15.4 V39.6 Q14.4 35.6 5 38.6Z', C.white, { shift: .8 })
    + K.obj('M43 14.6 Q33.6 11 24 15.4 V39.6 Q33.6 35.6 43 38.6Z', C.white, { shift: .8 })
    + K.detail('M9 20 Q14 18.6 20 20.4 M9 25 Q14 23.6 20 25.4 M9 30 Q14 28.6 18 29.8', .9)
    + K.g('rotate(38 34 24)', K.obj(K.rr(31, 9, 6, 22, .8), C.yellow) + K.obj(K.rr(31, 5, 6, 4.4, 1.2), C.pink, { shift: .5 }) + K.obj('M31 31 L34 37.4 L37 31Z', C.cream, { shift: .4 }) + K.obj('M33 35.2 L34 37.4 L35 35.2Z', STYLE.line, { flat: true, noline: true }) + K.hi('M33 12 V27'))
    + K.dot(19, 44.6, .8) + K.dot(22, 45.6, .7) + K.sparkle(8, 8, 2.6)],
  class: ['수업', K => K.line('M10 32 L6 44 M38 32 L42 44', 2.4, '#8a5a44')
    + K.obj(K.rr(4, 5, 40, 28, 2.6), C.wood) + K.obj(K.rr(7, 8, 34, 22, 1.4), C.board, { shift: .8 })
    + K.line('M11.4 14 l4 -2.6 l4 2.6 M11.4 19.4 H22 M11.4 24 H17.6 M27 13 v8 M23 17 h8', 1.3, '#f6fbf4')
    + K.obj('M33.6 36.6 Q30 32.4 34.4 30.6 Q36.6 30 37.6 31.6 Q38.6 30 40.8 30.6 Q45.2 32.4 41.6 36.6 Q39.6 39.6 37.6 38.6 Q35.6 39.6 33.6 36.6Z', C.red)
    + K.obj('M37.6 30.6 Q39.6 26.4 42.6 27 Q41 30.4 37.6 30.6Z', C.green, { shift: .4 }) + K.hi('M34.4 33 Q34.8 31.6 36 31.4')],
  clean: ['청소', K => K.obj('M9.6 8 H22 Q25 8 25 11 V15.6 H9.6Z', C.sky) + K.obj('M5 9 H9.6 V12.6 H5Z', C.sky, { shift: .4 })
    + K.obj('M14.6 15.6 Q13 17.6 15 19.4 L22 19.6 L21 15.6Z', C.yellow, { shift: .4 })
    + K.obj('M10.6 19.6 H24.6 L26.6 40 Q26.6 43.4 23.4 43.4 H12.4 Q9 43.4 9 40Z', '#eaf6fd')
    + K.obj('M10.2 28 H25.4 L26.6 40 Q26.6 43.4 23.4 43.4 H12.4 Q9 43.4 9 40Z', C.sky, { noline: true }) + K.line('M10.6 19.6 H24.6 L26.6 40 Q26.6 43.4 23.4 43.4 H12.4 Q9 43.4 9 40Z')
    + K.hi('M12.4 22.6 V38') + K.dot(2.6, 8, .9) + K.dot(1.6, 12, .9) + K.dot(3.4, 15.6, .8)
    + K.obj(K.rr(28, 31.6, 15.6, 11.6, 3), C.yellow) + K.obj(K.rr(28, 28, 15.6, 4.6, 1.6), C.green, { shift: .5 })
    + K.obj(K.circ(33, 22.6, 3.2), '#ffffff', { flat: true, w: 1 }) + K.obj(K.circ(39.4, 19.6, 2.2), '#ffffff', { flat: true, w: 1 }) + K.obj(K.circ(41.6, 25, 1.6), '#ffffff', { flat: true, w: 1 })],
  laundry: ['빨래', K => K.obj(K.rr(8, 4, 32, 39, 4), C.white) + K.detail('M8 12.6 H40')
    + K.obj(K.circ(14, 8.4, 2), C.red, { shift: .3 }) + K.detail('M20 8.4 H24 M27 8.4 H31', 1.4)
    + K.obj(K.circ(24, 28.4, 10.4), C.silver) + K.obj(K.circ(24, 28.4, 7.6), C.sky, { shift: .9 })
    + K.obj('M19.4 27 Q21 23.6 24 25.6 Q27 27.6 29 25 L29.6 29 Q26.6 31.6 23.6 29.6 Q21 28 20 30.6Z', C.pink, { shift: .5, w: 1.1 })
    + K.hi('M18.6 23 Q20.6 20.6 23.6 20.6') + K.obj(K.rr(10, 43, 5, 2.6, .8), STYLE.line, { flat: true, noline: true }) + K.obj(K.rr(33, 43, 5, 2.6, .8), STYLE.line, { flat: true, noline: true })
    + K.obj(K.circ(42.6, 4.6, 2.6), '#ffffff', { flat: true, w: 1 }) + K.obj(K.circ(44.6, 10.4, 1.6), '#ffffff', { flat: true, w: 1 })],
  grocery: ['장보기', K => K.g('rotate(-22 15 14)', K.obj(K.rr(11, 2, 7.6, 24, 3.6), C.wood) + K.detail('M13 7 l3.4 1.4 M13 12.4 l3.4 1.4 M13 17.6 l3.4 1.4'))
    + K.obj('M27.6 22 Q26.4 10 30 3 Q31.6 11 30.6 22Z', C.green) + K.obj('M30.6 22 Q33 12 39 7.6 Q36.6 15 33.6 22Z', C.green)
    + K.obj('M6 21 H42 L38.4 43.4 H9.6Z', C.kraft)
    + K.line('M14 21 Q14 13.4 19 13.4 M34 21 Q34 13.4 29 13.4', 1.6)
    + K.detail('M7.4 27 H40.6') + K.obj('M20.4 33.4 Q17 29.6 21 28 Q23 27.6 24 29 Q25 27.6 27 28 Q31 29.6 27.6 33.4 Q25.8 36.4 24 35.4 Q22.2 36.4 20.4 33.4Z', C.red, { shift: .7, w: 1.3 })
    + K.hi('M10 30.6 L11.4 39')],
  parcel: ['택배', K => K.obj('M24 23 L41 15.6 V35.6 L24 43Z', '#d4a56c')
    + K.obj('M7 15.6 L24 23 V43 L7 35.6Z', C.kraft)
    + K.obj('M7 15.6 L24 8.4 L41 15.6 L24 23Z', '#f2d3a6', { shift: .6 })
    + K.obj('M14 12.4 L31.4 19.6 L34.4 18.2 L17 11Z', '#fff4e2', { shift: .4, w: 1.2 })
    + K.obj('M27.4 27 L36.6 23 V29.6 L27.4 33.6Z', C.white, { shift: .4, w: 1.2 }) + K.detail('M29.4 28.6 L34.4 26.4', .8)
    + K.hi('M10 20 V33') + K.sparkle(42, 6, 3) + K.sparkle(5, 8, 2)],
  bank: ['은행·공과금', K => K.obj('M9.6 39 V43.4 H14.4 V40.4Z', C.pink, { shift: .5 }) + K.obj('M29 40.6 V43.4 H33.6 V39Z', C.pink, { shift: .5 })
    + K.obj(K.ell(23, 29, 16.4, 12.4), C.pink)
    + K.obj('M12.4 19.4 L13 12 L19.6 17Z', C.pink, { shift: .5 })
    + K.obj(K.ell(38.6, 29.6, 4.2, 3.8), '#ffb3c6', { shift: .5 }) + K.dot(37.4, 29.6, .9) + K.dot(39.8, 29.6, .9)
    + K.dot(30.4, 25, 1.4) + K.blush(31.4, 30.6, 1.8)
    + K.line('M6.6 28 q-4 -1 -3 -4 q1 -2.4 3 -.6', 1.4)
    + K.obj(K.rr(19, 16.6, 8.4, 2.4, 1.2), STYLE.line, { flat: true, noline: true })
    + K.obj(K.circ(23.2, 8, 5), C.yellow) + K.obj(K.circ(23.2, 8, 3), C.yellow, { shift: .5, w: 1 })
    + K.hi('M11 24 Q13 20 18 18.6') + K.sparkle(41, 12, 2.6)],
  travel: ['여행', K => K.line('M18 14 V5.4 H30 V14', 3.6) + K.line('M18 14 V5.4 H30 V14', 1.6, C.silver)
    + K.obj(K.rr(10.6, 14, 26.8, 27, 4), C.sky)
    + K.detail('M18 17 V38 M30 17 V38', 1.2)
    + K.obj(K.circ(15.6, 43.4, 2.2), STYLE.line, { flat: true, noline: true }) + K.obj(K.circ(32.4, 43.4, 2.2), STYLE.line, { flat: true, noline: true })
    + K.obj(K.circ(24.6, 23, 3.6), C.yellow, { shift: .5, w: 1.2 }) + K.obj(K.rr(20, 30, 8, 5, 1.4), C.pink, { shift: .5, w: 1.2 })
    + K.hi('M13.6 18 V36') + plane(K, 'translate(26 0) rotate(-16 10 6)')],
  movie: ['영화·공연', K => K.g('rotate(-16 10 30)', K.obj('M2 24 H17 V28.4 Q15 28.4 15 30.4 Q15 32.4 17 32.4 V37 H2 V32.4 Q4 32.4 4 30.4 Q4 28.4 2 28.4Z', C.yellow, { w: 1.3 }) + `<path d="M9.4 24.6 V36.4" stroke="${STYLE.line}" stroke-width="1" stroke-dasharray="1.4 1.6"/>`)
    + [[17, 13, 4.4], [23, 10, 4.8], [29.6, 12.4, 4.4], [35, 15.6, 3.8], [20, 16, 4], [27, 16.6, 4.2]].map(([x, y, r]) => K.obj(K.circ(x, y, r), C.cream, { shift: .6, w: 1.3 })).join('')
    + K.obj('M13 18.4 H39 L35.6 43.4 H16.4Z', C.white)
    + `<clipPath id="pnpop"><path d="M13 18.4 H39 L35.6 43.4 H16.4Z"/></clipPath><g clip-path="url(#pnpop)"><path d="M17.6 18 L19.6 44 H23.6 L22.4 18Z M27.6 18 L27.6 44 H31.6 L32.4 18Z" fill="${C.red}"/></g>`
    + K.line('M13 18.4 H39 L35.6 43.4 H16.4Z') + K.detail('M13.6 23 H38.4', 1.2) + K.sparkle(43, 8, 2.8)],
  read: ['독서', K => K.obj(K.rr(5, 34, 35, 8.6, 1.6), C.sky) + K.obj(K.rr(36.4, 35.4, 3, 5.8, .6), C.cream, { flat: true, w: .9 })
    + K.obj(K.rr(9, 25.6, 31, 8.6, 1.6), C.pink) + K.obj(K.rr(36.4, 27, 3, 5.8, .6), C.cream, { flat: true, w: .9 })
    + K.obj(K.rr(6.6, 17.2, 32, 8.6, 1.6), C.yellow) + K.obj(K.rr(35, 18.6, 3, 5.8, .6), C.cream, { flat: true, w: .9 })
    + K.detail('M11 21.4 H20 M14 30 H22 M10 38.4 H19', 1)
    + K.obj(K.circ(16.6, 11.6, 4.6), '#eaf6fd', { shift: .5, w: 1.4 }) + K.obj(K.circ(28.6, 11.6, 4.6), '#eaf6fd', { shift: .5, w: 1.4 })
    + K.line('M21.2 11 Q22.6 9.6 24 11 M33.2 11.6 L38 9.4', 1.4) + K.hi('M14.6 9.6 Q15.6 8.4 17 8.4', 1.2) + K.hi('M26.6 9.6 Q27.6 8.4 29 8.4', 1.2) + K.sparkle(43, 26, 2.4)],
  pet: ['반려동물', K => K.obj(K.ell(24, 26, 14, 13), '#f4d3a8')
    + K.obj('M11.6 14.6 Q3.6 15.6 5.6 28.6 Q7.6 32 12.4 27.6Z', '#c98a5a') + K.obj('M36.4 14.6 Q44.4 15.6 42.4 28.6 Q40.4 32 35.6 27.6Z', '#c98a5a')
    + K.obj(K.ell(24, 31.4, 6.4, 4.8), C.white, { shift: .5 })
    + K.obj(K.ell(24, 28.6, 2.6, 1.8), STYLE.line, { flat: true, noline: true }) + K.detail('M24 30.4 V32.4 M21.4 32.6 Q24 34.6 26.6 32.6')
    + K.obj('M22.6 33.4 Q24 37.4 25.4 33.4Z', C.pink, { shift: .3, w: 1 })
    + K.dot(18.6, 23.6, 1.5) + K.dot(29.4, 23.6, 1.5) + K.blush(15.6, 28.4) + K.blush(32.4, 28.4)
    + K.obj('M13 36.6 Q24 42 35 36.6 L35.6 39.6 Q24 45 12.4 39.6Z', C.red, { shift: .5 }) + K.obj(K.circ(24, 42.6, 2.4), C.yellow, { shift: .4, w: 1.1 })
    + K.hi('M15 17 Q18 14 22 13.6') + K.heart(41, 7, 2.8)],
  anniversary: ['기념일·결혼식', K => `<circle cx="17.6" cy="30" r="10" fill="none" stroke="${STYLE.line}" stroke-width="5.6"/><circle cx="17.6" cy="30" r="10" fill="none" stroke="${C.yellow}" stroke-width="3"/>`
    + `<circle cx="30.4" cy="30" r="10" fill="none" stroke="${STYLE.line}" stroke-width="5.6"/><circle cx="30.4" cy="30" r="10" fill="none" stroke="${C.yellow}" stroke-width="3"/>`
    + `<path d="M24.4 21.6 a10 10 0 0 1 0 16.8" fill="none" stroke="${STYLE.line}" stroke-width="5.6"/><path d="M24.4 21.6 a10 10 0 0 1 0 16.8" fill="none" stroke="${C.yellow}" stroke-width="3"/>`
    + K.hi('M10.6 25 Q12.4 21.4 16 20.6', 1.2)
    + K.obj('M13 16.4 L15.6 12.4 H19.6 L22.2 16.4 L17.6 21.6Z', '#bfe6fb', { shift: .5, w: 1.3 }) + K.detail('M13 16.4 H22.2 M15.6 12.4 L17.6 16.4 L19.6 12.4', .8)
    + K.heart(37, 9.6, 3.4, C.red) + K.sparkle(9, 8, 2.6)],
  rest: ['휴식·잠', K => K.obj('M27.6 5 Q13.6 7 12.6 23 Q12.6 38.6 27.6 42.6 Q36 43.6 41.4 37.4 Q25.6 37.6 23.6 23 Q23 11.6 27.6 5Z', C.yellow)
    + K.detail('M15.4 22.4 Q17.4 24.6 19.4 22.4') + K.blush(15.4, 27.4, 1.8) + K.detail('M17.6 30 q1.2 .9 2.4 0', 1)
    + K.hi('M16.6 13 Q18.6 9.6 22 8.4')
    + K.line('M31 9.6 H36 L31 15.6 H36', 1.5) + K.line('M38.4 18 H41.6 L38.4 22 H41.6', 1.3)
    + K.sparkle(37, 30, 2.4) + K.sparkle(7, 41, 2)],
};

function build(prefix = 'pn_') {
  const out = {};
  for (const [key, [name, fn]] of Object.entries(ART)) {
    const K = kit({ ...STYLE, uid: prefix + key });
    out[prefix + key] = { name, svg: fn(K) };
  }
  return out;
}

module.exports = { build, STYLE, PALETTE: C, ORDER: Object.keys(ART) };
