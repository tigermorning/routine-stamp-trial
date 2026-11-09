"""참 잘했어요 도장·마스킹테이프·D-day 팩에 새 그림을 더한다(2026-11-09 사용자 요청: «내용이 부실하다, 더 다양한 모양, 팩마다 최소 15개 이상»).
기존 그림과 같은 화풍(번진 잉크 도장, 찢긴 끝 테이프, 뜯는 달력)으로 조각 함수를 조합해 만든다. 여러 번 돌려도 같은 결과(이미 있는 id 는 건너뜀).
쓰는 법(저장소 루트에서): python tools/stickers/extra_packs.py"""
import json, math, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
INK_DASH = '46 1.1 9 1.3 30 1 14 1.2'
FONT = 'style="font-family:inherit"'


def text(x, y, s, size, fill, w=None, weight=800):
    tl = f' textLength="{w}" lengthAdjust="spacingAndGlyphs"' if w else ''
    return f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{size}" font-weight="{weight}" fill="{fill}"{tl} {FONT}>{s}</text>'


def poly(n, r, cx=24, cy=24, rot=-90, inner=None):
    pts = []
    for i in range(n * (2 if inner else 1)):
        rr = r if (not inner or i % 2 == 0) else inner
        a = math.radians(rot + i * (360 / (n * (2 if inner else 1))))
        pts.append(f'{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}')
    return ' '.join(pts)


# ---------- 도장 ----------
def stamp(shape, lines, color, rot):
    c = color
    if shape == 'circle':
        body = f'<circle cx="24" cy="24" r="19" fill="none" stroke="{c}" stroke-width="2.6" stroke-dasharray="{INK_DASH}" stroke-linecap="round"/><circle cx="24" cy="24" r="15" fill="none" stroke="{c}" stroke-width="1.2" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'rect':
        body = f'<rect x="6" y="8" width="36" height="32" rx="5" fill="none" stroke="{c}" stroke-width="2.6" stroke-dasharray="{INK_DASH}"/><rect x="9.6" y="11.6" width="28.8" height="24.8" rx="3" fill="none" stroke="{c}" stroke-width="1.1" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'oval':
        body = f'<ellipse cx="24" cy="24" rx="20" ry="15" fill="none" stroke="{c}" stroke-width="2.6" stroke-dasharray="{INK_DASH}"/><ellipse cx="24" cy="24" rx="16" ry="11.2" fill="none" stroke="{c}" stroke-width="1.1" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'hex':
        body = f'<polygon points="{poly(6, 20)}" fill="none" stroke="{c}" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/><polygon points="{poly(6, 15.5)}" fill="none" stroke="{c}" stroke-width="1.1" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'oct':
        body = f'<polygon points="{poly(8, 20, rot=-67.5)}" fill="none" stroke="{c}" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/><polygon points="{poly(8, 15.6, rot=-67.5)}" fill="none" stroke="{c}" stroke-width="1.1" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'burst':
        body = f'<polygon points="{poly(12, 21, inner=15.5)}" fill="none" stroke="{c}" stroke-width="2.2" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'diamond':
        body = f'<polygon points="24,3 45,24 24,45 3,24" fill="none" stroke="{c}" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/><polygon points="24,9 39,24 24,39 9,24" fill="none" stroke="{c}" stroke-width="1.1" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'shield':
        body = f'<path d="M24 4 L41 9 V23 C41 33 33 40 24 44 C15 40 7 33 7 23 V9 Z" fill="none" stroke="{c}" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/><path d="M24 9 L36 12.6 V23 C36 30 30.5 35.2 24 38.4 C17.5 35.2 12 30 12 23 V12.6 Z" fill="none" stroke="{c}" stroke-width="1.1" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'ticket':
        body = f'<path d="M5 12 H43 V20 a4 4 0 0 0 0 8 V36 H5 V28 a4 4 0 0 0 0 -8 Z" fill="none" stroke="{c}" stroke-width="2.4" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'scallop':
        pts = []
        for i in range(14):
            a = i * 2 * math.pi / 14
            pts.append(f'{24 + 19 * math.cos(a):.1f} {24 + 19 * math.sin(a):.1f}')
        d = 'M' + ' A4.2 4.2 0 0 1 '.join(pts) + ' A4.2 4.2 0 0 1 ' + pts[0] + 'Z'
        body = f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.4" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/><circle cx="24" cy="24" r="13.5" fill="none" stroke="{c}" stroke-width="1.1" stroke-dasharray="{INK_DASH}"/>'
    elif shape == 'heart':
        body = f'<path d="M24 41 C8 30 5 20 10 14 C15 9 22 11 24 16 C26 11 33 9 38 14 C43 20 40 30 24 41Z" fill="none" stroke="{c}" stroke-width="2.6" stroke-linejoin="round" stroke-dasharray="{INK_DASH}"/>'
    else:
        raise ValueError(shape)
    ys = {1: [26.6], 2: [22.6, 33]}[len(lines)]
    txt = ''
    for ln, y in zip(lines, ys):
        if shape in ('ticket', 'rect', 'oval') and len(lines) == 1:
            y = 27.5
        if shape == 'heart':
            y = 24 if len(lines) == 1 else y - 3
        size = 10 if len(lines) == 2 else (11 if len(ln) <= 3 else 9)
        w = min(26, max(10, len(ln) * (size * 0.95)))
        txt += text(24, y, ln, size, c, w)
    return f'<g transform="rotate({rot} 24 24)">{body}{txt}</g>'


