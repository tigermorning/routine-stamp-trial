"""사진·PDF 속 글자 읽기(OCR). 손글씨 메모 사진이나 시간표 PDF에서 줄마다 칸 이름 후보를 뽑는다. (Docker 실습용)

Python 라이브러리(pytesseract, pdf2image)는 requirements.txt 로 설치되지만, 실제로 글자를 읽는 tesseract 와
PDF 를 이미지로 바꾸는 poppler 는 운영체제에 따로 설치하는 프로그램이다.
노트북에는 직접 설치하고, 서버에서는 실행 환경(이미지)에 들어 있어야 한다.
"""
import io
import json

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


def read_lines(data: bytes) -> list[str]:
    import pytesseract
    from PIL import Image, UnidentifiedImageError

    if len(data) > MAX_BYTES:
        raise OcrError("파일이 5MB보다 큽니다.")
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
