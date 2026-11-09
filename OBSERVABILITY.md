# 관측과 품질 확인 (Langfuse)

배운 곳: 모두의연구소 «AI 서비스 인 프로덕션» 노드 10(문제 찾기)·11(품질 지키기). 코드는 `server/tracing.py`와 `server/main.py`의 `/api/chat`, 시험은 `server/tests/test_tracing.py`.
이 문서의 «지금 상태»는 2026-11-03에 코드와 시험을 직접 돌려 확인한 것이다. Langfuse Cloud(us, 프로젝트 My Project)에 개발 환경 트레이스·데이터셋·실험·프롬프트가 있다(운영 Cloud Run 에는 아직 키가 없다).

## 왜 붙였나

서버 로그에는 `POST /api/chat 200` 만 남고(대화 원문은 남기지 않는 원칙), 도우미가 어느 모드를 골랐는지, 근거 카드를 어느 것으로 골랐는지, 어느 단계가 느렸는지는 알 수 없다. 응답 코드는 200인데 답이 이상한 경우가 이 서비스의 주된 문제 모양이다.
트레이스는 «메시지 하나가 거친 단계»를 한 묶음으로 보여 준다.

## 계측 구조 (한 턴 = 트레이스 하나)

| 단계 | 관찰 단위 이름 | 종류 | 모델을 부르나 | 남기는 것(원문 없이) |
|---|---|---|---|---|
| 한 턴 전체 | `chat-turn` | agent(트레이스의 뿌리) | – | BYOK 여부, 결과(reply·crisis·scope·key-error), done.ok, 모드, 근거 표시 종류 |
| 위기 키워드 검사 | `check-safety` | guardrail | 안 부름(코드 규칙) | 위기 여부 |
| 모드·카드 고르기 | `choose-mode` | generation | 부름(짧은 비스트리밍) | 모델 이름, 토큰 수, 고른 모드, 실제 카드 id, 모델이 댄 카드 id 수(없는 id를 대면 실제보다 많음) |
| 답 스트리밍 | `generate-reply` | generation | 부름 | 모델 이름, 토큰 수, 모드, 첫 글자가 나온 시각, 답 글자 수, `[REFUSED]` 여부, 길이 제한으로 끊었는지(`cut`) |
| 숫자 검사 | `check-numbers` | guardrail | 안 부름(코드 규칙) | 통과 여부, 모드 |

- 나눈 기준은 «고치는 곳이 다른가»다. 엉뚱한 답의 원인이 모드 선택이면 `PLAN_SYSTEM`을, 카드 선택이면 카드 목록을, 답이면 `MODE_RULES`를 고친다(`server/policy.py`).
- 모델을 부르는 단계만 generation으로 남겼다(모델 이름과 토큰이 있어야 비용이 계산되기 때문).
- 2026-11-03 Langfuse 공식 스킬(`langfuse/skills`)과 문서(best-practices, observation types, token cost)에 맞춰 고쳤다: 이름을 동사로 시작하게(`check-safety`·`choose-mode`·`generate-reply`·`check-numbers`, 이름은 필터·평가자가 찾는 열쇠라 앞으로 바꾸지 않는다), 코드 규칙 검사 둘을 `guardrail`로, 흐름을 고르는 한 턴을 `agent`로, generation 에 토큰 수(`usage_details` 의 input·output)를 넣었다. 원문 수집을 켠 경우에만 트레이스 입력=사용자 말, 출력에 답을 넣는다.
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
| 맥락과 상관없는 조언·카드가 붙음 | `choose-mode`의 metadata(고른 모드, 카드 id) | 계측함 |
| «카드가 없어 방법을 말하지 못했어요» 안내가 자주 뜸 | `choose-mode`의 asked_cards 와 card_ids 개수 차이 | 계측함 |
| 답이 가끔 늦음 | Latency 정렬, `generate-reply`의 첫 글자 시각 | 계측함 |
| 같은 질문인데 답이 실행마다 다름 | 같은 모드의 트레이스끼리 비교 | 원문이 있어야 내용을 읽을 수 있음(기본은 꺼짐) |
| 숫자 검사에서 자꾸 탈락(`done.ok=false`) | `check-numbers` 의 ok=false 트레이스 | 계측함 |
| 요금이 예상보다 큼 | generation 별 토큰·비용 | 계측함(아래 한계) |

## 아직 하지 않은 것

