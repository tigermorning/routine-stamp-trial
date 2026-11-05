"""사진·PDF 속 글자 읽기(OCR). 손글씨 메모 사진이나 시간표 PDF에서 줄마다 칸 이름 후보를 뽑는다. (Docker 실습용)

Python 라이브러리(pytesseract, pdf2image)는 requirements.txt 로 설치되지만, 실제로 글자를 읽는 tesseract 와
PDF 를 이미지로 바꾸는 poppler 는 운영체제에 따로 설치하는 프로그램이다.
노트북에는 직접 설치하고, 서버에서는 실행 환경(이미지)에 들어 있어야 한다.
"""
import io
import json
import os
import time

MAX_BYTES = 5 * 1024 * 1024  # 파일 하나 최대 5MB
MAX_LINE_CHARS = 30  # 칸 이름 후보 한 줄의 최대 글자 수
MAX_PDF_PAGES = 3  # PDF 는 앞쪽 3쪽까지만 읽는다
PDF_DPI = 200  # PDF 를 이미지로 바꿀 때의 해상도


class OcrError(Exception):
    pass


def log(severity: str, message: str, **fields) -> None:
    """Cloud Run 로그에 심각도가 붙도록 JSON 한 줄로 찍는다."""
    print(json.dumps({"severity": severity, "message": message, **fields}, ensure_ascii=False), flush=True)


def _register_heif() -> None:
    """아이폰 사진(HEIC)을 열 수 있게 등록한다. 패키지가 없으면 HEIC 만 못 읽는다."""
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        log("WARNING", "pillow-heif 패키지가 없어 HEIC 사진은 읽을 수 없습니다.")


def _pdf_to_images(data: bytes) -> list:
    from pdf2image import convert_from_bytes
    from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError

    try:
        return convert_from_bytes(data, dpi=PDF_DPI, first_page=1, last_page=MAX_PDF_PAGES)
    except (PDFInfoNotInstalledError, FileNotFoundError) as error:
        log("ERROR", "poppler 프로그램(pdftoppm)을 찾을 수 없습니다. 실행 환경에 poppler-utils 가 설치되어 있지 않습니다.")
        raise OcrError("PDF를 이미지로 바꾸는 프로그램이 서버에 없습니다.") from error
    except (PDFPageCountError, PDFSyntaxError) as error:
        raise OcrError("PDF 파일을 읽을 수 없습니다.") from error


def engine() -> str:
    """환경변수 OCR_ENGINE 으로 엔진을 고른다: tesseract(기본) 또는 easyocr. easyocr 는 torch 가 필요해 무겁다."""
    return os.environ.get("OCR_ENGINE", "tesseract").strip().lower()


_easy_reader = None


def _easyocr_lines(image) -> list[str]:
    """EasyOCR 로 읽고, 글자 조각을 같은 높이끼리 묶어 줄로 만든다. (손글씨 시험용, 선택 사항)"""
    global _easy_reader
    import numpy as np

    try:
        import easyocr
    except ImportError as error:
        raise OcrError("OCR_ENGINE=easyocr 인데 easyocr 패키지가 설치되어 있지 않습니다.") from error
    if _easy_reader is None:
        _easy_reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    boxes = _easy_reader.readtext(np.array(image.convert("RGB")))
    items = []  # (가운데 y, 왼쪽 x, 높이, 글)
    for points, text, _conf in boxes:
        ys = [p[1] for p in points]
        xs = [p[0] for p in points]
        items.append(((min(ys) + max(ys)) / 2, min(xs), max(ys) - min(ys), text.strip()))
    items.sort()
    rows: list[list[tuple]] = []
    for item in items:
        if rows and abs(item[0] - rows[-1][-1][0]) < 0.6 * max(item[2], rows[-1][-1][2]):
            rows[-1].append(item)
        else:
            rows.append([item])
    result = []
    for row in rows:
        row.sort(key=lambda it: it[1])
        line = " ".join(it[3] for it in row if it[3]).strip()
        if line:
            result.append(line[:MAX_LINE_CHARS])
    return result


TROCR_MODEL = "team-lucid/trocr-small-korean"
_trocr = None


