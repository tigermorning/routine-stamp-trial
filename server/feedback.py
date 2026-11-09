"""의견 보내기: 화면의 '제출하기'가 보낸 글을 만든 사람의 메일로 전달한다.

- Gmail SMTP(smtp.gmail.com:465, SSL)로 보낸다. 환경변수: FEEDBACK_SMTP_USER(보내는 Gmail 계정) FEEDBACK_SMTP_PASSWORD(그 계정의 앱 비밀번호, Secret Manager 에서 주입)
  FEEDBACK_TO(받는 주소, 없으면 FEEDBACK_SMTP_USER). 비밀번호는 코드·화면·로그에 넣지 않는다.
- 의견 본문은 로그에 남기지 않는다(오류 종류만 남긴다). 서버는 의견을 저장하지 않고 메일로 넘기기만 한다.
"""
import os
import smtplib
from email.message import EmailMessage

MAX_TEXT = 1500
MAX_STATS = 300
SUBJECT = "[루틴 도장] 의견이 도착했어요"


def clean(text, limit):
    """제어문자를 걷어 내고 길이를 자른다(줄바꿈·탭은 남긴다)."""
    t = "".join(c for c in str(text or "") if c in "\n\t" or c >= " ")
    return t.strip()[:limit]


def configured():
    return bool(os.environ.get("FEEDBACK_SMTP_USER", "").strip() and os.environ.get("FEEDBACK_SMTP_PASSWORD", "").strip())


def build_message(text, stats):
    user = os.environ["FEEDBACK_SMTP_USER"].strip()
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = os.environ.get("FEEDBACK_TO", "").strip() or user
    msg["Subject"] = SUBJECT  # 제목은 고정이다(사용자 글을 헤더에 넣지 않는다)
    msg.set_content(text + ("\n\n" + stats if stats else ""))
    return msg


def send(text, stats=""):
    """메일 한 통을 보낸다. 실패하면 예외를 그대로 던진다(호출자가 종류만 로그에 남긴다)."""
    msg = build_message(clean(text, MAX_TEXT), clean(stats, MAX_STATS))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login(os.environ["FEEDBACK_SMTP_USER"].strip(), "".join(os.environ["FEEDBACK_SMTP_PASSWORD"].split()))  # 앱 비밀번호는 4칸씩 띄어 보여 줘서 공백을 모두 뺀다
        smtp.send_message(msg)
