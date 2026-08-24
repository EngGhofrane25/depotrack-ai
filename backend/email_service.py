import base64
import logging
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

logger = logging.getLogger("email_service")

BASE_DIR = Path(__file__).resolve().parent.parent

# simulasyon | gmail_api | smtp
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "simulasyon")
GMAIL_SENDER_EMAIL = os.getenv("GMAIL_SENDER_EMAIL", "")
GMAIL_CREDENTIALS_FILE = Path(os.getenv("GMAIL_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json")))
GMAIL_TOKEN_FILE = Path(os.getenv("GMAIL_TOKEN_FILE", str(BASE_DIR / "token.json")))
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_SENDER_EMAIL = os.getenv("SENDER_EMAIL", "simulasyon@local")
SMTP_SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")


def get_active_provider():
    if EMAIL_PROVIDER == "gmail_api":
        return "gmail_api" if GMAIL_TOKEN_FILE.exists() else "simulasyon"
    if EMAIL_PROVIDER == "smtp" and SMTP_SENDER_PASSWORD:
        return "smtp"
    return "simulasyon"


def _get_gmail_credentials():
    from google.oauth2.credentials import Credentials

    if not GMAIL_TOKEN_FILE.exists():
        raise RuntimeError(
            f"Gmail token dosyasi yok ({GMAIL_TOKEN_FILE}). "
            "Once 'python -m backend.authorize_gmail' komutunu calistirin."
        )

    creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), GMAIL_SCOPES)

    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request

        creds.refresh(Request())
        GMAIL_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        logger.info("Gmail access token yenilendi.")

    return creds


def _send_via_gmail(to_email, subject, html_content):
    from googleapiclient.discovery import build
    from google.auth.exceptions import RefreshError

    try:
        creds = _get_gmail_credentials()
        service = build("gmail", "v1", credentials=creds)

        msg = MIMEText(html_content, "html", "utf-8")
        msg["To"] = to_email
        msg["Subject"] = subject
        if GMAIL_SENDER_EMAIL:
            msg["From"] = GMAIL_SENDER_EMAIL

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except RefreshError:
        logger.error(
            "Gmail token gecersiz/sureyi dolmus ve yenilenemedi. "
            "'python -m backend.authorize_gmail' ile yeniden yetkilendirin."
        )
        return False
    except Exception as e:
        logger.error(f"Gmail API ile e-posta gonderilemedi: {e}")
        return False


def _send_via_smtp(to_email, subject, html_content):
    try:
        msg = MIMEText(html_content, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"SMTP ile e-posta gonderilemedi: {e}")
        return False


def send_email(to_email, subject, html_content):
    """E-posta gonderir; hicbir durumda uygulama cokmez, bool doner."""
    if not to_email or "@" not in to_email:
        logger.warning(f"Gecersiz alici adresi, e-posta gonderilmedi: '{to_email}'")
        return False

    provider = get_active_provider()

    if provider == "simulasyon":
        print(f"[MAIL SIMULASYONU] Kime: {to_email} | Konu: {subject}")
        return True

    if provider == "gmail_api":
        return _send_via_gmail(to_email, subject, html_content)

    return _send_via_smtp(to_email, subject, html_content)