- **토큰·비용의 한계**: `server/llm.py`가 호출마다 넘겨받은 dict 에 토큰 수를 채운다(OpenAI·Claude). 스트리밍은 OpenAI 본 주소에서만 `stream_options={"include_usage": True}`를 요청한다 — Gemini 호환 주소의 동작은 확인하지 못해 그 경우 답 단계 토큰 칸이 빈다. 답을 길이 제한으로 먼저 끊으면(`cut=true`) 사용량이 담긴 마지막 조각을 못 받아 역시 빈다. 2026-11-03 gpt-4o-mini 한 턴으로 토큰·비용이 찍히는 것을 확인했다(choose-mode 939/23 토큰 $0.00015465, generate-reply 2048/74 토큰 $0.0003516).
- **세션**: 대화는 브라우저가 기록을 들고 매번 보내는 방식이라 서버에 대화 id 가 없다. Langfuse 문서는 여러 턴 대화에 `session_id` 를 권하지만, 브라우저가 대화마다 임의 id 를 만들어 보내게 하는 것은 «계정·추적 없음» 원칙과 맞는지 PRD 에서 먼저 정할 일이라 넣지 않았다.
- **사용자 반응 점수**: 답마다 좋아요·별로예요 버튼이 없다(의견 보내기는 메일 한 통). 버튼을 더하면 PRD 원칙 1·4(처음 화면에 고를 것을 늘리지 않는다 / 새 기능은 뒤에서 열린다)와 충돌하므로, 넣기 전에 PRD에서 먼저 정해야 한다.
- **A/B 테스트**: 하지 않는다. 사용자 ID 도 좋아요·별로예요 버튼도 없어서 그룹을 나누거나 반응을 셀 수 없고, 요청이 적은 서비스는 비율 차이를 가리는 데 표본이 너무 오래 걸린다(노드 11 섹션 5: 하루 메시지 50건·피드백 10%면 5%p 차이에 1년 가까이). 의견이 갈리면 데이터셋 항목을 늘려 실험으로 가린다.
- **CI 평가 게이트**: 저장소에 CI가 없다(`.github/` 없음). 대신 `deploy.sh --eval-gate` 로 배포 전 평가 관문을 고를 때만 돌린다(아래).
- **운영(Cloud Run) 키**: 운영 서버에는 아직 Langfuse 키를 넣지 않았다. 그래서 운영은 Langfuse 프롬프트 대신 코드 문장(policy.py, Langfuse production 과 같은 문장)으로 답하고 트레이스도 남기지 않는다.
- **남은 실패**: 연구 수치 질문(`numbers-ask`)을 아직 범위 밖으로 보낸다(지시문 v1·v2·v3 모두). 지시문에 이미 적혀 있는데도 안 따르므로, 다음에는 코드로 고칠지(예: 연구·수치 질문이면 모드 고르기 결과를 listen 으로 바꾸기) 정한다.

## 노드 11(품질 지키기)을 적용한 결과 — 2026-11-03

서비스 도우미 = gpt-4o-mini(운영과 같은 모델), 심사 = Claude claude-sonnet-5-5. 숫자는 같은 설정을 두 번 돌린 결과다(실행마다 2~4개씩 흔들린다).

1. **오류 분석**: 평가 사례 23건 × 2 = 트레이스 46개(이 실행만 원문 수집, environment=development)를 앞 단계부터 읽어 실패 유형을 묶었다 — ① 모드 오분류(choose-mode) ② 듣기 모드 효과 단정·범위 밖 제안 ③ 되묻기 되풀이 ④ 한 답에 질문 여러 개. 메모는 Langfuse 트레이스 댓글(17개).
2. **데이터셋**(`evals/langfuse_experiment.py upload`): `stamp-mode` 21개(대화 → 기대 모드), `stamp-listen-reply` 12개(모드를 listen 으로 고정하고 답만 잰다 — 답이 틀렸을 때 모드 탓과 답 지시문 탓을 가르려고). 실패 사례와 정상 사례를 함께 넣었다.
3. **평가자**: 코드 — mode-correct, no-invented-numbers(서버 numbers_ok), no-repeat-question, one-question, not-bare-echo. LLM 심사(Claude) — judge-no-effect-claim(②), judge-natural(⑤ 말투 흔들림·뜻 모를 문장), judge-relevance(⑥ 이미 말한 일 되묻기·엉뚱한 칸 짚기·막연한 제안·방법 되묻기). ⑤⑥은 사용자 라벨에서 나온 유형이다.
4. **심사 보정**: 사용자가 답 23개에 직접 통과·실패를 붙였다. 심사 판정과 일치율 65%(놓친 실패 6) → 기준 문장을 사용자 말로 고치고 경계 4가지를 정해 **91%(놓친 실패 0)**.
5. **프롬프트 관리**(`server/prompts.py`, `evals/prompt_versions.py`): `stamp-plan`(모드 고르기), `stamp-listen-rule`(듣기 규칙)을 Langfuse 에서 라벨(production/staging)로 가져오고, 못 가져오면 코드 문장으로 답한다. generation 에 프롬프트가 연결돼 트레이스에서 버전이 보인다. 지금 production 은 두 프롬프트 모두 v3.
6. **코드로 옮긴 것**(`coach.ReplyGate`): 지시문에 적혀 있어도 모델이 지키지 않던 규칙 — 질문은 하나만(두 번째부터 버림), 직전이 질문이면 되묻는 질문 버림('~해 볼까요?' 같은 제안은 남김), 근거 없는 숫자 문장 버림. 대화 모드 답을 문장 단위로 내보내며 화면에 나가기 전에 거른다.
7. **실험 결과**(듣기 답 12개, 모드 21개):

