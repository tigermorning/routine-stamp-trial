import { useEffect, useState } from 'react';
import { StyleSheet, TextInput } from 'react-native';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { loadServerUrl, saveServerUrl } from '@/lib/ocr';

/** 손글씨 읽기 서버 주소 설정. 하드코딩하지 않고 여기서 바꾼다. */
export function ServerSetting() {
  const [url, setUrl] = useState('');

  useEffect(() => {
    loadServerUrl().then(setUrl);
  }, []);

  return (
    <ThemedView style={styles.box}>
      <ThemedText type="smallBold">손글씨 읽기 서버 주소</ThemedText>
      <TextInput
        value={url}
        onChangeText={(text) => {
          setUrl(text);
          saveServerUrl(text).catch(() => {});
        }}
        placeholder="예: 192.168.0.10:8898"
        autoCapitalize="none"
        autoCorrect={false}
        keyboardType="url"
        style={styles.input}
        accessibilityLabel="손글씨 읽기 서버 주소"
      />
      <ThemedText type="small" themeColor="textSecondary">
        칸의 «손글씨 읽어 메모에 넣기»가 이 서버를 불러요. 같은 와이파이의 노트북 주소를 넣어 주세요.
      </ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  box: { gap: Spacing.two },
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
});
