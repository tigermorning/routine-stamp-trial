# 관측과 품질 확인 (Langfuse)

배운 곳: 모두의연구소 «AI 서비스 인 프로덕션» 노드 10(문제 찾기)·11(품질 지키기). 코드는 `server/tracing.py`와 `server/main.py`의 `/api/chat`, 시험은 `server/tests/test_tracing.py`.
이 문서의 «지금 상태»는 2026-11-03에 코드와 시험을 직접 돌려 확인한 것이다. Langfuse 화면(Cloud 프로젝트)은 아직 만들지 않았으므로 화면에서 본 것은 하나도 없다.

## 왜 붙였나

서버 로그에는 `POST /api/chat 200` 만 남고(대화 원문은 남기지 않는 원칙), 도우미가 어느 모드를 골랐는지, 근거 카드를 어느 것으로 골랐는지, 어느 단계가 느렸는지는 알 수 없다. 응답 코드는 200인데 답이 이상한 경우가 이 서비스의 주된 문제 모양이다.
트레이스는 «메시지 하나가 거친 단계»를 한 묶음으로 보여 준다.

## 계측 구조 (한 턴 = 트레이스 하나)

| 단계 | 관찰 단위 이름 | 종류 | 모델을 부르나 | 남기는 것(원문 없이) |
|---|---|---|---|---|
| 한 턴 전체 | `chat-turn` | 트레이스 | – | BYOK 여부, 결과(reply·crisis·scope·key-error), done.ok, 모드, 근거 표시 종류 |
| 위기 키워드 검사 | `safety` | span | 안 부름(코드 규칙) | 위기 여부 |
| 모드·카드 고르기 | `plan-mode` | generation | 부름(짧은 비스트리밍) | 모델 이름, 고른 모드, 실제 카드 id, 모델이 댄 카드 id 수(없는 id를 대면 실제보다 많음) |
| 답 스트리밍 | `reply` | generation | 부름 | 모델 이름, 모드, 첫 글자가 나온 시각, 답 글자 수, `[REFUSED]` 여부 |
| 숫자 검사 | `numbers-check` | span | 안 부름(코드 규칙) | 통과 여부 |

- 나눈 기준은 «고치는 곳이 다른가»다. 엉뚱한 답의 원인이 모드 선택이면 `PLAN_SYSTEM`을, 카드 선택이면 카드 목록을, 답이면 `MODE_RULES`를 고친다(`server/policy.py`).
- 모델을 부르는 단계만 generation으로 남겼다(모델 이름과 토큰이 있어야 비용이 계산되기 때문).
- `/api/stamp`(도장 그림)·`/api/feedback`(메일)은 계측하지 않았다(이번 범위는 대화).

## 정한 것과 이유 (결정)

1. **대화 원문은 기본으로 보내지 않는다.** 이 앱의 개인정보 안내(`index.html`의 privBody, 10개 언어)가 «도우미와 나눈 말은 이 앱 서버에 저장되지 않아요»라고 약속하고 있고, 원문을 외부 관측 도구로 보내면 그 문장이 거짓이 된다. 그래서 단계 구조·모드·카드 id·글자 수·시간만 남긴다.
   - 원문이 필요하면 `LANGFUSE_CAPTURE_TEXT=on`. 그러면 보내기 전에 전화번호·이메일·카드 번호 모양을 가린다(`tracing.mask`). 켜기 전에 개인정보 안내 문구와 보관 기간(Hobby 플랜 30일)을 먼저 고친다.
   - 버린 대안: 원문을 켜 두고 마스킹만 믿기 → 패턴 밖의 개인정보(이름·주소 등)는 못 가리므로 약속과 어긋난다.
2. **키가 없으면 완전히 꺼진다.** `LANGFUSE_PUBLIC_KEY`·`LANGFUSE_SECRET_KEY`가 둘 다 있을 때만 켜지고, 시험·로컬·GitHub Pages에서는 그대로 돈다. 계측이 던지는 오류는 모두 삼켜서 대답에 영향을 주지 않는다.
3. **사용자·세션 속성은 붙이지 않았다.** 이 앱에는 계정도 로그인도 없다. 사용자 ID를 새로 만들면 «계정 없음» 원칙에 어긋나고, 대화도 서버가 이어 주지 않는다(서버는 상태가 없음).
4. **environment와 release는 붙였다.** `ENV`(기본 local)와 Cloud Run이 넣어 주는 `K_REVISION`을 Langfuse environment·release로 보낸다. 배포 앞뒤 리비전별로 지연 시간·실패를 비교하려는 것이다.
5. **턴이 끝날 때 `flush()`를 부른다.** Cloud Run은 응답이 끝나면 CPU를 줄여서, 모아 두었다 보내는 SDK가 기록을 못 보낼 수 있다. 대가는 스트림이 닫히는 시점이 조금 늦어지는 것(전송 시간만큼)이다.
6. **SDK 버전을 고정했다(`langfuse==5.1.0`).** 웹 예제 상당수가 옛 문법이라, 이 버전에서 쓰는 `start_observation`·`update`·`end`·`flush`를 설치해 시그니처를 확인하고 썼다. 진짜 SDK로 호출 스모크를 돌려 오류가 없는 것까지 확인했다(막힌 주소로 보내서 전송 자체는 시험하지 못함).

## 증상 → 열어 볼 곳