| | 기준선(v1, 코드 없음) | 지금(v3 + 문장 걸러 내기) |
|---|---|---|
| 모드를 맞게 고름 | 18·18 /21 | 20·20 /21 |
| 심사 셋(효과·말투뜻·맥락) 모두 통과 | 6·5 /12 | 12·9 /12 |
| 지어낸 숫자 없음 | 10·11 /12 | 12·12 /12 |
| 되묻기 없음(직전이 질문인 4개) | 1·1 /4 | 4·4 /4 |
| 질문 하나 | 6·6 /12 | 12·12 /12 |
| 빈 맞장구 아님 | 12·12 /12 | 12·12 /12 |

   전체 사례 회귀 확인(evals/cases.json 23건, judge.py): 처음 46개 중 실패 17개(채점기 문제 4개 포함) → 마지막 23개 중 2개(numbers-ask, general-info 1건).
8. **실험에서 드러난 함정(기록)**:
   - 걸러 내기 첫 판은 '질문 하나 뒤 멈춤'이라 첫 문장이 되받는 질문이면 답이 한 줄로 끝났다 → 두 번째 질문부터 버리기로.
   - 둘째 판은 직전이 질문일 때 '~해 볼까요?' 제안까지 지워 '저녁만 되면 눕게 되는군요.' 한 줄만 남았다(실행마다 2~4개). 평가자는 모두 통과라 숫자로 안 보였고, 전후 답을 사람이 읽다 찾았다 → 제안형 물음은 남기고 not-bare-echo 평가자를 더했다.
   - 모드 지시문 v2 의 '자기 경험을 털어놓는 말은 listen' 이 관계 고민까지 잡아 scope-relationship 이 회귀했다(전체 사례 회귀 확인에서 발견) → v3 에서 '루틴·이 앱'으로 좁힘.
   - 심사가 처음 두 번 점수를 못 남겼다: anthropic 패키지 미설치(평가자 예외를 SDK 가 삼킴), max_tokens 400 에서 응답 잘림(빈 BOOLEAN 점수를 Langfuse 가 거절).

## 평가 관문(노드 11 섹션 6)

- `server/evals/eval_gate.py --runs 2`: 지금 라벨·설정으로 두 데이터셋 실험을 돌리고 `gate_thresholds.json` 바닥값(내보낸 결과에서 흔들림 1~2를 뺀 값)에 못 미치면 1로 끝난다. 2026-11-03 실행: 통과(모드 평균 19.0, 심사 셋 10.5, 숫자 12, 되묻기 4, 질문 하나 12).
- `deploy.sh --eval-gate` 가 점검 단계에서 부른다. 실험 한 번에 OpenAI 약 33번·Claude 약 36번을 부르므로 기본은 꺼져 있고, 지시문이나 대화 코드를 바꿨을 때만 켠다.
- 프롬프트 라벨을 옮기기 전(`prompt_versions.py promote`)에도 이 관문을 먼저 돌린다. 롤백은 이전 버전 번호로 promote.

## 켜는 방법

1. https://us.cloud.langfuse.com 에서 가입하고 프로젝트 `routine-stamp`(staging과 production은 프로젝트를 나누지 않고 environment로 나눈다)를 만든 뒤 Settings > API Keys 에서 키를 만든다. 비밀키는 화면을 닫으면 다시 못 본다. 채팅·명령·코드에 붙여 넣지 않는다.
2. 로컬: `.env`에 세 줄(`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com`)을 넣고 서버를 띄운다. 리전 주소가 가입한 리전과 다르면 키가 맞아도 기록이 안 들어온다.
3. Cloud Run: 비밀키는 콘솔에서 Secret Manager에 `langfuse-secret-key`로 직접 만들고, 서비스(`routine-coach`)에 `--update-env-vars`(공개키·주소·`ENV=production`)와 `--update-secrets LANGFUSE_SECRET_KEY=langfuse-secret-key:latest`로 연결한다. 기존 값을 지우는 `--set-env-vars`를 쓰지 않는다. 실행 서비스 계정에 그 시크릿 하나만 읽기 권한을 준다. 자세한 점검은 `DEPLOY.md`.
4. 확인: 대화 두세 번 → Langfuse > Tracing 에 `chat-turn` 트레이스가 생기고, 열면 `check-safety` → `choose-mode` → `generate-reply` → `check-numbers` 순서로 있는지, 위기 표현 메시지에는 `check-safety`만 있는지, generation 두 개에 토큰 수와 비용이 찍히는지 본다(몇 초에서 수십 초 늦게 뜬다).
