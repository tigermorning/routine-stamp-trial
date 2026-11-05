import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CalendarView } from '@/components/calendar-view';
import { PhotoImport } from '@/components/photo-import';
import { StampBoard } from '@/components/stamp-board';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { type CalendarEvent, loadEvents, saveEvents } from '@/lib/events';
import { DEFAULT_SLOTS, type Slot, loadSlots, saveSlots } from '@/lib/stamps';

type View = 'stamps' | 'calendar';

export default function HomeScreen() {
  const [view, setView] = useState<View>('stamps');
  const [slots, setSlots] = useState<readonly Slot[]>(DEFAULT_SLOTS);
  const [events, setEvents] = useState<readonly CalendarEvent[]>([]);

  useEffect(() => {
    loadSlots().then(setSlots);
    loadEvents().then(setEvents);
  }, []);

  function changeSlots(next: Slot[]) {
    setSlots(next);
    saveSlots(next).catch(() => {});
  }

  function changeEvents(next: CalendarEvent[]) {
    setEvents(next);
    saveEvents(next).catch(() => {});
  }

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          automaticallyAdjustKeyboardInsets>
          <ThemedView style={styles.header}>
            <ThemedText type="title">루틴 도장</ThemedText>
            <ThemedText themeColor="textSecondary">
              {view === 'stamps'
                ? '오늘 한 만큼만 찍어요. 칸을 누를 때마다 도장이 바뀌어요.'
                : '날짜를 눌러 그날의 루틴과 일정을 봐요.'}
            </ThemedText>
          </ThemedView>

          <ThemedView style={styles.switcher}>
            {(['stamps', 'calendar'] as const).map((v) => (
              <Pressable
                key={v}
                onPress={() => setView(v)}
                style={[styles.tab, view === v && styles.tabOn]}
                accessibilityRole="button"
                accessibilityState={{ selected: view === v }}>
                <ThemedText style={view === v && styles.tabOnText}>{v === 'stamps' ? '도장' : '캘린더'}</ThemedText>
              </Pressable>
            ))}
          </ThemedView>

          {view === 'stamps' ? (
            <>
              <StampBoard slots={slots} />
              <ThemedText type="small" themeColor="textSecondary" style={styles.footer}>
                진한 도장 → 연한 도장 → 비움 순서로 바뀌어요. 놓쳐도 쌓인 것은 그대로예요.
              </ThemedText>
            </>
          ) : (
            <>
              <CalendarView slots={slots} events={events} onEventsChange={changeEvents} />
              <PhotoImport slots={slots} onSlotsChange={changeSlots} events={events} onEventsChange={changeEvents} />
            </>
          )}
        </ScrollView>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    flexDirection: 'row',
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: Spacing.four,
    maxWidth: MaxContentWidth,
  },
  content: {
    paddingTop: Spacing.five,
    gap: Spacing.four,
    paddingBottom: BottomTabInset + Spacing.five,
  },
  header: {
    gap: Spacing.two,
  },
  switcher: {
    flexDirection: 'row',
    gap: Spacing.two,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: Spacing.two,
    borderRadius: Spacing.three,
    backgroundColor: '#E0E1E6',
  },
  tabOn: {
    backgroundColor: '#D93D42',
  },
  tabOnText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  footer: {
    textAlign: 'center',
  },
});