RED, BLUE, GREEN, PURPLE, ORANGE, PINK, TEAL, NAVY = '#d9372f', '#2f5fb3', '#2f8f4e', '#7b4fc4', '#e8731c', '#d6457f', '#1f8f8a', '#2c3e7a'
# (id, 이름, 모양, 글줄, 색, 기울기)
STAMPS = [
    ('sl_great', '대단해요', 'circle', ['대단', '해요'], ORANGE, -7),
    ('sl_cool', '멋져요', 'oval', ['멋져요'], PINK, 5),
    ('sl_thanks', '고마워요', 'heart', ['고마워'], PINK, -5),
    ('sl_smart', '똑똑해요', 'hex', ['똑똑', '해요'], BLUE, 6),
    ('sl_try', '도전했어요', 'oct', ['도전', '했어요'], TEAL, -4),
    ('sl_win', '이겼다', 'burst', ['이겼다'], RED, 8),
    ('sl_ok', 'OK', 'circle', ['OK'], GREEN, -9),
    ('sl_pass2', 'PASS', 'rect', ['PASS'], GREEN, 5),
    ('sl_best2', 'BEST', 'ticket', ['BEST'], PURPLE, -6),
    ('sl_wow', 'WOW', 'burst', ['WOW'], ORANGE, -5),
    ('sl_goodday', '좋은 하루', 'scallop', ['좋은', '하루'], PINK, 4),
    ('sl_tomorrow', '내일도', 'shield', ['내일도'], NAVY, -3),
    ('sl_hard', '수고했어요', 'rect', ['수고', '했어요'], BLUE, -4),
    ('sl_early', '일찍 일어남', 'oval', ['일찍', '기상'], ORANGE, 6),
    ('sl_water', '물 마셨어요', 'circle', ['물 한', '잔'], TEAL, -6),
    ('sl_walk', '걸었어요', 'hex', ['오늘', '걸음'], GREEN, 5),
    ('sl_study', '공부 완료', 'rect', ['공부', '완료'], NAVY, 4),
    ('sl_workout', '운동 완료', 'oct', ['운동', '완료'], RED, -5),
    ('sl_meds', '약 먹었어요', 'ticket', ['약 먹음'], PURPLE, 5),
    ('sl_clean', '청소 완료', 'diamond', ['청소', '끝'], TEAL, 0),
    ('sl_slept', '푹 잤어요', 'oval', ['푹 잠'], NAVY, -5),
    ('sl_rest', '쉬어도 돼요', 'scallop', ['쉬어도', '돼요'], GREEN, -4),
    ('sl_proud', '뿌듯해요', 'heart', ['뿌듯'], RED, 6),
    ('sl_lucky', '행운', 'diamond', ['행운'], ORANGE, 3),
]

