import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import { Alert, Image, Linking, Pressable, StyleSheet, TextInput } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { type Evidence, discardPhoto, keepPhoto } from '@/lib/evidence';

type Props = {
  date: string;
  slotId: string;
  evidence: Evidence | undefined;
  onChange: (next: Evidence | undefined) => void;
};

type Source = 'library' | 'camera';

/** 칸 안의 증거 사진·메모. 손글씨 읽기는 서버가 켜져 있을 때만 되고, 읽은 글은 메모 칸에 채워지며 사람이 고친다. */
export function SlotEvidence({ date, slotId, evidence, onChange }: Props) {
  const [message, setMessage] = useState('');
  const [needSettings, setNeedSettings] = useState(false);
  const note = evidence?.note ?? '';
  const uri = evidence?.uri;

  async function pick(source: Source) {
    setMessage('');
    setNeedSettings(false);
    // 권한을 거부해도 앱이 멈추지 않고 안내한다
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
      const saved = keepPhoto(result.assets[0].uri, date, slotId);
      discardPhoto(uri);
      onChange({ uri: saved, note });
    } catch {
      setMessage('사진을 저장하지 못했어요. 다시 시도해 주세요.');
    }
  }

  function choose() {
    Alert.alert('증거 사진', '오늘 한 일을 사진으로 남겨요.', [
      { text: '카메라로 찍기', onPress: () => pick('camera') },
      { text: '사진첩에서 고르기', onPress: () => pick('library') },
      { text: '취소', style: 'cancel' },
    ]);
  }

  function removePhoto() {
    discardPhoto(uri);
    onChange(note ? { note } : undefined);
  }

  return (
    <ThemedView style={styles.box}>
      <ThemedView style={styles.row}>
        {uri ? <Image source={{ uri }} style={styles.thumb} accessibilityLabel="증거 사진" /> : null}
        <ThemedView style={styles.buttons}>
          <Pressable onPress={choose} style={styles.btn} accessibilityRole="button">
            <ThemedText type="small">{uri ? '📷 사진 바꾸기' : '📷 증거 사진 넣기'}</ThemedText>
          </Pressable>
          {uri ? (
            <>
              <Pressable onPress={removePhoto} style={styles.btn} accessibilityRole="button">
                <ThemedText type="small">🗑️ 사진 지우기</ThemedText>
              </Pressable>
            </>
          ) : null}
        </ThemedView>
      </ThemedView>

      <TextInput
        value={note}
        onChangeText={(text) => {
          const next = { uri, note: text };
          onChange(!next.uri && !text ? undefined : next);
        }}
        placeholder="오늘 메모"
        multiline
        style={styles.input}
        accessibilityLabel="오늘 메모"
      />

      {message !== '' && <ThemedText type="small" themeColor="textSecondary">{message}</ThemedText>}
      {needSettings && (
        <Pressable onPress={() => Linking.openSettings().catch(() => {})} accessibilityRole="button">
          <ThemedText type="link">설정에서 권한 열기</ThemedText>
        </Pressable>
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  box: { gap: Spacing.two, backgroundColor: 'transparent' },
  row: { flexDirection: 'row', gap: Spacing.three, alignItems: 'center', backgroundColor: 'transparent' },
  buttons: { flex: 1, gap: Spacing.one, backgroundColor: 'transparent' },
  thumb: { width: 96, height: 96, borderRadius: Spacing.two, backgroundColor: '#E0E1E6' },
  btn: {
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.three,
    borderRadius: Spacing.two,
    backgroundColor: '#E0E1E6',
  },
  dim: { opacity: 0.5 },
  input: {
    backgroundColor: '#FFFFFF',
    color: '#000000',
    borderRadius: Spacing.two,
    borderWidth: 1,
    borderColor: '#C9CCD3',
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 16,
    minHeight: 44,
  },
});
