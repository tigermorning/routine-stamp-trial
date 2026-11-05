import { useState } from 'react';
import { Alert, Pressable, StyleSheet, TextInput } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import {
  type CalendarEvent,
  dDayLabel,
  dateKey,
  eventsOn,
  monthCells,
  normalizeDateKey,
  parseTimeInput,
  weekdayOf,
} from '@/lib/events';
import { describe, isDueOn } from '@/lib/schedule';
import type { Slot } from '@/lib/stamps';

const WEEK = ['일', '월', '화', '수', '목', '금', '토'];

type Props = {
  slots: readonly Slot[];
  events: readonly CalendarEvent[];
  onEventsChange: (events: CalendarEvent[]) => void;
};

type Draft = { id?: string; title: string; date: string; time: string };

/** 월 달력. 날짜를 누르면 그날의 루틴·일정이 보이고, 일정을 직접 추가·수정·삭제·완료 표시할 수 있다. */
export function CalendarView({ slots, events, onEventsChange }: Props) {
  const todayKey = dateKey(new Date());
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth());
  const [selected, setSelected] = useState(todayKey);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState('');

  function moveMonth(delta: number) {
    const d = new Date(year, month + delta, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth());
  }

  function goToday() {
    const now = new Date();
    setYear(now.getFullYear());
    setMonth(now.getMonth());
    setSelected(dateKey(now));
  }

  function startAdd() {
    setError('');
    setDraft({ title: '', date: selected, time: '' });
  }

  function startEdit(e: CalendarEvent) {
    setError('');
    setDraft({ id: e.id, title: e.title, date: e.date, time: e.time ?? '' });
  }

  function save() {
    if (!draft) return;
    const title = draft.title.trim();
    const date = normalizeDateKey(draft.date);
    const time = parseTimeInput(draft.time);
    if (!title) return setError('제목을 입력해 주세요.');
    if (!date) return setError('날짜는 2026-11-07 꼴로 입력해 주세요.');
    if (time === null) return setError('시간은 10:30 꼴로 입력하거나 비워 두세요.');
    const next: CalendarEvent[] = draft.id
      ? events.map((e) => (e.id === draft.id ? { ...e, title, date, time } : e))
      : [...events, { id: `e-${Date.now()}`, title, date, time }];
    onEventsChange(next);
    setSelected(date);
    const d = new Date(Number(date.slice(0, 4)), Number(date.slice(5, 7)) - 1, 1);
    setYear(d.getFullYear());
    setMonth(d.getMonth());
    setDraft(null);
    setError('');
  }

  function remove(e: CalendarEvent) {
    Alert.alert('일정 지우기', `«${e.title}»을(를) 지울까요?`, [
      { text: '지우기', style: 'destructive', onPress: () => onEventsChange(events.filter((x) => x.id !== e.id)) },
      { text: '취소', style: 'cancel' },
    ]);
  }

  function toggleDone(e: CalendarEvent) {
    onEventsChange(events.map((x) => (x.id === e.id ? { ...x, done: !x.done } : x)));
  }

  const cells = monthCells(year, month);
  const dayEvents = eventsOn(events, selected);
  const weekday = weekdayOf(selected);
  const dayRoutines = slots.filter((s) => isDueOn(s, weekday));
  const countOf = (key: string) => events.filter((e) => e.date === key).length;

  return (
    <ThemedView style={styles.wrap}>
      <ThemedView style={styles.monthRow}>
        <Pressable onPress={() => moveMonth(-1)} style={styles.nav} accessibilityRole="button" accessibilityLabel="이전 달">
          <ThemedText type="subtitle">◀</ThemedText>
        </Pressable>
        <ThemedText type="subtitle">
          {year}년 {month + 1}월
        </ThemedText>
        <Pressable onPress={() => moveMonth(1)} style={styles.nav} accessibilityRole="button" accessibilityLabel="다음 달">
          <ThemedText type="subtitle">▶</ThemedText>
        </Pressable>
        <Pressable onPress={goToday} style={styles.todayBtn} accessibilityRole="button">
          <ThemedText type="smallBold">오늘</ThemedText>
        </Pressable>
      </ThemedView>

      <ThemedView style={styles.grid}>
        {WEEK.map((w, i) => (
          <ThemedText key={w} type="smallBold" themeColor="textSecondary" style={[styles.cell, i === 0 && styles.sun, i === 6 && styles.sat]}>
            {w}
          </ThemedText>
        ))}
        {cells.map((key, i) => {
          if (!key) return <ThemedView key={`b${i}`} style={styles.cell} />;
          const n = countOf(key);
          return (
            <Pressable
              key={key}
              onPress={() => setSelected(key)}
              style={[styles.cell, styles.dayCell, key === todayKey && styles.today, key === selected && styles.selected]}
              accessibilityRole="button"
              accessibilityLabel={`${key} 일정 ${n}개`}>
              <ThemedText style={[i % 7 === 0 && styles.sun, i % 7 === 6 && styles.sat, key === selected && styles.selectedText]}>
                {Number(key.slice(8))}
              </ThemedText>
              <ThemedText style={[styles.dot, key === selected && styles.selectedText]}>
                {n > 1 ? `●${n}` : n === 1 ? '●' : ' '}
              </ThemedText>
            </Pressable>
          );
        })}
      </ThemedView>

      <ThemedView type="backgroundElement" style={styles.panel}>
        <ThemedText type="subtitle">
          {Number(selected.slice(5, 7))}월 {Number(selected.slice(8))}일 ({WEEK[weekday]}) · {dDayLabel(selected)}
        </ThemedText>

        {dayRoutines.length > 0 && (
          <ThemedView style={styles.block} type="backgroundElement">
            <ThemedText type="smallBold" themeColor="textSecondary">
              이날의 루틴
            </ThemedText>
            {dayRoutines.map((s) => (
              <ThemedText key={s.id} type="small">
                {s.icon} {s.name}
                {s.days || s.time ? ` · ${describe(s)}` : ''}
              </ThemedText>
            ))}
          </ThemedView>
        )}

        <ThemedView style={styles.block} type="backgroundElement">
          <ThemedText type="smallBold" themeColor="textSecondary">
            이날의 일정
          </ThemedText>
          {dayEvents.length === 0 && (
            <ThemedText type="small" themeColor="textSecondary">
              일정이 없어요.
            </ThemedText>
          )}
          {dayEvents.map((e) => (
            <ThemedView key={e.id} style={styles.eventRow} type="backgroundElement">
              <Pressable onPress={() => toggleDone(e)} accessibilityRole="button" accessibilityLabel={e.done ? '완료 취소' : '완료로 표시'}>
                <ThemedText style={styles.check}>{e.done ? '☑️' : '⬜'}</ThemedText>
              </Pressable>
              <ThemedView style={styles.eventText} type="backgroundElement">
                <ThemedText style={e.done && styles.doneText}>{e.title}</ThemedText>
                {e.time ? (
                  <ThemedText type="small" themeColor="textSecondary">
                    {e.time}
                  </ThemedText>
                ) : null}
              </ThemedView>
              <Pressable onPress={() => startEdit(e)} style={styles.iconBtn} accessibilityRole="button" accessibilityLabel="일정 고치기">
                <ThemedText>✏️</ThemedText>
              </Pressable>
              <Pressable onPress={() => remove(e)} style={styles.iconBtn} accessibilityRole="button" accessibilityLabel="일정 지우기">
                <ThemedText>🗑️</ThemedText>
              </Pressable>
            </ThemedView>
          ))}
        </ThemedView>

        {draft ? (
          <ThemedView style={styles.block} type="backgroundElement">
            <ThemedText type="smallBold">{draft.id ? '일정 고치기' : '새 일정'}</ThemedText>
            <TextInput
              value={draft.title}
              onChangeText={(title) => setDraft({ ...draft, title })}
              placeholder="제목"
              style={styles.input}
              accessibilityLabel="일정 제목"
            />
            <ThemedView style={styles.eventRow} type="backgroundElement">
              <TextInput
                value={draft.date}
                onChangeText={(date) => setDraft({ ...draft, date })}
                placeholder="2026-11-07"
                autoCapitalize="none"
                style={[styles.input, styles.half]}
                accessibilityLabel="일정 날짜"
              />
              <TextInput
                value={draft.time}
                onChangeText={(time) => setDraft({ ...draft, time })}
                placeholder="10:30 (선택)"
                autoCapitalize="none"
                style={[styles.input, styles.half]}
                accessibilityLabel="일정 시간"
              />
            </ThemedView>
            {error !== '' && <ThemedText type="small" style={styles.error}>{error}</ThemedText>}
            <ThemedView style={styles.eventRow} type="backgroundElement">
              <Pressable onPress={save} style={[styles.btn, styles.primary]} accessibilityRole="button">
                <ThemedText style={styles.primaryText}>저장</ThemedText>
              </Pressable>
              <Pressable onPress={() => setDraft(null)} style={styles.btn} accessibilityRole="button">
                <ThemedText>취소</ThemedText>
              </Pressable>
            </ThemedView>
          </ThemedView>
        ) : (
          <Pressable onPress={startAdd} style={[styles.btn, styles.primary]} accessibilityRole="button">
            <ThemedText style={styles.primaryText}>＋ 이 날 일정 추가</ThemedText>
          </Pressable>
        )}
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: Spacing.three },
  monthRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  nav: { padding: Spacing.two },
  todayBtn: { paddingHorizontal: Spacing.three, paddingVertical: Spacing.two, borderRadius: Spacing.three, backgroundColor: '#E0E1E6' },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: '14.2857%', alignItems: 'center', paddingVertical: Spacing.one, textAlign: 'center' },
  dayCell: { borderRadius: Spacing.two, minHeight: 52 },
  today: { borderWidth: 2, borderColor: '#D93D42' },
  selected: { backgroundColor: '#D93D42' },
  selectedText: { color: '#FFFFFF', fontWeight: '700' },
  sun: { color: '#D93D42' },
  sat: { color: '#2F6FE4' },
  dot: { fontSize: 10, lineHeight: 14, color: '#D93D42' },
  panel: { borderRadius: Spacing.four, padding: Spacing.three, gap: Spacing.three },
  block: { gap: Spacing.one },
  eventRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.two },
  eventText: { flex: 1 },
  check: { fontSize: 24, lineHeight: 30 },
  doneText: { textDecorationLine: 'line-through', opacity: 0.5 },
  iconBtn: { padding: Spacing.two },
  input: {
    backgroundColor: '#FFFFFF',
    color: '#000000',
    borderRadius: Spacing.two,
    borderWidth: 1,
    borderColor: '#C9CCD3',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 16,
  },
  half: { flex: 1 },
  btn: { flex: 1, alignItems: 'center', paddingVertical: Spacing.three, borderRadius: Spacing.three, backgroundColor: '#E0E1E6' },
  primary: { backgroundColor: '#D93D42' },
  primaryText: { color: '#FFFFFF', fontWeight: '700' },
  error: { color: '#D93D42' },
});
