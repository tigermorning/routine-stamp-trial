#!/usr/bin/env bash
# 루틴 도장 Cloud Run 배포. 점검 → 스냅샷 → (배포 → 라이브 확인). 자세한 이유와 점검 목록은 DEPLOY.md.
#
# 사용:
#   ./deploy.sh                       점검과 스냅샷만 하고 실행할 배포 명령을 보여 준다(배포하지 않는다)
#   ./deploy.sh --deploy              점검 → 스냅샷 → 배포 → 라이브 확인
#   ./deploy.sh --deploy --smoke-chat 라이브 확인에 도우미 대화 한 번을 더한다(모델 비용이 조금 든다)
#
# 환경변수(선택): PROJECT REGION SERVICE FEEDBACK_USER, STAMP_TOOLS(화면 시험 스크립트가 든 폴더. 있으면 5종을 돌린다)
# 스냅샷으로 배포하는 이유: 다른 세션이 파일을 고치는 도중에 올라가지 않게, 올릴 파일만 복사해 둔 사본에서 배포한다.
set -euo pipefail

PROJECT=${PROJECT:-friend-agent-512201}
REGION=${REGION:-us-central1}
SERVICE=${SERVICE:-routine-coach}
FEEDBACK_USER=${FEEDBACK_USER:-tigermorning0@gmail.com}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DO_DEPLOY=0
SMOKE=0
for arg in "$@"; do
  case "$arg" in
    --deploy) DO_DEPLOY=1 ;;
    --smoke-chat) SMOKE=1 ;;
    *) echo "알 수 없는 옵션: $arg (사용법은 파일 맨 위 주석)" >&2; exit 2 ;;
  esac
done

step() { printf '\n== %s\n' "$*"; }
ok() { printf '  ✔ %s\n' "$*"; }
fail() { printf '  ✗ %s\n' "$*" >&2; exit 1; }

# ---- 1. 배포 전 점검(DEPLOY.md 의 점검 목록) ----
step "1. 점검"
for f in index.html Procfile requirements.txt .gcloudignore server/main.py server/requirements.txt; do
  [ -f "$HERE/$f" ] || fail "파일이 없어요: $f"
done
ok "올릴 파일이 있어요"

account="$(gcloud config get-value account 2>/dev/null || true)"
[ -n "$account" ] || fail "gcloud 로그인 계정이 없어요(gcloud auth login)"
ok "gcloud 계정: $account / 프로젝트: $PROJECT / 리전: $REGION"

for secret in llm-api-key feedback-smtp-password; do
  gcloud secrets describe "$secret" --project "$PROJECT" >/dev/null 2>&1 || fail "Secret Manager 에 '$secret' 가 없어요"
done
ok "비밀 2개가 있어요(값은 읽지 않아요)"

(cd "$HERE/server" && python -m pytest tests -q) || fail "서버 시험이 실패했어요"
ok "서버 시험 통과"

node -e "
const h=require('fs').readFileSync(process.argv[1],'utf8');
const c=[...h.matchAll(/<script(?![^>]*src)[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]).join('\n');
new Function(c);
" "$HERE/index.html" || fail "index.html 스크립트 문법 오류"
ok "화면 스크립트 문법 통과"

if [ -n "${STAMP_TOOLS:-}" ]; then
  for t in unlock settings routine del chat; do
    node "$STAMP_TOOLS/${t}_test.js" "$HERE/index.html" >/dev/null 2>&1 || fail "화면 시험 실패: $t"
  done
  ok "화면 시험 5종 통과"
else
  echo "  - STAMP_TOOLS 가 없어 화면 시험 5종은 건너뛰었어요(확인 못 함)"
fi

if git -C "$HERE" status --porcelain 2>/dev/null | grep -q .; then
  echo "  - 커밋하지 않은 변경이 있어요(배포는 되지만 기록과 어긋날 수 있어요)"
fi

# ---- 2. 스냅샷 ----
step "2. 스냅샷"
SNAP="$(mktemp -d)/snap"
mkdir -p "$SNAP"
cp "$HERE/index.html" "$HERE/Procfile" "$HERE/requirements.txt" "$HERE/.gcloudignore" "$SNAP/"
cp -r "$HERE/server" "$SNAP/server"
find "$SNAP" \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
ok "스냅샷: $SNAP"

# ---- 3. 배포 ----
step "3. 배포"
PREV="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)' 2>/dev/null || true)"
echo "  지금 서비스 중인 리비전: ${PREV:-없음}"
DEPLOY_CMD=(gcloud run deploy "$SERVICE" --source "$SNAP" --region "$REGION" --project "$PROJECT"
  --update-env-vars "FEEDBACK_SMTP_USER=$FEEDBACK_USER"
  --update-secrets "FEEDBACK_SMTP_PASSWORD=feedback-smtp-password:latest" --quiet)
if [ "$DO_DEPLOY" -ne 1 ]; then
  echo "  (배포하지 않았어요. 실제로 올리려면 --deploy 를 붙여요) 실행할 명령:"
  printf '    %q' "${DEPLOY_CMD[@]}"; printf '\n'
  exit 0
fi
"${DEPLOY_CMD[@]}"
NEW="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.latestReadyRevisionName)')"
ok "새 리비전: $NEW"

# ---- 4. 라이브 확인 ----
step "4. 라이브 확인"
URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" --format='value(status.url)')"
code="$(curl -s -o /dev/null -w '%{http_code}' "$URL/")"
[ "$code" = "200" ] || fail "화면이 200 이 아니에요: $code"
ok "화면 200"
curl -s "$URL/health" | grep -q '"ok"' || fail "/health 가 ok 가 아니에요"
ok "/health ok"
if [ "$SMOKE" -eq 1 ]; then
  body='{"messages":[{"role":"user","content":"안녕"}],"context":{"slots":["걷기"],"days":1,"today":[0]}}'
  printf '%s' "$body" | curl -s -X POST "$URL/api/chat" -H 'Content-Type: application/json' --data-binary @- | grep -q '"done"' || fail "도우미 대화가 끝까지 오지 않았어요"
  ok "도우미 대화 한 번 성공"
else
  echo "  - 도우미 대화는 확인하지 않았어요(--smoke-chat 으로 확인할 수 있어요)"
fi
echo
echo "되돌리려면(이전 리비전으로 트래픽 100%):"
echo "  gcloud run services update-traffic $SERVICE --region $REGION --project $PROJECT --to-revisions ${PREV:-<이전리비전>}=100"
echo "최신으로 복귀:"
echo "  gcloud run services update-traffic $SERVICE --region $REGION --project $PROJECT --to-latest"