| 증상 | Langfuse에서 | 필요한 기록 |
|---|---|---|
| 맥락과 상관없는 조언·카드가 붙음 | `plan-mode`의 metadata(고른 모드, 카드 id) | 계측함 |
| «카드가 없어 방법을 말하지 못했어요» 안내가 자주 뜸 | `plan-mode`의 asked_cards 와 card_ids 개수 차이 | 계측함 |
| 답이 가끔 늦음 | Latency 정렬, `reply`의 첫 글자 시각 | 계측함 |
| 같은 질문인데 답이 실행마다 다름 | 같은 모드의 트레이스끼리 비교 | 원문이 있어야 내용을 읽을 수 있음(기본은 꺼짐) |
| 숫자 검사에서 자꾸 탈락(`done.ok=false`) | `numbers-check` 의 ok=false 트레이스 | 계측함 |
| 요금이 예상보다 큼 | generation 별 토큰·비용 | **미구현**(아래) |

## 아직 하지 않은 것

- **토큰·비용**: `server/llm.py`의 `complete_json`·`chat_stream`이 사용량(usage)을 돌려주지 않아 generation에 토큰을 못 넣었다. 비용 칸은 비어 있다. OpenAI 호환 제공사는 스트리밍에서 `stream_options={"include_usage": True}`가 필요한데 제공사(Gemini 호환 엔드포인트 포함)별 동작을 이 PC에서 확인하지 못해 건드리지 않았다. 먼저 `FakeLLM`이 아닌 진짜 키로 `evals/run_eval.py --real` 한 번 돌려 확인한 뒤 붙인다.
- **사용자 반응 점수**: 답마다 좋아요·별로예요 버튼이 없다(의견 보내기는 메일 한 통). 버튼을 더하면 PRD 원칙 1·4(처음 화면에 고를 것을 늘리지 않는다 / 새 기능은 뒤에서 열린다)와 충돌하므로, 넣기 전에 PRD에서 먼저 정해야 한다.
- **프롬프트 버전 관리**: 지시문이 `server/policy.py`에 있고 시험(`evals/`)이 그것을 읽는다. Langfuse 프롬프트 관리로 옮기려면 평가 실행기도 함께 라벨을 읽게 바꿔야 해서 범위 밖으로 뒀다.
- **A/B 테스트**: 하지 않는다. 요청이 적은 서비스는 별로예요 비율 차이를 가리는 데 표본이 너무 오래 걸린다(노드 11 섹션 5의 계산). 의견이 갈리면 `evals/` 사례를 늘려 가린다.
- **CI 평가 게이트**: 저장소에 CI가 없다(`.github/` 없음). 지금은 배포 전 `deploy.sh`가 `pytest`를 돌리는 것이 유일한 관문이다.
- **Langfuse Cloud 프로젝트·키**: 만들지 않았다. 켜는 방법은 아래.

## 평가(노드 11)와 이미 있는 것

노드 11이 만들라고 하는 것 가운데 이 프로젝트에 이미 있는 것:

| 노드 11 | 이 프로젝트 |
|---|---|
| 같은 메시지 묶음(데이터셋) | `server/evals/cases.json` 23건(core 표시 있음) |
| 코드로 채점하는 평가자 | `server/evals/judge.py`(모드·카드·숫자·문장 수·말투·훈계 표현 등 휴리스틱 검사) |
| 실행기 | `server/evals/run_eval.py`(`--fake`/`--real`, 호출 횟수 출력) |
| 고치기 전에 잴 방법 | 같은 사례를 두 번 돌려 흔들림을 본다 — 지금까지 이렇게 해 왔는지는 기록으로 확인하지 못함 |

없는 것은 «읽어야 아는 실패»를 판정하는 LLM 심사와, 실행 결과를 Langfuse 실험으로 남기는 연결이다. 둘 다 위 «아직 하지 않은 것»의 프롬프트 관리와 같은 이유로 미뤘다.
노드 11 섹션 2의 오류 분석(트레이스 30개쯤을 읽고 처음 어긋난 단계를 한 줄씩 적어 유형으로 묶기)은 **트레이스가 쌓인 뒤에** 할 수 있다. 지금은 쌓인 것이 없어 유형표를 만들지 않았다(지어내지 않기 위해).

## 켜는 방법

1. https://us.cloud.langfuse.com 에서 가입하고 프로젝트 `routine-stamp`(staging과 production은 프로젝트를 나누지 않고 environment로 나눈다)를 만든 뒤 Settings > API Keys 에서 키를 만든다. 비밀키는 화면을 닫으면 다시 못 본다. 채팅·명령·코드에 붙여 넣지 않는다.
2. 로컬: `.env`에 세 줄(`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com`)을 넣고 서버를 띄운다. 리전 주소가 가입한 리전과 다르면 키가 맞아도 기록이 안 들어온다.
3. Cloud Run: 비밀키는 콘솔에서 Secret Manager에 `langfuse-secret-key`로 직접 만들고, 서비스(`routine-coach`)에 `--update-env-vars`(공개키·주소·`ENV=production`)와 `--update-secrets LANGFUSE_SECRET_KEY=langfuse-secret-key:latest`로 연결한다. 기존 값을 지우는 `--set-env-vars`를 쓰지 않는다. 실행 서비스 계정에 그 시크릿 하나만 읽기 권한을 준다. 자세한 점검은 `DEPLOY.md`.
4. 확인: 대화 두세 번 → Langfuse > Tracing 에 `chat-turn` 트레이스가 생기고, 열면 `safety` → `plan-mode` → `reply` → `numbers-check` 순서로 있는지, 위기 표현 메시지에는 `safety`만 있는지 본다(몇 초에서 수십 초 늦게 뜬다).
