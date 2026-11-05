import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PhotoImport } from '@/components/photo-import';
import { StampBoard } from '@/components/stamp-board';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { BottomTabInset, MaxContentWidth, Spacing } from '@/constants/theme';
import { DEFAULT_SLOTS, type Slot, loadSlots, saveSlots } from '@/lib/stamps';

export default function HomeScreen() {
  const [slots, setSlots] = useState<readonly Slot[]>(DEFAULT_SLOTS);

  useEffect(() => {
    loadSlots().then(setSlots);
  }, []);

  function changeSlots(next: Slot[]) {
    setSlots(next);
    saveSlots(next).catch(() => {});
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
              오늘 한 만큼만 찍어요. 칸을 누를 때마다 도장이 바뀌어요.
            </ThemedText>
          </ThemedView>

          <StampBoard slots={slots} />

          <ThemedText type="small" themeColor="textSecondary" style={styles.footer}>
            진한 도장 → 연한 도장 → 비움 순서로 바뀌어요. 놓쳐도 쌓인 것은 그대로예요.
          </ThemedText>

          <PhotoImport slots={slots} onSlotsChange={changeSlots} />

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
  footer: {
    textAlign: 'center',
  },
});
