import * as Haptics from 'expo-haptics';
import { useEffect, useState } from 'react';
import { Platform, Pressable, StyleSheet } from 'react-native';

import { SlotEvidence } from '@/components/slot-evidence';
import { ThemedText } from '@/components/themed-text';
import { describe, isDueOn } from '@/lib/schedule';
import { type Evidence, type EvidenceLog, loadEvidence, saveEvidence } from '@/lib/evidence';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import {
  type Slot,
  type StampLevel,
  type StampLog,
  countDays,
  loadLog,
  nextLevel,
  saveLog,
  todayKey,
} from '@/lib/stamps';

/** 도장 단계별 진동: 진한 도장은 묵직하게, 연한 도장은 가볍게, 비울 때는 짧게 */
function buzz(level: StampLevel) {
  if (Platform.OS === 'web') return;
  const run =
    level === 2
      ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy)
      : level === 1
        ? Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)
        : Haptics.selectionAsync();
  // 진동이 안 되는 기기에서도 도장 찍기는 멈추지 않게 한다
  run.catch(() => {});
}

const LEVEL_LABEL: Record<StampLevel, string> = {
  0: '아직',
  1: '조금만 했어요',
  2: '다 했어요',
};

export function StampBoard({ slots }: { slots: readonly Slot[] }) {
  const [log, setLog] = useState<StampLog>({});
  const [loaded, setLoaded] = useState(false);
  const today = todayKey();

  useEffect(() => {
    loadLog().then((saved) => {
      setLog(saved);
      setLoaded(true);
    });
  }, []);

  // 요일이 정해진 칸은 그 요일에만 보인다. 일정이 없는 칸은 매일 보인다.
  const [showAll, setShowAll] = useState(false);
  const weekday = new Date().getDay();
  const dueSlots = slots.filter((s) => isDueOn(s, weekday));
  const visible = showAll ? slots : dueSlots;
  const hiddenCount = slots.length - dueSlots.length;

  const [evidence, setEvidence] = useState<EvidenceLog>({});
  useEffect(() => {
    loadEvidence().then(setEvidence);
  }, []);

  function changeEvidence(slotId: string, next: Evidence | undefined) {
    const day = { ...evidence[today] };
    if (next) day[slotId] = next;
    else delete day[slotId];
    const updated: EvidenceLog = { ...evidence, [today]: day };
    setEvidence(updated);
    saveEvidence(updated).catch(() => {});
  }

  function press(slotId: string) {
    const current: StampLevel = log[today]?.[slotId] ?? 0;
    const next = nextLevel(current);
    buzz(next);
    const updated: StampLog = { ...log, [today]: { ...log[today], [slotId]: next } };
    setLog(updated);
    saveLog(updated).catch(() => {});
  }

  return (
    <ThemedView style={styles.board}>
      {hiddenCount > 0 || showAll ? (
        <Pressable onPress={() => setShowAll((v) => !v)} accessibilityRole="button">
          <ThemedText type="link">
            {showAll ? '오늘 할 것만 보기' : `오늘 할 일이 아닌 ${hiddenCount}칸 숨김 · 전체 보기`}
          </ThemedText>
        </Pressable>
      ) : null}
      {visible.map((slot) => {
        const level: StampLevel = log[today]?.[slot.id] ?? 0;
        const days = countDays(log, slot.id);
        return (
          <ThemedView
            key={slot.id}
            style={[styles.card, level === 2 && styles.slotStrong, level === 1 && styles.slotLight]}>
          <Pressable
            onPress={() => press(slot.id)}
            disabled={!loaded}
            accessibilityRole="button"
            accessibilityLabel={`${slot.name}, 오늘 ${LEVEL_LABEL[level]}`}
            style={({ pressed }) => [styles.slot, pressed && styles.slotPressed]}>
            <ThemedText style={styles.icon}>{slot.icon}</ThemedText>
            <ThemedView style={styles.slotText} type="backgroundElement">
              <ThemedText type="subtitle" style={styles.slotName}>
                {slot.name}
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                {slot.days || slot.time ? `${describe(slot)} · ` : ''}오늘 {LEVEL_LABEL[level]} · 누적 {days}일
              </ThemedText>
            </ThemedView>
            <ThemedText style={styles.stamp}>{level === 2 ? '🟥' : level === 1 ? '🩷' : '⬜'}</ThemedText>
          </Pressable>
            <SlotEvidence
              date={today}
              slotId={slot.id}
              evidence={evidence[today]?.[slot.id]}
              onChange={(next) => changeEvidence(slot.id, next)}
            />
          </ThemedView>
        );
      })}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  board: {
    alignSelf: 'stretch',
    gap: Spacing.three,
  },
  card: {
    padding: Spacing.three,
    gap: Spacing.three,
    borderRadius: Spacing.four,
    borderWidth: 2,
    borderColor: 'transparent',
    backgroundColor: '#F0F0F3',
  },
  slot: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.three,
  },
  slotStrong: {
    borderColor: '#D93D42',
    backgroundColor: '#FFE9E9',
  },
  slotLight: {
    borderColor: '#F2A5B8',
    backgroundColor: '#FFF3F6',
  },
  slotPressed: {
    opacity: 0.7,
  },
  icon: {
    fontSize: 32,
    lineHeight: 40,
  },
  slotText: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  slotName: {
    fontSize: 22,
    lineHeight: 30,
  },
  stamp: {
    fontSize: 28,
    lineHeight: 36,
  },
});
