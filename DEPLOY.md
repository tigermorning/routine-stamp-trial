# 배포 (Cloud Run: routine-coach)

배포 작업이면 이 문서를 먼저 읽는다. 실행은 `./deploy.sh`(기본은 배포 없이 점검·스냅샷만, `--deploy`를 붙여야 올린다).
표의 "이유"는 근거가 있는 것만 적었고, 기록이 없는 칸은 그렇게 표시했다. 값은 2026-10-21에 `gcloud run services describe routine-coach` 로 확인했다.

## 배포 전 점검 목록
`deploy.sh`가 자동으로 하는 것은 ⚙, 사람이 확인하는 것은 ☐.

- ⚙ 올릴 파일이 있다(`index.html`, `Procfile`, `requirements.txt`, `.gcloudignore`, `server/`)
- ⚙ gcloud 계정·프로젝트·리전이 맞다
- ⚙ Secret Manager 에 `llm-api-key`, `feedback-smtp-password` 가 있다(값은 읽지 않는다)
- ⚙ 서버 시험 통과(`cd server && python -m pytest tests`)
- ⚙ 화면 스크립트 문법 통과
- ⚙ `STAMP_TOOLS` 를 주면 화면 시험 5종 통과(unlock·settings·routine·del·chat). 시험 스크립트는 저장소 밖(`stamp-app-tools`)에 있다
- ☐ 다른 세션이 이 폴더 파일을 고치는 중이 아니다(스냅샷은 복사 시점의 파일을 올린다)
- ☐ 지금 서비스 중인 리비전 이름을 적어 뒀다(스크립트가 출력한다). 되돌릴 때 필요하다
- ☐ 키·비밀번호를 코드나 문서에 넣지 않았다
- ☐ 설정값을 바꾸는 배포라면 아래 표의 이유 칸을 같이 고쳤다

## 배포 후 확인
- ⚙ 화면 200, `/health` ok. `--smoke-chat` 을 주면 도우미 대화 한 번(모델 비용이 조금 든다)
- ☐ 바뀐 부분을 라이브에서 직접 눌러 확인했다(스크립트는 화면이 뜨는지만 본다)
- ☐ 트래픽이 새 리비전에 100% 인지 확인했다

## 되돌리기
리비전은 남아 있어서 다시 빌드하지 않고 트래픽만 돌린다.
```
gcloud run services update-traffic routine-coach --region us-central1 --project friend-agent-512201 --to-revisions <이전리비전>=100
gcloud run services update-traffic routine-coach --region us-central1 --project friend-agent-512201 --to-latest
```

## 설정값과 이유
| 항목 | 값 | 이유 |
|---|---|---|
| 프로젝트 | friend-agent-512201 | 노드 2에서 만든 프로젝트를 이어서 씀(`HANDOFF-node2.md`) |
| 리전 | us-central1 | 강의자료가 모두 같은 리전을 쓰도록 안내했다(사용자 확인, 자료는 직접 보지 못함) |
| 최대 인스턴스 | 2(리비전 설정). 서비스 쪽 설정에는 3이 따로 보임 | 공개 서비스에 실제 키가 연결돼 있어 한도를 걸기로 했다(`HANDOFF-node2.md`). 서비스 쪽 3과 어느 쪽이 적용되는지는 확인하지 못함 |
| 최소 인스턴스 | 설정 없음(기본 0) | 기본값. 안 쓰면 실행 요금이 없고 대신 오래 비운 뒤 첫 접속이 느리다 |
| CPU / 메모리 | 1 CPU / 512Mi | 기본값으로 보임(friend-agent 와 같음을 확인. 직접 고른 기록은 없음) |
| 동시성 | 80 | 기본값으로 보임(위와 같음). 우리 서버는 모델 응답을 기다리는 시간이 대부분이다 |
| 요청 제한 시간 | 300초 | 최대 인스턴스와 함께 "한도(최대 인스턴스, 타임아웃 등)"로 기록돼 있음(`HANDOFF-node2.md`). 화면은 대화 45초·도장 그림 70초에 포기하므로 서버가 훨씬 넉넉하다 |
| 시작 CPU 부스트 | 켬 | friend-agent 와 같음. 느린 첫 시작을 줄이는 설정 |
| 공개 범위 | 누구나(allUsers) | 로그인 없이 친구들이 써 보는 서비스라서. 방어: IP별·전체 속도 제한, 의견 제출 IP당 분당 3번, 비밀은 Secret Manager |
| 서비스 계정 | 기본 컴퓨트 계정 | 기본값이며 직접 고른 기록은 없다. 전용 계정으로 바꿔 필요한 비밀만 읽게 하는 것이 개선 과제 |
| 환경변수 | `LLM_PROVIDER=openai`, `FEEDBACK_SMTP_USER=tigermorning0@gmail.com` | 운영자 키 방식으로 진행하기로 정했다. 의견 메일을 받을 계정 |
| 비밀 | `llm-api-key` → `LLM_API_KEY`, `feedback-smtp-password` → `FEEDBACK_SMTP_PASSWORD` | 코드·저장소·로그에 값이 남지 않게 한다 |

## 리비전 이력(2026-10-21)
| 리비전 | 바뀐 것 | 이유 |
|---|---|---|
| 00010-scs | 말투 선택지 2개, 도우미가 오늘 칸 상태를 받음 | '기본'이 존댓말과 겹쳤고, "힘들어"에 일반적인 답만 나왔다 |
| 00011-5mg | 오늘 상태를 보고하지 않고 칸 이름으로 되묻도록 규칙 수정 | "도장을 안 찍으셨네요"가 감시처럼 느껴졌다 |
| 00012-269 | 의견 보내기에 mailto 단추 | 복사만 있고 보낼 곳이 없었다 |
| 00013-4js | 제출하기 → 서버가 Gmail 로 발송 | 글을 적고 제출만 누르면 가야 한다는 요청 |

## 알려진 한계
- 속도 제한은 인스턴스 안에서만 센다(인스턴스가 여러 개면 합쳐지지 않는다). 하루 총량 한도는 없다.
- GitHub Pages(`main`)에는 서버가 없어 도우미·제출하기·AI 도장 그림이 실패 안내를 보인다. 공유 주소는 Cloud Run 하나로 쓴다.
