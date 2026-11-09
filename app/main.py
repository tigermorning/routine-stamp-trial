"""루틴도장 연습용 서버. index.html 을 내보내고, 켜 두면 사진에서 칸 이름 후보를 읽어 준다. (Docker 실습용)"""
import os
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app import ocr

ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT / "server"

app = FastAPI()

# 시작 지연 스위치(배포 실습용). 정한 시간 동안은 준비 중이라 모든 요청에 503을 돌려준다. 기본값 0(끔).
SLOW_START_SECONDS = float(os.environ.get("SLOW_START_SECONDS", "0") or 0)
READY_AT = time.time() + SLOW_START_SECONDS


@app.middleware("http")
async def not_ready_yet(request, call_next):
    if time.time() < READY_AT:
        return JSONResponse({"status": "starting"}, status_code=503)
    return await call_next(request)


def ocr_enabled() -> bool:
    """환경변수 OCR_ENABLED 가 true 일 때만 켠다. 기본값은 꺼짐."""
    return os.environ.get("OCR_ENABLED", "").strip().lower() in ("1", "true", "yes")


@app.get("/")
def index():
    return FileResponse(ROOT / "index.html")


@app.get("/health")
def health():
    # 망가진 버전 시험용 스위치: BROKEN_HEALTH 가 켜져 있으면 준비되지 않았다고 답한다.
    if os.environ.get("BROKEN_HEALTH", "").strip().lower() in ("1", "true", "yes"):
        return JSONResponse({"ok": False}, status_code=503)
    return {"ok": True, "ocr_enabled": ocr_enabled()}


@app.get("/version")
def version():
    """어느 커밋·리비전이 대답하는지 보여 준다. 커밋은 배포할 때 COMMIT_SHA 로, 리비전은 Cloud Run 이 K_REVISION 으로 넣는다."""
    return {
        "commit": os.environ.get("COMMIT_SHA", ""),
        "revision": os.environ.get("K_REVISION", ""),
        "env": os.environ.get("ENV", ""),
    }


@app.post("/api/ocr")
async def read_photo(photo: UploadFile):
    if not ocr_enabled():
        raise HTTPException(404, "사진 글자 읽기가 꺼져 있습니다")
    try:
        lines = ocr.read_lines(await photo.read())
        # lines: 웹 화면용(기존), text: 모바일 앱용(줄바꿈으로 이은 글)
        return {"lines": lines, "text": "\n".join(lines)}
    except ocr.OcrError as error:
        raise HTTPException(500, str(error)) from error


# 도우미·크레딧·상점·결제·의견 보내기(server/main.py)를 같은 주소 아래에 붙인다.
# 위에서 정한 경로(/, /health, /version, /api/ocr)가 먼저 맞고, 나머지(/api/chat, /api/shop, /pay 등)는 server 앱이 받는다.
# server 안의 모듈은 서로 `import byok` 처럼 이름만 써서 불러오므로 server 폴더를 모듈 찾는 길에 넣는다.
sys.path.insert(0, str(SERVER_DIR))
import main as _server_main  # noqa: E402  (server/main.py)

app.mount("/", _server_main.app)
