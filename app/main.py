"""루틴도장 연습용 서버. index.html 을 내보내고, 켜 두면 사진에서 칸 이름 후보를 읽어 준다. (Docker 실습용)"""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import ocr

ROOT = Path(__file__).resolve().parent.parent

app = FastAPI()


def ocr_enabled() -> bool:
    """환경변수 OCR_ENABLED 가 true 일 때만 켠다. 기본값은 꺼짐."""
    return os.environ.get("OCR_ENABLED", "").strip().lower() in ("1", "true", "yes")


@app.get("/")
def index():
    return FileResponse(ROOT / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "ocr_enabled": ocr_enabled()}


@app.post("/api/ocr")
async def read_photo(photo: UploadFile):
    if not ocr_enabled():
        raise HTTPException(404, "사진 글자 읽기가 꺼져 있습니다")
    try:
        return {"lines": ocr.read_lines(await photo.read())}
    except ocr.OcrError as error:
        raise HTTPException(500, str(error)) from error
