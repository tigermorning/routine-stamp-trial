import AsyncStorage from '@react-native-async-storage/async-storage';

/** 0 = 비움, 1 = 연한 도장(조금만 했어요), 2 = 진한 도장(다 했어요) */
export type StampLevel = 0 | 1 | 2;

/**
 * days: 하는 요일(0=일 … 6=토). 없으면 매일. time: 'HH:MM'(선택).
 * 일정 필드는 선택 항목이라 이전에 저장된 칸(일정 없음)도 그대로 읽힌다.
 */
export type Slot = { id: string; icon: string; name: string; days?: number[]; time?: string };

/** 처음 쓰는 사람에게 채워 주는 기본 칸 세 개. 이후 칸 목록은 SLOTS_KEY 에 따로 저장한다. */
export const DEFAULT_SLOTS: readonly Slot[] = [
  { id: 'water', icon: '💧', name: '물 마시기' },
  { id: 'stretch', icon: '🧘', name: '스트레칭' },
  { id: 'read', icon: '📖', name: '책 읽기' },
];

/** 날짜(YYYY-MM-DD) → 칸 id → 도장 단계 */
export type StampLog = Record<string, Record<string, StampLevel>>;

const STORAGE_KEY = 'routine-stamp:v1';
/** 칸 목록 저장 키. 도장 기록(STORAGE_KEY)은 칸 id 로만 가리키므로 형식을 바꾸지 않아도 이전 데이터가 그대로 쓰인다. */
const SLOTS_KEY = 'routine-stamp:slots:v1';

/** 칸은 최대 8개까지 */
export const MAX_SLOTS = 8;
const NEW_SLOT_ICON = '✅';
const MAX_NAME_LENGTH = 30;

/** 폰의 현재 시간대 기준 오늘 날짜 */
export function todayKey(d: Date = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** 칸을 누를 때마다: 비움 → 진한 도장 → 연한 도장 → 비움 */
export function nextLevel(level: StampLevel): StampLevel {
  if (level === 0) return 2;
  if (level === 2) return 1;
  return 0;
}

/** 그 칸에 도장(연한 것 포함)이 찍힌 날의 누적 일수. 연속이 아니라 누적이다. */
export function countDays(log: StampLog, slotId: string): number {
  return Object.values(log).filter((day) => (day[slotId] ?? 0) > 0).length;
}

export async function loadLog(): Promise<StampLog> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StampLog) : {};
  } catch {
    // 저장된 값이 깨졌거나 읽지 못하면 빈 기록으로 시작한다
    return {};
  }
}

export async function saveLog(log: StampLog): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(log));
}

function isSlot(x: unknown): x is Slot {
  const s = x as Slot;
  return !!s && typeof s.id === 'string' && typeof s.icon === 'string' && typeof s.name === 'string';
}

/** 저장된 칸 목록. 없거나 깨졌으면 기본 3칸. */
export async function loadSlots(): Promise<Slot[]> {
  try {
    const raw = await AsyncStorage.getItem(SLOTS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0 && parsed.every(isSlot)) return parsed;
    }
  } catch {
    // 읽지 못하면 기본 칸으로 시작한다
  }
  return [...DEFAULT_SLOTS];
}

export async function saveSlots(slots: Slot[]): Promise<void> {
  await AsyncStorage.setItem(SLOTS_KEY, JSON.stringify(slots));
}

export type AddResult = { slots: Slot[]; added: string[]; duplicates: string[]; overflow: string[] };

/**
 * 이름 목록을 칸으로 추가한다(순수 함수). 앞뒤 공백을 지우고, 빈 이름·이미 있는 이름(공백 무시)은 건너뛰고,
 * 최대 칸 수를 넘는 것은 overflow 로 돌려준다. 기존 칸의 id 는 바꾸지 않는다.
 */
export function addSlots(current: readonly Slot[], names: readonly string[], now: number = Date.now()): AddResult {
  const slots = [...current];
  const squash = (t: string) => t.replace(/\s+/g, '');
  const seen = new Set(slots.map((s) => squash(s.name)));
  const added: string[] = [];
  const duplicates: string[] = [];
  const overflow: string[] = [];
  names.forEach((raw, i) => {
    const name = raw.trim().slice(0, MAX_NAME_LENGTH);
    if (!name) return;
    const key = squash(name);
    if (seen.has(key)) {
      duplicates.push(name);
    } else if (slots.length >= MAX_SLOTS) {
      overflow.push(name);
    } else {
      seen.add(key);
      slots.push({ id: `c-${now}-${i}`, icon: NEW_SLOT_ICON, name });
      added.push(name);
    }
  });
  return { slots, added, duplicates, overflow };
}
