import AsyncStorage from '@react-native-async-storage/async-storage';

import { takeTime } from '@/lib/schedule';

/** 날짜가 있는 일회성 일정. 도장 칸(반복 루틴)과 따로 저장한다. */
export type CalendarEvent = {
  id: string;
  title: string;
  /** YYYY-MM-DD */
  date: string;
  /** HH:MM (선택) */
  time?: string;
  done?: boolean;
};

/** 읽은 글에서 뽑은 일정 후보. 날짜를 못 찾았으면 date 가 없다. */
export type EventDraft = { title: string; date?: string; time?: string };

const KEY = 'routine-stamp:events:v1';
const MAX_TITLE = 40;

export async function loadEvents(): Promise<CalendarEvent[]> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((e) => e && typeof e.id === 'string' && typeof e.title === 'string' && typeof e.date === 'string')
      : [];
  } catch {
    return [];
  }
}

export async function saveEvents(events: CalendarEvent[]): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(events));
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

export function dateKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** 월·일이 실제 있는 날짜인가(2월 30일 같은 것을 거른다) */
function validDate(y: number, m: number, d: number): boolean {
  const date = new Date(y, m - 1, d);
  return date.getFullYear() === y && date.getMonth() === m - 1 && date.getDate() === d;
}

const FULL = /(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?/;
const MONTH_DAY = /(\d{1,2})\s*월\s*(\d{1,2})\s*일?/;
const SLASH = /(?<![\d/])(\d{1,2})\s*\/\s*(\d{1,2})(?![\d/])/;

/**
 * 문장에서 날짜를 찾아 YYYY-MM-DD 로 돌려주고 문장에서 지운다.
 * 연도가 없으면 오늘 이후 가장 가까운 그 월·일(이미 지났으면 다음 해)로 본다.
 */
export function takeDate(text: string, today: Date): { date?: string; rest: string } {
  let y: number | undefined;
  let mo: number;
  let d: number;
  let m = FULL.exec(text);
  if (m) {
    y = Number(m[1]);
    mo = Number(m[2]);
    d = Number(m[3]);
  } else if ((m = MONTH_DAY.exec(text) ?? SLASH.exec(text))) {
    mo = Number(m[1]);
    d = Number(m[2]);
  } else {
    return { rest: text.trim() };
  }
  if (y === undefined) {
    y = today.getFullYear();
    const todayStart = new Date(y, today.getMonth(), today.getDate());
    if (validDate(y, mo, d) && new Date(y, mo - 1, d) < todayStart) y += 1;
  }
  if (!validDate(y, mo, d)) return { rest: text.trim() };
  const rest = (text.slice(0, m.index) + ' ' + text.slice(m.index + m[0].length)).trim();
  return { date: `${y}-${pad(mo)}-${pad(d)}`, rest };
}

/** 줄에 날짜가 하나라도 있으면 «날짜 일정 메모»로 본다 */
export function hasDate(lines: readonly string[], today: Date = new Date()): boolean {
  return lines.some((line) => takeDate(line, today).date !== undefined);
}

/**
 * 읽은 줄들을 일정 후보로 묶는다. 메모 한 장은 일정 하나가 기본이고(날짜 줄·시간 줄·제목 줄이 따로 읽혀도 합친다),
 * 날짜가 이미 있는 일정에 또 다른 날짜가 나오면 새 일정으로 나눈다. 제목이 없는 일정은 버린다.
 */
export function parseEvents(lines: readonly string[], today: Date = new Date()): EventDraft[] {
  const drafts: { date?: string; time?: string; parts: string[] }[] = [];
  let current: { date?: string; time?: string; parts: string[] } = { parts: [] };
  const flush = () => {
    if (current.parts.length > 0 || current.date || current.time) drafts.push(current);
    current = { parts: [] };
  };
  for (const raw of lines) {
    const withDate = takeDate(raw, today);
    if (withDate.date && current.date && current.date !== withDate.date) flush();
    if (withDate.date) current.date = withDate.date;
    const withTime = takeTime(withDate.rest);
    if (withTime.time) {
      if (current.time && current.time !== withTime.time) flush();
      current.time = withTime.time;
    }
    const text = withTime.rest.replace(/^[:：,\-–·]+|[:：,\-–·]+$/g, '').trim();
    if (text) current.parts.push(text);
  }
  flush();
  return drafts
    .filter((d) => d.parts.length > 0)
    .map((d) => ({ title: d.parts.join(' ').slice(0, MAX_TITLE), date: d.date, time: d.time }));
}

/** «2026-11-07 10:30» 꼴의 짧은 설명 */
export function describeEvent(e: { date?: string; time?: string }): string {
  const date = e.date ?? '날짜 없음';
  return e.time ? `${date} ${e.time}` : date;
}

/** 날짜순(같은 날은 시간순)으로 정렬한 새 배열 */
export function sortEvents(events: readonly CalendarEvent[]): CalendarEvent[] {
  return [...events].sort((a, b) => `${a.date} ${a.time ?? ''}`.localeCompare(`${b.date} ${b.time ?? ''}`));
}

/** 오늘로부터 며칠 남았나(오늘 0, 내일 1, 지났으면 음수) */
export function daysUntil(date: string, today: Date = new Date()): number {
  const [y, m, d] = date.split('-').map(Number);
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  return Math.round((new Date(y, m - 1, d).getTime() - start) / 86_400_000);
}

export function dDayLabel(date: string, today: Date = new Date()): string {
  const n = daysUntil(date, today);
  if (n === 0) return '오늘';
  return n > 0 ? `D-${n}` : `${-n}일 지남`;
}

/** 그 달의 달력 칸. 앞쪽은 요일 맞춤용 빈칸(null), 값은 YYYY-MM-DD. month 는 0~11. */
export function monthCells(year: number, month: number): (string | null)[] {
  const cells: (string | null)[] = Array(new Date(year, month, 1).getDay()).fill(null);
  const days = new Date(year, month + 1, 0).getDate();
  for (let d = 1; d <= days; d++) cells.push(`${year}-${pad(month + 1)}-${pad(d)}`);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function eventsOn(events: readonly CalendarEvent[], date: string): CalendarEvent[] {
  return sortEvents(events.filter((e) => e.date === date));
}

/** YYYY-MM-DD 로 쓴 실제 있는 날짜인가 */
export function isValidDateKey(text: string): boolean {
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(text.trim());
  return !!m && validDate(Number(m[1]), Number(m[2]), Number(m[3]));
}

/** 날짜 입력을 YYYY-MM-DD 로 다듬는다(2026-3-4 → 2026-03-04). 잘못된 날짜면 null. */
export function normalizeDateKey(text: string): string | null {
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(text.trim());
  if (!m || !validDate(Number(m[1]), Number(m[2]), Number(m[3]))) return null;
  return `${m[1]}-${pad(Number(m[2]))}-${pad(Number(m[3]))}`;
}

/** 시간 입력: 빈 칸이면 undefined(시간 없음), «7:30»·«07:30» 이면 'HH:MM', 잘못된 입력이면 null */
export function parseTimeInput(text: string): string | undefined | null {
  const t = text.trim();
  if (!t) return undefined;
  const m = /^(\d{1,2}):(\d{2})$/.exec(t);
  if (!m || Number(m[1]) > 23 || Number(m[2]) > 59) return null;
  return `${pad(Number(m[1]))}:${m[2]}`;
}

export function weekdayOf(date: string): number {
  const [y, m, d] = date.split('-').map(Number);
  return new Date(y, m - 1, d).getDay();
}

/** 초안을 일정으로 확정한다. 날짜가 없는 초안은 건너뛰고 skipped 로 돌려준다. */
export function addEvents(
  current: readonly CalendarEvent[],
  drafts: readonly EventDraft[],
  now: number = Date.now(),
): { events: CalendarEvent[]; added: number; skipped: number; duplicates: number } {
  const events = [...current];
  let added = 0;
  let skipped = 0;
  let duplicates = 0;
  drafts.forEach((draft, i) => {
    if (!draft.date || !draft.title.trim()) {
      skipped += 1;
      return;
    }
    const same = events.some((e) => e.date === draft.date && (e.time ?? '') === (draft.time ?? '') && e.title === draft.title.trim());
    if (same) {
      duplicates += 1;
      return;
    }
    events.push({ id: `e-${now}-${i}`, title: draft.title.trim(), date: draft.date, time: draft.time });
    added += 1;
  });
  return { events, added, skipped, duplicates };
}