# ---------- 마스킹테이프 ----------
STRIP = 'M6 14 L8 14 L6 17.7 L8 21.4 L6 25.1 L8 28.8 L6 32.5 L6 33 L42 33 L42 32.5 L40 28.8 L42 25.1 L40 21.4 L42 17.7 L40 14 Z'
SHORT = 'M12 14 L14 14 L12 17.7 L14 21.4 L12 25.1 L14 28.8 L12 32.5 L12 33 L36 33 L36 32.5 L34 28.8 L36 25.1 L34 21.4 L36 17.7 L34 14 Z'
DIAG = 'M6 30 L8 32 L6.5 33.5 L9 35.5 L7.5 37 L38 12 L40 14 L41.5 12.5 L42 10 L10 36 Z'
CORNER = 'M6 6 L26 6 L24.5 8 L26 10 L24.5 12 L26 14 L8 32 L6 32 L7.5 29.5 L6 27.5 L7.5 25.5 L6 23.5 Z'
WAVE = 'M6 14 Q10 11 14 14 T22 14 T30 14 T38 14 L42 14 L42 33 L38 33 Q34 36 30 33 T22 33 T14 33 T6 33 Z'


def pat(kind, c1, c2):
    if kind == 'diag':
        return ('rotate(45)', 8, 8, f'<rect width="4" height="8" fill="{c1}"/>')
    if kind == 'thin':
        return ('rotate(0)', 6, 6, f'<rect width="6" height="1.6" y="2" fill="{c1}"/>')
    if kind == 'bigdot':
        return ('rotate(0)', 12, 12, f'<circle cx="6" cy="6" r="3.2" fill="{c1}"/>')
    if kind == 'tiny':
        return ('rotate(0)', 5, 5, f'<circle cx="2.5" cy="2.5" r=".9" fill="{c1}"/>')
    if kind == 'tri':
        return ('rotate(0)', 10, 10, f'<path d="M0 10 L5 2 L10 10Z" fill="{c1}"/>')
    if kind == 'scal':
        return ('rotate(0)', 10, 8, f'<path d="M0 8 A5 5 0 0 1 10 8" fill="none" stroke="{c1}" stroke-width="1.4"/>')
    if kind == 'leaf':
        return ('rotate(0)', 12, 12, f'<ellipse cx="6" cy="6" rx="4.2" ry="2" transform="rotate(-35 6 6)" fill="{c1}"/>')
    if kind == 'cloud':
        return ('rotate(0)', 14, 12, f'<circle cx="5" cy="7" r="2.6" fill="{c1}"/><circle cx="8.6" cy="5.6" r="3" fill="{c1}"/><circle cx="11.6" cy="7.4" r="2.2" fill="{c1}"/>')
    if kind == 'cross':
        return ('rotate(0)', 9, 9, f'<path d="M4.5 2 V7 M2 4.5 H7" stroke="{c1}" stroke-width="1.5" stroke-linecap="round"/>')
    if kind == 'plaid':
        return ('rotate(0)', 12, 12, f'<rect width="12" height="3" y="3" fill="{c1}" opacity=".6"/><rect width="3" height="12" x="3" fill="{c2 or c1}" opacity=".6"/>')
    if kind == 'dash':
        return ('rotate(0)', 12, 7, f'<rect width="7" height="1.8" x="1" y="2.6" rx=".9" fill="{c1}"/>')
    if kind == 'stripe2':
        return ('rotate(0)', 10, 10, f'<rect width="10" height="2" y="1" fill="{c1}"/><rect width="10" height="2" y="6" fill="{c2 or c1}"/>')
    if kind == 'heart':
        return ('rotate(0)', 10, 10, f'<path d="M5 8 c-3 -2 -3.6 -3.6 -2.2 -4.4 c1 -.6 1.8 0 2.2 .8 c.4 -.8 1.2 -1.4 2.2 -.8 c1.4 .8 .8 2.4 -2.2 4.4z" fill="{c1}"/>')
    if kind == 'star':
        return ('rotate(0)', 12, 12, f'<polygon points="{poly(5, 3.6, cx=6, cy=6, inner=1.5)}" fill="{c1}"/>')
    if kind == 'check':
        return ('rotate(0)', 10, 10, f'<rect width="5" height="5" fill="{c1}"/><rect width="5" height="5" x="5" y="5" fill="{c1}"/>')
    if kind == 'sakura':
        return ('rotate(0)', 14, 14, ''.join(f'<ellipse cx="{7 + 2.6 * math.cos(math.radians(a)):.1f}" cy="{7 + 2.6 * math.sin(math.radians(a)):.1f}" rx="2" ry="1.6" transform="rotate({a} {7 + 2.6 * math.cos(math.radians(a)):.1f} {7 + 2.6 * math.sin(math.radians(a)):.1f})" fill="{c1}"/>' for a in range(0, 360, 72)) + '<circle cx="7" cy="7" r="1" fill="#fff4a8"/>')
    return ('rotate(0)', 8, 8, '')


