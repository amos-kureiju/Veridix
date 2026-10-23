import smtplib
import ssl
import socket
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.core.config import settings

logger = logging.getLogger("VERIDIX-EMAIL")


# Subclass resmi untuk memaksa koneksi ke IPv4 Google
class IPv4SMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        if self.context is None:
            self.context = ssl.create_default_context()
        # Ambil IP address IPv4 murni (menghindari error IPv6 di Windows)
        addrinfo = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        ipv4_ip = addrinfo[0][4][0]
        raw_sock = socket.create_connection((ipv4_ip, port), timeout, self.source_address)
        return self.context.wrap_socket(raw_sock, server_hostname=host)


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Mengirimkan email tautan reset kata sandi menggunakan jalur IPv4 SSL Gmail (Port 465).
    """
    smtp_password = (
        settings.SMTP_PASSWORD.get_secret_value() 
        if settings.SMTP_PASSWORD 
        else ""
    )

    # Bersihkan spasi dari email dan 16 digit app password
    smtp_user = (settings.SMTP_USER or "").strip()
    smtp_password = smtp_password.replace(" ", "").strip()

    if not smtp_user or not smtp_password:
        print("\n[ERROR]: SMTP_USER atau SMTP_PASSWORD masih kosong di file .env!")
        return False

    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
    expire_minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Instruksi Pemulihan Kata Sandi Akun VERIDIX"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{smtp_user}>"
    msg["To"] = to_email

    text_content = f"""Halo,

Kami menerima permintaan untuk mengatur ulang kata sandi akun VERIDIX Anda.
Silakan klik tautan di bawah ini untuk membuat kata sandi baru:

{reset_link}

Tautan ini hanya berlaku selama {expire_minutes} menit.
Jika Anda tidak meminta pengaturan ulang kata sandi, abaikan email ini.

Salam,
Tim Keamanan VERIDIX
"""

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }}
            .container {{ max-width: 520px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
            .header {{ text-align: center; margin-bottom: 24px; }}
            .brand {{ font-size: 20px; font-weight: 800; color: #064e3b; letter-spacing: 1px; }}
            .title {{ font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 10px; }}
            .text {{ font-size: 14px; color: #475569; line-height: 1.6; margin: 16px 0; }}
            .btn-wrapper {{ text-align: center; margin: 28px 0; }}
            .btn {{ display: inline-block; background-color: #047857; color: #ffffff !important; font-weight: 600; font-size: 14px; text-decoration: none; padding: 12px 28px; border-radius: 10px; }}
            .footer {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 32px; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
            .link-alt {{ word-break: break-all; color: #059669; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="brand">VERIDIX SECURITY</div>
                <div class="title">Permintaan Reset Kata Sandi</div>
            </div>
            <p class="text">Halo,</p>
            <p class="text">Kami menerima permintaan untuk mengatur ulang kata sandi akun VERIDIX Anda. Klik tombol di bawah ini untuk membuat kata sandi baru:</p>
            <div class="btn-wrapper">
                <a href="{reset_link}" class="btn" target="_blank">Atur Ulang Kata Sandi</a>
            </div>
            <p class="text" style="font-size: 13px;">Tautan ini berlaku selama <strong>{expire_minutes} menit</strong> dan hanya dapat digunakan <strong>satu kali</strong>.</p>
            <p class="text" style="font-size: 12px; color: #64748b;">Jika tombol di atas tidak berfungsi, salin dan tempel tautan berikut ke browser:<br>
            <span class="link-alt">{reset_link}</span></p>
            <div class="footer">
                Jika Anda tidak meminta pengaturan ulang kata sandi, abaikan email ini.<br>
                &copy; 2026 VERIDIX AI Verification System.
            </div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Menghubungkan secara langsung ke IPv4 Gmail Port 465
        with IPv4SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"Email reset password berhasil dikirim ke {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"\n[ERROR AUTHENTICATION]: Google menolak login. Pastikan App Password 16 huruf sudah benar dan Verifikasi 2 Langkah aktif di akun pengirim: {smtp_user}. Detail: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR DETAIL]: {type(e).__name__} - {e}")
        return False