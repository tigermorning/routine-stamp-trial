import * as ImagePicker from 'expo-image-picker';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Linking, Pressable, StyleSheet, TextInput } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { type CalendarEvent, addEvents, describeEvent, hasDate, parseEvents } from '@/lib/events';
import { loadServerUrl, readPhoto, saveServerUrl } from '@/lib/ocr';
import { applySchedule, describe, parseLine, parseSchedule } from '@/lib/schedule';
import { MAX_SLOTS, type Slot } from '@/lib/stamps';

type Props = {
  slots: readonly Slot[];
  /** 새 칸 목록을 화면·저장소에 반영한다 */
  onSlotsChange: (slots: Slot[]) => void;
  events: readonly CalendarEvent[];
  /** 날짜가 있는 일정을 반영한다 */
  onEventsChange: (events: CalendarEvent[]) => void;
};

type Source = 'library' | 'camera';

/**
 * 주간 루틴표 사진(손글씨·인쇄물) → 서버에서 글자 읽기 → 줄마다 «칸 이름 + 요일 + 시간»으로 풀어 보여 줌
 * → 사용자가 확인·수정·삭제 → «루틴표 반영»을 눌러야 칸에 들어간다. 읽은 글을 바로 반영하지 않는다.
 */
export function PhotoImport({ slots, onSlotsChange, events, onEventsChange }: Props) {
  const [serverUrl, setServerUrl] = useState('');
  useEffect(() => {
    loadServerUrl().then(setServerUrl);
  }, []);
  const [rows, setRows] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [needSettings, setNeedSettings] = useState(false);

  async function pick(source: Source) {
    setMessage('');
    setNeedSettings(false);
    // 사진을 고르기 전에 서버 주소부터 확인한다(주소가 없으면 읽어도 올릴 곳이 없다)
    if (!serverUrl.trim()) {
      setMessage('먼저 위의 «글자 읽기 서버 주소» 칸에 노트북 주소를 입력해 주세요. 예: 192.168.0.10:8898');
      return;
    }
    const perm =
      source === 'camera'
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      setNeedSettings(!perm.canAskAgain);
      setMessage(
        source === 'camera'
          ? '카메라 권한이 없어 사진을 찍을 수 없어요. 권한을 허용하거나 사진첩에서 골라 주세요.'
          : '사진 접근 권한이 없어 사진을 고를 수 없어요. 권한을 허용하면 다시 시도할 수 있어요.',
      );
      return;
    }
    try {
      const options: ImagePicker.ImagePickerOptions = { mediaTypes: ['images'], quality: 0.8 };
      const result =
        source === 'camera'
          ? await ImagePicker.launchCameraAsync(options)
          : await ImagePicker.launchImageLibraryAsync(options);
      if (result.canceled || result.assets.length === 0) return;

      setBusy(true);
      setMessage('글자를 읽는 중이에요…');
      await saveServerUrl(serverUrl).catch(() => {});
      const lines = await readPhoto(serverUrl, result.assets[0].uri, result.assets[0].mimeType);
      setRows(lines);
      setMessage(
        lines.length > 0
          ? `${lines.length}줄을 읽었어요. 틀린 글자는 고치고, 필요 없는 줄은 지운 뒤 «루틴표 반영»을 눌러 주세요.`
          : '읽은 글이 없어요. 더 밝고 또렷한 사진으로 다시 시도해 보세요.',
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '글자를 읽지 못했어요.');
    } finally {
      setBusy(false);
    }
  }

  // 읽은 줄에 날짜(«11월 7일», «2026-03-24» 등)가 있으면 날짜 일정, 없으면 주간 루틴표로 본다
  const eventMode = hasDate(rows);
  const drafts = eventMode ? parseEvents(rows) : [];

  function confirmEvents() {
    const result = addEvents(events, drafts);
    if (result.added > 0) onEventsChange(result.events);
    const parts: string[] = [];
    if (result.added > 0) parts.push(`${result.added}개 일정을 캘린더에 넣었어요.`);
    if (result.duplicates > 0) parts.push(`같은 일정 ${result.duplicates}개는 건너뛰었어요.`);
    if (result.skipped > 0) parts.push(`날짜를 못 찾은 ${result.skipped}개는 넣지 못했어요. 날짜(예: 11월 7일)를 줄에 적어 주세요.`);
    if (parts.length === 0) parts.push('넣을 일정이 없어요.');
    setMessage(parts.join(' '));
    if (result.skipped === 0) setRows([]);
  }

  function confirm() {
    if (eventMode) return confirmEvents();
    const items = parseSchedule(rows);
    const result = applySchedule(slots, items);
    onSlotsChange(result.slots);
    const parts: string[] = [];
    if (result.added.length > 0) parts.push(`${result.added.length}칸을 새로 넣었어요.`);
    if (result.updated.length > 0) parts.push(`${result.updated.length}칸의 요일·시간을 바꿨어요.`);
    if (result.overflow.length > 0) parts.push(`칸은 최대 ${MAX_SLOTS}개라 ${result.overflow.length}개는 넣지 못했어요.`);
    if (parts.length === 0) parts.push('반영할 항목이 없어요.');
    setMessage(parts.join(' '));
    // 넣지 못한 항목만 남겨 두어 고쳐서 다시 시도할 수 있게 한다
    setRows(rows.filter((row) => result.overflow.includes(parseLine(row)?.name ?? '')));
  }

  return (
    <ThemedView type="backgroundElement" style={styles.box}>
      <ThemedText type="subtitle">사진에서 일정 가져오기</ThemedText>
      <ThemedText type="small" themeColor="textSecondary">
        손으로 쓴 «11월 7일 오전 10시 30분 미용실 예약» 같은 메모는 캘린더 일정으로, «월수금 07:00 스트레칭» 같은 루틴표는 칸의 요일·시간으로
        옮겨요. 읽은 글은 확인한 뒤에만 반영돼요. (칸 {slots.length}/{MAX_SLOTS})
      </ThemedText>

      <ThemedText type="smallBold">글자 읽기 서버 주소</ThemedText>
      <TextInput
        value={serverUrl}
        onChangeText={setServerUrl}
        placeholder="예: 192.168.0.10:8898"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        style={styles.input}
        accessibilityLabel="글자 읽기 서버 주소"
      />

      <ThemedView style={styles.row} type="backgroundElement">
        <Pressable onPress={() => pick('library')} disabled={busy} style={[styles.button, busy && styles.disabled]} accessibilityRole="button">
          <ThemedText style={styles.buttonText}>사진첩에서 고르기</ThemedText>
        </Pressable>
        <Pressable onPress={() => pick('camera')} disabled={busy} style={[styles.button, busy && styles.disabled]} accessibilityRole="button">
          <ThemedText style={styles.buttonText}>카메라로 찍기</ThemedText>
        </Pressable>
      </ThemedView>

      {busy && <ActivityIndicator />}
      {message !== '' && <ThemedText type="small">{message}</ThemedText>}
      {needSettings && (
        <Pressable onPress={() => Linking.openSettings().catch(() => {})} accessibilityRole="button">
          <ThemedText type="link">설정에서 권한 열기</ThemedText>
        </Pressable>
      )}

      {eventMode && (
        <ThemedView style={styles.rowBox} type="backgroundElement">
          <ThemedText type="smallBold">날짜 일정으로 읽었어요</ThemedText>
          {drafts.map((d, i) => (
            <ThemedText key={i} type="small">
              📅 {describeEvent(d)} · {d.title}
              {d.date ? '' : '  (날짜를 못 찾았어요)'}
            </ThemedText>
          ))}
        </ThemedView>
      )}

      {rows.map((row, index) => {
        const parsed = eventMode ? null : parseLine(row);
        return (
          <ThemedView key={index} style={styles.rowBox} type="backgroundElement">
            <ThemedView style={styles.row} type="backgroundElement">
              <TextInput
                value={row}
                onChangeText={(text) => setRows((prev) => prev.map((t, i) => (i === index ? text : t)))}
                style={[styles.input, styles.itemInput]}
                accessibilityLabel={`읽은 줄 ${index + 1}`}
              />
              <Pressable
                onPress={() => setRows((prev) => prev.filter((_, i) => i !== index))}
                style={styles.delete}
                accessibilityRole="button"
                accessibilityLabel="이 줄 지우기">
                <ThemedText>🗑️</ThemedText>
              </Pressable>
            </ThemedView>
            {eventMode ? null : (
              <ThemedText type="small" themeColor="textSecondary">
                {parsed ? `→ ${parsed.name} · ${describe(parsed)}` : '→ 칸 이름을 알 수 없어 건너뛰어요'}
              </ThemedText>
            )}
          </ThemedView>
        );
      })}

      {rows.length > 0 && (
        <Pressable onPress={confirm} style={[styles.button, styles.primary]} accessibilityRole="button">
          <ThemedText style={styles.primaryText}>
            {eventMode ? `캘린더에 일정 넣기 (${drafts.length}개)` : `루틴표 반영 (${rows.length}줄)`}
          </ThemedText>
        </Pressable>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  box: { borderRadius: Spacing.four, padding: Spacing.three, gap: Spacing.two },
  row: { flexDirection: 'row', gap: Spacing.two, alignItems: 'center' },
  rowBox: { gap: Spacing.one },
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
  itemInput: { flex: 1 },
  button: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: Spacing.three,
    borderRadius: Spacing.three,
    backgroundColor: '#E0E1E6',
  },
  buttonText: { fontWeight: '600' },
  primary: { backgroundColor: '#D93D42', flex: 0 },
  primaryText: { color: '#FFFFFF', fontWeight: '700' },
  disabled: { opacity: 0.5 },
  delete: { padding: Spacing.two },
});