# (id, 이름, 바탕색, 무늬, 무늬색, 보조색, 모양, 기울기)
WASHI = [
    ('wt_diag', '사선 줄무늬', '#fff3b0', 'diag', '#ffc94d', None, STRIP, -6),
    ('wt_thin', '가는 줄', '#e6f3ff', 'thin', '#7fb6e8', None, STRIP, 5),
    ('wt_bigdot', '큰 물방울', '#ffe3ec', 'bigdot', '#ff9eb8', None, STRIP, -4),
    ('wt_tiny', '잔 물방울', '#e9f7e4', 'tiny', '#6cbf6a', None, SHORT, 7),
    ('wt_tri', '삼각 깃발', '#fff0d9', 'tri', '#ff9c5b', None, STRIP, -7),
    ('wt_scal', '조개 물결', '#e3f1ff', 'scal', '#5aa9e6', None, STRIP, 4),
    ('wt_leaf2', '잎사귀', '#f0f7df', 'leaf', '#8bc34a', None, STRIP, -5),
    ('wt_cloud2', '구름', '#dff1ff', 'cloud', '#ffffff', None, SHORT, 6),
    ('wt_cross', '십자 수놓기', '#fdebd3', 'cross', '#e0894d', None, STRIP, -3),
    ('wt_plaid2', '체크 담요', '#fff', 'plaid', '#e86a6a', '#5a8de0', STRIP, 5),
    ('wt_dash', '점선', '#f3e8ff', 'dash', '#a98be0', None, STRIP, -6),
    ('wt_stripe2', '두 줄 무늬', '#fff7e0', 'stripe2', '#ff8fa3', '#7ecbf2', STRIP, 4),
    ('wt_heart2', '작은 하트', '#ffdfe6', 'heart', '#ff7b98', None, SHORT, -8),
    ('wt_star2', '반짝 별', '#e8edff', 'star', '#ffd24d', None, STRIP, 6),
    ('wt_check2', '체스판', '#fff', 'check', '#9aa5b8', None, STRIP, -4),
    ('wt_sakura', '벚꽃', '#fff0f4', 'sakura', '#ff9fbc', None, STRIP, 5),
    ('wt_diag_b', '파란 사선', '#e4f0ff', 'diag', '#6aa8f0', None, DIAG, 0),
    ('wt_corner', '모서리 테이프', '#ffe9a8', 'diag', '#ffc247', None, CORNER, 0),
    ('wt_wave2', '물결 테이프', '#d9f1ff', 'thin', '#6fb7e8', None, WAVE, -3),
    ('wt_solid_pink', '분홍 무지', '#ffc9d8', None, None, None, STRIP, -5),
    ('wt_solid_mint', '민트 무지', '#bfeedd', None, None, None, SHORT, 6),
    ('wt_solid_lemon', '레몬 무지', '#fff09a', None, None, None, STRIP, 4),
    ('wt_solid_lav', '라벤더 무지', '#dccdfa', None, None, None, STRIP, -4),
    ('wt_solid_sky', '하늘 무지', '#bfe3ff', None, None, None, DIAG, 0),
]


def washi(pid, base, kind, c1, c2, shape, rot):
    if kind:
        tr, w, h, inner = pat(kind, c1, c2)
        defs = f'<defs><pattern id="wp-{pid}" width="{w}" height="{h}" patternUnits="userSpaceOnUse" patternTransform="{tr}">{inner}</pattern></defs>'
        patfill = f'<path d="{shape}" fill="url(#wp-{pid})" stroke="rgba(0,0,0,.12)" stroke-width=".8" stroke-linejoin="round"/>'
    else:
        defs = ''
        patfill = f'<path d="{shape}" fill="none" stroke="rgba(0,0,0,.12)" stroke-width=".8" stroke-linejoin="round"/>'
    return (f'{defs}<g transform="rotate({rot} 24 24)"><path d="{shape}" fill="#fff" stroke="#fff" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="{shape}" fill="{base}" opacity=".95"/>{patfill}<path d="M10 17 H40" stroke="#fff" stroke-width="1.4" opacity=".4" stroke-linecap="round"/></g>')