def _trocr_lines(image) -> list[str]:
    """손글씨 시험용(선택): EasyOCR 의 글자 위치 검출기로 줄을 찾고, 줄마다 잘라 한국어 TrOCR 로 읽는다.

    사진에서 뽑은 줄 중 한글도 숫자도 없는 것(배경의 영어 인쇄 글자 등)은 버린다.
    """
    global _trocr, _easy_reader
    import numpy as np

    try:
        import easyocr
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    except ImportError as error:
        raise OcrError("OCR_ENGINE=trocr 인데 easyocr·transformers 패키지가 설치되어 있지 않습니다.") from error
    if _easy_reader is None:
        _easy_reader = easyocr.Reader(["ko", "en"], gpu=False, verbose=False)
    if _trocr is None:
        _trocr = (TrOCRProcessor.from_pretrained(TROCR_MODEL), VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL))
    processor, model = _trocr

    horizontal, free = _easy_reader.detect(np.array(image))
    boxes = list(horizontal[0]) + [
        [min(p[0] for p in b), max(p[0] for p in b), min(p[1] for p in b), max(p[1] for p in b)] for b in free[0]
    ]
    boxes.sort(key=lambda b: (b[2] + b[3]) / 2)
    rows: list[dict] = []
    for x0, x1, y0, y1 in boxes:
        cy, h = (y0 + y1) / 2, y1 - y0
        if rows and abs(cy - rows[-1]["cy"]) < 0.6 * max(h, rows[-1]["h"]):
            r = rows[-1]
            r["x0"], r["x1"] = min(r["x0"], x0), max(r["x1"], x1)
            r["y0"], r["y1"] = min(r["y0"], y0), max(r["y1"], y1)
            r["cy"], r["h"] = (r["y0"] + r["y1"]) / 2, r["y1"] - r["y0"]
        else:
            rows.append({"x0": x0, "x1": x1, "y0": y0, "y1": y1, "cy": cy, "h": h})
    result = []
    pad = 10
    for r in rows[:40]:  # 줄이 너무 많은 사진은 앞쪽 40줄까지만
        crop = image.crop((max(0, r["x0"] - pad), max(0, r["y0"] - pad), min(image.width, r["x1"] + pad), min(image.height, r["y1"] + pad)))
        pixel_values = processor(images=crop, return_tensors="pt").pixel_values
        ids = model.generate(pixel_values, max_length=32)
        text = processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
        if any("가" <= ch <= "힣" or ch.isdigit() for ch in text):
            result.append(text[:MAX_LINE_CHARS])
    return result


def save_debug(data: bytes) -> None:
    """OCR_DEBUG_DIR 가 지정되면 올라온 파일을 그 폴더에 저장한다(인식 품질을 살펴볼 때만 쓴다)."""
    folder = os.environ.get("OCR_DEBUG_DIR", "").strip()
    if not folder:
        return
    os.makedirs(folder, exist_ok=True)
    suffix = ".pdf" if data.startswith(b"%PDF-") else ".img"
    path = os.path.join(folder, f"upload-{int(time.time())}{suffix}")
    with open(path, "wb") as fh:
        fh.write(data)
    log("INFO", "디버그용으로 올라온 파일 저장", path=path)


def read_lines(data: bytes) -> list[str]:
    import pytesseract
    from PIL import Image, UnidentifiedImageError

    if len(data) > MAX_BYTES:
        raise OcrError("파일이 5MB보다 큽니다.")
    save_debug(data)
    if data.startswith(b"%PDF-"):
        images = _pdf_to_images(data)
        source = "pdf"
    else:
        _register_heif()
        try:
            images = [Image.open(io.BytesIO(data))]
        except UnidentifiedImageError as error:
            raise OcrError("사진 파일을 읽을 수 없습니다.") from error
        source = "photo"
    lines: list[str] = []
    if engine() == "trocr":
        for image in images:
            lines += _trocr_lines(image.convert("RGB"))
        log("INFO", "글자 읽기", source=source, pages=len(images), engine="trocr", lines=len(lines))
        return lines
    if engine() == "easyocr":
        for image in images:
            lines += _easyocr_lines(image)
        log("INFO", "글자 읽기", source=source, pages=len(images), engine="easyocr", lines=len(lines))
        return lines
    try:
        langs = pytesseract.get_languages(config="")
        lang = "kor+eng" if "kor" in langs else "eng"
        if lang == "eng":
            log("WARNING", "tesseract 한국어 데이터가 없어 영어로만 읽습니다.")
        for image in images:
            # 형식(HEIC 등)에 상관없이 일반 RGB 이미지로 바꿔서 넘긴다.
            # --psm 6: 한 쪽 전체를 글자 덩어리 하나로 본다.
            text = pytesseract.image_to_string(image.convert("RGB"), lang=lang, config="--psm 6")
            lines += [line.strip()[:MAX_LINE_CHARS] for line in text.splitlines() if line.strip()]
    except pytesseract.TesseractNotFoundError as error:
        log("ERROR", "tesseract 프로그램을 찾을 수 없습니다. 실행 환경에 tesseract 가 설치되어 있지 않습니다.")
        raise OcrError("사진에서 글자를 읽는 프로그램이 서버에 없습니다.") from error
    log("INFO", "글자 읽기", source=source, pages=len(images), lang=lang, lines=len(lines))
    return lines
