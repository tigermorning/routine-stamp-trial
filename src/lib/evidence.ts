import AsyncStorage from '@react-native-async-storage/async-storage';
import { Directory, File, Paths } from 'expo-file-system';

/** 한 칸·하루의 증거: 사진 파일 주소(폰 안)와 메모 */
export type Evidence = { uri?: string; note: string };

/** 날짜(YYYY-MM-DD) → 칸 id → 증거. 도장 기록(routine-stamp:v1)과는 따로 저장해서 이전 데이터에 영향이 없다. */
export type EvidenceLog = Record<string, Record<string, Evidence>>;

const KEY = 'routine-stamp:evidence:v1';
const DIR_NAME = 'evidence';

export async function loadEvidence(): Promise<EvidenceLog> {
  try {
    const raw = await AsyncStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as EvidenceLog) : {};
  } catch {
    return {};
  }
}

export async function saveEvidence(log: EvidenceLog): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(log));
}

/** 선택기가 준 임시 사진을 앱의 문서 폴더로 복사해 영구 보관한다(임시 폴더는 운영체제가 지울 수 있다). */
export function keepPhoto(tempUri: string, date: string, slotId: string): string {
  const dir = new Directory(Paths.document, DIR_NAME);
  if (!dir.exists) dir.create({ intermediates: true });
  const dest = new File(dir, `${date}-${slotId}-${Date.now()}.jpg`);
  new File(tempUri).copy(dest);
  return dest.uri;
}

/** 보관한 사진 파일을 지운다. 이미 없거나 실패해도 앱은 멈추지 않는다. */
export function discardPhoto(uri: string | undefined): void {
  if (!uri) return;
  try {
    const file = new File(uri);
    if (file.exists) file.delete();
  } catch {
    // 파일을 못 지워도 기록만 지우면 된다
  }
}