# ---------- D-day ----------
def tile(label, num, c_head, c_line, head_txt='D-DAY'):
    return (f'<rect x="7" y="9" width="34" height="34" rx="5" fill="#fff" stroke="#fff" stroke-width="4"/><rect x="7" y="9" width="34" height="34" rx="5" fill="#fffdf8" stroke="{c_line}" stroke-width="2"/>'
            f'<path d="M7 14 a5 5 0 0 1 5 -5 H36 a5 5 0 0 1 5 5 V21 H7Z" fill="{c_head}" stroke="{c_line}" stroke-width="2" stroke-linejoin="round"/>'
            '<rect x="14" y="5" width="3.6" height="8" rx="1.8" fill="#e8e8ee" stroke="#6b7280" stroke-width="1.4"/><rect x="30.4" y="5" width="3.6" height="8" rx="1.8" fill="#e8e8ee" stroke="#6b7280" stroke-width="1.4"/>'
            + text(24, 18.2, head_txt, 6.4, '#fff') + text(24, 36.4, num, 12.4 if len(num) <= 4 else 10.4, c_line)
            + f'<path d="M41 36 L33 43 V36Z" fill="#e9e4d8" stroke="{c_line}" stroke-width="1.2" stroke-linejoin="round" opacity=".9"/>')


def balloon(num, fill, line):
    return (f'<path d="M24 4 C14 4 10 12 10 19 C10 28 18 33 24 36 C30 33 38 28 38 19 C38 12 34 4 24 4Z" fill="#fff" stroke="#fff" stroke-width="4"/>'
            f'<path d="M24 4 C14 4 10 12 10 19 C10 28 18 33 24 36 C30 33 38 28 38 19 C38 12 34 4 24 4Z" fill="{fill}" stroke="{line}" stroke-width="2" stroke-linejoin="round"/>'
            f'<ellipse cx="18" cy="12" rx="3" ry="4.6" transform="rotate(25 18 12)" fill="#fff" opacity=".5"/><path d="M22 36 L26 36 L24.6 39 L23.4 39Z" fill="{line}"/>'
            f'<path d="M24 39 q-3 3 0 5 q3 2 0 4" fill="none" stroke="{line}" stroke-width="1.5" stroke-linecap="round"/>'
            + text(24, 22.6, num, 11 if len(num) <= 4 else 9, '#fff', 20 if len(num) > 3 else None))


def ticket_dd(num, fill, line):
    return (f'<path d="M4 13 H44 V21 a4 4 0 0 0 0 8 V37 H4 V29 a4 4 0 0 0 0 -8 Z" fill="#fff" stroke="#fff" stroke-width="4" stroke-linejoin="round"/>'
            f'<path d="M4 13 H44 V21 a4 4 0 0 0 0 8 V37 H4 V29 a4 4 0 0 0 0 -8 Z" fill="{fill}" stroke="{line}" stroke-width="2" stroke-linejoin="round"/>'
            f'<path d="M33 14 V36" stroke="#fff" stroke-width="1.4" stroke-dasharray="2.4 2.2" opacity=".8"/>'
            + text(18.5, 29.4, num, 11.6 if len(num) <= 4 else 9.4, '#fff', 25 if len(num) > 3 else None) + text(38.4, 28.4, 'D', 8.4, '#fff'))


def flag(num, fill, line):
    return (f'<path d="M12 6 V44" stroke="{line}" stroke-width="3" stroke-linecap="round"/><path d="M12 8 H40 L35 16 L40 24 H12Z" fill="#fff" stroke="#fff" stroke-width="4" stroke-linejoin="round"/>'
            f'<path d="M12 8 H40 L35 16 L40 24 H12Z" fill="{fill}" stroke="{line}" stroke-width="2" stroke-linejoin="round"/>'
            + text(25, 19.6, num, 8.6 if len(num) <= 4 else 7.2, '#fff', 17 if len(num) > 3 else None))


