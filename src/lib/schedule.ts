import { MAX_SLOTS, type Slot } from '@/lib/stamps';

/** 읽은 한 줄에서 뽑은 일정. days 가 없으면 매일. */
export type ScheduleItem = { name: string; days?: number[]; time?: string };

const DAY_INDEX: Record<string, number> = { 일: 0, 월: 1, 화: 2, 수: 3, 목: 4, 금: 5, 토: 6 };
const DAY_LABEL = ['일', '월', '화', '수', '목', '금', '토'];
const DAY_TOKEN = /^(매일|평일|주말|[월화수목금토일]([,/·~]?[월화수목금토일])*)(요일)?$/;
const BULLET = /^\s*(?:[-•*·□☐✓]|\d+[.)])\s*/;
const TIME = /(오전|오후|아침|저녁|밤|새벽)?\s*(\d{1,2})\s*(?:시\s*(반)?|:)\s*(\d{1,2})?\s*(?:분)?/;

function daysFromToken(token: string): number[] {
  const t = token.replace(/요일$/, '');
  if (t === '매일') return [0, 1, 2, 3, 4, 5, 6];
  if (t === '평일') return [1, 2, 3, 4, 5];
  if (t === '주말') return [0, 6];
  const result = new Set<number>();
  const chars = [...t];
  for (let i = 0; i < chars.length; i++) {
    const c = chars[i];
    if (c === '~' && i > 0 && i < chars.length - 1) {
      // 월~금 처럼 범위(일요일에서 토요일 방향이 아닌 같은 주 안에서만)
      const from = DAY_INDEX[chars[i - 1]];
      const to = DAY_INDEX[chars[i + 1]];
      for (let d = from; d <= to; d++) result.add(d);
    } else if (c in DAY_INDEX) {
      result.add(DAY_INDEX[c]);
    }
  }
  return [...result].sort((a, b) => a - b);
}

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

/** «월수금 07:00 스트레칭», «스트레칭 월/수/금 7시 반», «매일 저녁 9시 책 읽기» 같은 한 줄을 일정으로. 이름이 비면 null. */
export function parseLine(line: string): ScheduleItem | null {
  let rest = line.replace(BULLET, '').trim();

  // 시간 찾기 (찾으면 문장에서 지운다)
  let time: string | undefined;
  const m = TIME.exec(rest);
  if (m) {
    let hour = Number(m[2]);
    const minute = m[3] ? 30 : m[4] ? Number(m[4]) : 0;
    const period = m[1];
    if (period && ['오후', '저녁', '밤'].includes(period) && hour < 12) hour += 12;
    if (hour <= 23 && minute <= 59) {
      time = `${pad(hour)}:${pad(minute)}`;
      rest = (rest.slice(0, m.index) + ' ' + rest.slice(m.index + m[0].length)).trim();
    }
  }

  // 요일 토큰 찾기: 공백으로 나눈 낱말 중 요일 꼴인 것만(«일기»처럼 낱말 일부는 요일로 보지 않는다)
  const days = new Set<number>();
  const nameTokens: string[] = [];
  for (const token of rest.split(/\s+/).filter(Boolean)) {
    if (DAY_TOKEN.test(token)) daysFromToken(token).forEach((d) => days.add(d));
    else nameTokens.push(token);
  }

  const name = nameTokens.join(' ').replace(/^[:：,\-–]+|[:：,\-–]+$/g, '').trim();
  if (!name) return null;
  const sorted = [...days].sort((a, b) => a - b);
  return {
    name,
    days: sorted.length > 0 && sorted.length < 7 ? sorted : undefined,
    time,
  };
}

export function parseSchedule(lines: readonly string[]): ScheduleItem[] {
  return lines.map(parseLine).filter((x): x is ScheduleItem => x !== null);
}

/** 화면에 보여 줄 짧은 설명: «월 수 금 · 07:00» */
export function describe(item: { days?: number[]; time?: string }): string {
  const day = item.days && item.days.length > 0 ? item.days.map((d) => DAY_LABEL[d]).join(' ') : '매일';
  return item.time ? `${day} · ${item.time}` : day;
}

/** 그 요일(0=일)에 하는 칸인가. 일정이 없으면 매일. */
export function isDueOn(slot: Slot, weekday: number): boolean {
  return !slot.days || slot.days.length === 0 || slot.days.includes(weekday);
}

export type ApplyResult = { slots: Slot[]; added: string[]; updated: string[]; overflow: string[] };

/**
 * 일정 항목을 칸 목록에 반영한다(순수 함수). 이름이 같은(공백 무시) 칸은 일정만 바꾸고(id·도장 기록 유지),
 * 없는 이름은 새 칸으로 넣는다. 최대 칸 수를 넘으면 overflow.
 */
export function applySchedule(current: readonly Slot[], items: readonly ScheduleItem[], now: number = Date.now()): ApplyResult {
  const squash = (t: string) => t.replace(/\s+/g, '');
  const slots = current.map((s) => ({ ...s }));
  const added: string[] = [];
  const updated: string[] = [];
  const overflow: string[] = [];
  items.forEach((item, i) => {
    const existing = slots.find((s) => squash(s.name) === squash(item.name));
    if (existing) {
      existing.days = item.days;
      existing.time = item.time;
      updated.push(existing.name);
    } else if (slots.length >= MAX_SLOTS) {
      overflow.push(item.name);
    } else {
      slots.push({ id: `c-${now}-${i}`, icon: '✅', name: item.name.slice(0, 30), days: item.days, time: item.time });
      added.push(item.name);
    }
  });
  return { slots, added, updated, overflow };
}
