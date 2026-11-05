import AsyncStorage from '@react-native-async-storage/async-storage';
import { File } from 'expo-file-system';

/** 서버 주소 저장 키. 하드코딩하지 않고 화면에서 바꿀 수 있게 한다. */
const SERVER_KEY = 'routine-stamp:ocr-server:v1';
const TIMEOUT_MS = 60_000;

/** 기본 주소: .env 의 EXPO_PUBLIC_OCR_SERVER_URL (없으면 빈 칸 → 사용자가 입력) */
const ENV_DEFAULT = process.env.EXPO_PUBLIC_OCR_SERVER_URL ?? '';

/** 입력을 http://주소:포트 꼴로 다듬는다. 비면 빈 문자열. */
export function normalizeServerUrl(input: string): string {
  const trimmed = input.trim().replace(/\/+$/, '');
  if (!trimmed) return '';
  return /^https?:\/\//i.test(trimmed) ? trimmed : `http://${trimmed}`;
}

export async function loadServerUrl(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(SERVER_KEY);
    if (saved) return saved;
  } catch {
    // 읽지 못하면 기본값을 쓴다
  }
  return normalizeServerUrl(ENV_DEFAULT);
}

export async function saveServerUrl(url: string): Promise<void> {
  await AsyncStorage.setItem(SERVER_KEY, normalizeServerUrl(url));
}

/** 서버가 돌려준 text(줄바꿈으로 이은 글)를 줄 목록으로 */
export function textToLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

/** 사진을 서버 POST /api/ocr 에 올려 읽은 줄 목록을 받는다. 실패하면 사람이 읽을 수 있는 메시지로 던진다. */
export async function readPhoto(serverUrl: string, uri: string, mimeType?: string): Promise<string[]> {
  const base = normalizeServerUrl(serverUrl);
  if (!base) throw new Error('서버 주소를 먼저 입력해 주세요.');

  const form = new FormData();
  // 이 Expo 버전의 fetch 는 {uri, name, type} 꼴을 지원하지 않는다(Unsupported FormDataPart implementation).
  // bytes() 를 가진 expo-file-system 의 File 을 넣는다. 형식(JPEG·HEIC 등)은 서버가 내용으로 알아본다.
  void mimeType;
  form.append('photo', new File(uri));

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${base}/api/ocr`, { method: 'POST', body: form, signal: controller.signal });
    if (res.status === 404) throw new Error('서버의 글자 읽기가 꺼져 있어요. (OCR_ENABLED=true 로 실행했는지 확인)');
    if (!res.ok) throw new Error(`서버가 오류를 돌려줬어요 (${res.status}).`);
    const data = (await res.json()) as { text?: string };
    return textToLines(data.text ?? '');
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('서버가 60초 안에 답하지 않았어요. 주소·와이파이를 확인해 주세요.');
    }
    if (error instanceof TypeError) {
      throw new Error('서버에 연결하지 못했어요. 폰과 노트북이 같은 와이파이인지, 주소·방화벽을 확인해 주세요.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