def badge(num, fill, line):
    return (f'<circle cx="24" cy="24" r="19" fill="#fff" stroke="#fff" stroke-width="4"/><circle cx="24" cy="24" r="19" fill="{fill}" stroke="{line}" stroke-width="2"/>'
            f'<circle cx="24" cy="24" r="15" fill="none" stroke="#fff" stroke-width="1.2" stroke-dasharray="2 2.4" opacity=".85"/>'
            + text(24, 22, 'D', 7, '#fff') + text(24, 33.6, num, 11 if len(num) <= 4 else 9, '#fff', 22 if len(num) > 3 else None))


def bubble(num, fill, line):
    return (f'<path d="M8 8 H40 a3 3 0 0 1 3 3 V30 a3 3 0 0 1 -3 3 H28 L22 41 V33 H8 a3 3 0 0 1 -3 -3 V11 a3 3 0 0 1 3 -3Z" fill="#fff" stroke="#fff" stroke-width="4" stroke-linejoin="round"/>'
            f'<path d="M8 8 H40 a3 3 0 0 1 3 3 V30 a3 3 0 0 1 -3 3 H28 L22 41 V33 H8 a3 3 0 0 1 -3 -3 V11 a3 3 0 0 1 3 -3Z" fill="{fill}" stroke="{line}" stroke-width="2" stroke-linejoin="round"/>'
            + text(24, 25.6, num, 11.6 if len(num) <= 4 else 9.4, '#fff', 28 if len(num) > 3 else None))


COL = {'teal': ('#3fb8c8', '#1f7d8c'), 'blue': ('#6c8cff', '#3f58b8'), 'purple': ('#8e5bd6', '#5b3a9e'), 'red': ('#e8434f', '#a82a38'),
       'orange': ('#ffb347', '#c26a10'), 'sky': ('#6cb7ff', '#2f78c0'), 'green': ('#6fcf7f', '#2f8f4e'), 'pink': ('#ff8fb3', '#c2457a'), 'navy': ('#5b6fa8', '#2c3e7a')}
# (id, 이름, 모양, 글, 색)
DDAYS = [
    ('dd_m200', 'D-200', 'tile', 'D-200', 'blue'), ('dd_m60', 'D-60', 'tile', 'D-60', 'teal'), ('dd_m21', 'D-21', 'tile', 'D-21', 'green'),
    ('dd_m10', 'D-10', 'tile', 'D-10', 'orange'), ('dd_m5', 'D-5', 'tile', 'D-5', 'pink'), ('dd_m2', 'D-2', 'tile', 'D-2', 'red'),
    ('dd_b_m100', 'D-100 풍선', 'balloon', 'D-100', 'sky'), ('dd_b_m30', 'D-30 풍선', 'balloon', 'D-30', 'green'), ('dd_b_m7', 'D-7 풍선', 'balloon', 'D-7', 'pink'),
    ('dd_b_day', 'D-DAY 풍선', 'balloon', 'D-DAY', 'red'),
    ('dd_t_m50', 'D-50 티켓', 'ticket', 'D-50', 'purple'), ('dd_t_m14', 'D-14 티켓', 'ticket', 'D-14', 'teal'), ('dd_t_m3', 'D-3 티켓', 'ticket', 'D-3', 'orange'),
    ('dd_t_day', 'D-DAY 티켓', 'ticket', 'DAY', 'red'),
    ('dd_f_m30', 'D-30 깃발', 'flag', 'D-30', 'navy'), ('dd_f_m7', 'D-7 깃발', 'flag', 'D-7', 'orange'), ('dd_f_m1', 'D-1 깃발', 'flag', 'D-1', 'purple'),
    ('dd_f_day', 'D-DAY 깃발', 'flag', 'DAY', 'red'),
    ('dd_c_m100', 'D-100 동그라미', 'badge', '-100', 'blue'), ('dd_c_m10', 'D-10 동그라미', 'badge', '-10', 'green'), ('dd_c_day', 'D-DAY 동그라미', 'badge', 'DAY', 'red'),
    ('dd_c_p100', 'D+100 동그라미', 'badge', '+100', 'sky'),
    ('dd_s_m7', 'D-7 말풍선', 'bubble', 'D-7', 'teal'), ('dd_s_m1', 'D-1 말풍선', 'bubble', 'D-1', 'pink'), ('dd_s_day', 'D-DAY 말풍선', 'bubble', 'DAY!', 'red'),
    ('dd_s_p1', 'D+1 말풍선', 'bubble', 'D+1', 'orange'),
    ('dd_p3', 'D+3', 'tile', 'D+3', 'sky'), ('dd_p14', 'D+14', 'tile', 'D+14', 'green'), ('dd_p50', 'D+50', 'tile', 'D+50', 'purple'), ('dd_p500', 'D+500', 'tile', 'D+500', 'navy'),
    ('dd_p1000', 'D+1000', 'tile', 'D+1000', 'red'),
]
SHAPES = {'balloon': balloon, 'ticket': ticket_dd, 'flag': flag, 'badge': badge, 'bubble': bubble}


