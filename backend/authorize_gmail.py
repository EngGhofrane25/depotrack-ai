"""Gmail API icin BIR KEZLIK OAuth 2.0 yetkilendirmesi.

Kullanim (proje kok dizininde):
    python -m backend.authorize_gmail

Gereksinimler:
    - Google Cloud Console'dan indirdiginiz OAuth istemci dosyasi: credentials.json
    - Yetkilendirme sonucunda token.json olusur (git'e commit EDILMEZ).
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# .env once yuklenmeli cunku email_service modul seviyesinde ortam degiskenlerini okur.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from google_auth_oauthlib.flow import InstalledAppFlow

from .email_service import GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES, GMAIL_TOKEN_FILE


def main():
    if not GMAIL_CREDENTIALS_FILE.exists():
        print(f"[HATA] '{GMAIL_CREDENTIALS_FILE}' bulunamadi.")
        print("Google Cloud Console > APIs & Services > Credentials > OAuth client ID")
        print("adimlarindan indirdiginiz JSON dosyasini proje kokune 'credentials.json'")
        print("adiyla kaydedin (veya GMAIL_CREDENTIALS_FILE ile farkli yol verin).")
        sys.exit(1)

    flow = InstalledAppFlow.from_client_secrets_file(str(GMAIL_CREDENTIALS_FILE), GMAIL_SCOPES)
    # prompt='consent' her zaman refresh token uretir; boylece tekrar tekrar izin istenmez.
    creds = flow.run_local_server(port=0, prompt="consent")

    GMAIL_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"[OK] Yetkilendirme tamamlandi. Token kaydedildi: {GMAIL_TOKEN_FILE}")
    print("Artik .env icinde EMAIL_PROVIDER=gmail_api yaparak gonderim yapabilirsiniz.")


if __name__ == "__main__":
    main()