def build():
    syms, names = {}, {}
    for pid, ko, shape, lines, color, rot in STAMPS:
        syms[pid] = stamp(shape, lines, color, rot)
        names[pid] = ko
    for pid, ko, base, kind, c1, c2, shape, rot in WASHI:
        syms[pid] = washi(pid, base, kind, c1, c2, shape, rot)
        names[pid] = ko
    for pid, ko, shape, num, color in DDAYS:
        f, l = COL[color]
        if shape == 'tile':
            head = 'TODAY' if num == 'DAY' else 'D-DAY'
            syms[pid] = tile(ko, num, f, l, head)
        else:
            syms[pid] = SHAPES[shape](num, f, l)
        names[pid] = ko
    return syms, names


PACKS = {'sticker_seal': [x[0] for x in STAMPS], 'sticker_washi': [x[0] for x in WASHI], 'sticker_dday': [x[0] for x in DDAYS]}


def apply():
    p = os.path.join(ROOT, 'index.html')
    s = open(p, encoding='utf-8').read()
    syms, names = build()
    add = ''.join(f'<symbol id="sv-{pid}" viewBox="0 0 48 48">{body}</symbol>' for pid, body in syms.items() if f'<symbol id="sv-{pid}"' not in s)
    if add:
        i = s.index('<svg id="svSprite"')
        j = s.index('</svg>', i)
        s = s[:j] + add + s[j:]
    for pack, ids in PACKS.items():
        m = re.search(r"(%s:\{name:'[^']*',list:\[)([^\]]*)(\]\})" % pack, s)
        have = re.findall(r"'sv:([a-z0-9_]+)'", m.group(2))
        new = [i for i in ids if i not in have]
        lst = m.group(2) + ''.join(f",'sv:{i}'" for i in new)
        s = s[:m.start()] + m.group(1) + lst + m.group(3) + s[m.end():]
    m = re.search(r'const SV_NAMES=(\{.*?\});\n', s, re.S)
    d = json.loads(m.group(1))
    d.update({k: v for k, v in names.items()})
    s = s[:m.start()] + 'const SV_NAMES=' + json.dumps(d, ensure_ascii=False) + ';\n' + s[m.end():]
    open(p, 'w', encoding='utf-8', newline='').write(s)
    # 상품 설명의 개수(시험이 설명의 «N종»과 화면 목록 개수가 같은지 본다)
    p2 = os.path.join(ROOT, 'server', 'credits.py')
    c = open(p2, encoding='utf-8').read()
    cnt = {}
    for pack in PACKS:
        m = re.search(r"%s:\{name:'[^']*',list:\[([^\]]*)\]" % pack, s)
        cnt[pack] = len(re.findall(r"'[a-z]+:[a-z0-9_]+'", m.group(1)))
    for pack, n in cnt.items():
        c, k = re.subn(r'("%s": \{[^\n]*?)(\d+)종' % pack, lambda mm: f'{mm.group(1)}{n}종', c)
        assert k == 1, pack
    open(p2, 'w', encoding='utf-8', newline='').write(c)
    print('ok', {k: len(v) for k, v in PACKS.items()}, '현재 화면 개수', cnt)


if __name__ == '__main__':
    apply()
