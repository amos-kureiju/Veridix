from dataclasses import dataclass
from typing import Optional
import requests
from google.auth.exceptions import GoogleAuthError, TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src.core.config import settings

try:
    from cachecontrol import CacheControl
except ImportError:
    CacheControl = None


class GoogleAuthConfigError(Exception):
    """Konfigurasi GOOGLE_CLIENT_ID belum diatur di server."""


class GoogleServiceUnavailableError(Exception):
    """Gagal menghubungi server Google untuk mengambil kunci publik."""


class GoogleTokenInvalidError(Exception):
    """Token ID Google tidak valid, kedaluwarsa, atau klaim wajib tidak terpenuhi."""


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    is_google_hosted_email: bool
    full_name: str
    avatar_url: Optional[str]
    nonce: Optional[str]


class _TimeoutSession(requests.Session):
    def __init__(self, timeout: float):
        super().__init__()
        self._default_timeout = float(timeout)

    def request(self, method, url, **kwargs):
        # PERBAIKAN: Paksa timeout agar tidak kalah oleh timeout=None atau 120s bawaan transport
        req_timeout = kwargs.get("timeout")
        if req_timeout is None:
            kwargs["timeout"] = self._default_timeout
        else:
            kwargs["timeout"] = min(float(req_timeout), self._default_timeout)
        return super().request(method, url, **kwargs)


_raw_session = _TimeoutSession(timeout=settings.GOOGLE_CERT_TIMEOUT_SECONDS)
_cached_session = CacheControl(_raw_session) if CacheControl is not None else _raw_session
_google_request = google_requests.Request(session=_cached_session)


def verify_google_id_token(credential: str) -> GoogleIdentity:
    client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
    if not client_id:
        raise GoogleAuthConfigError("Login Google belum dikonfigurasi di server.")

    if not credential or not credential.strip():
        raise GoogleTokenInvalidError("Kredensial Google wajib diisi.")

    try:
        claims = id_token.verify_oauth2_token(
            credential.strip(),
            _google_request,
            audience=client_id,
        )
    except (TransportError, requests.RequestException, TimeoutError) as exc:
        raise GoogleServiceUnavailableError(
            "Layanan verifikasi Google sementara tidak tersedia. Silakan coba lagi."
        ) from exc
    except (ValueError, GoogleAuthError) as exc:
        raise GoogleTokenInvalidError(
            "Kredensial Google tidak valid atau sudah kedaluwarsa."
        ) from exc

    issuer = claims.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise GoogleTokenInvalidError("Penerbit token Google tidak valid.")

    raw_sub = claims.get("sub")
    raw_email = claims.get("email")
    email_verified = claims.get("email_verified") is True

    # PERBAIKAN: Pastikan tipe asli adalah string, tidak kosong, dan sesuai batas kolom DB (255)
    if not isinstance(raw_sub, str) or not isinstance(raw_email, str) or not email_verified:
        raise GoogleTokenInvalidError(
            "Akun Google tidak memiliki identitas atau email terverifikasi yang valid."
        )

    sub = raw_sub.strip()
    email = raw_email.strip().lower()

    if not sub or len(sub) > 255 or not email or len(email) > 255 or "@" not in email:
        raise GoogleTokenInvalidError(
            "Format atau panjang identitas akun Google tidak valid."
        )

    raw_hd = claims.get("hd")
    hosted_domain = raw_hd.strip() if isinstance(raw_hd, str) else ""
    is_google_hosted_email = email.endswith(("@gmail.com", "@googlemail.com")) or bool(hosted_domain)

    raw_name = claims.get("name")
    full_name = (raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else email.split("@")[0])[:150]

    raw_picture = claims.get("picture")
    avatar_url = None
    if isinstance(raw_picture, str):
        pic = raw_picture.strip()
        if pic.startswith(("https://", "http://")) and len(pic) <= 500:
            avatar_url = pic

    raw_nonce = claims.get("nonce")
    nonce = raw_nonce.strip() if isinstance(raw_nonce, str) and raw_nonce.strip() else None
    if nonce is not None and len(nonce) > 255:
        raise GoogleTokenInvalidError("Format nonce pada token Google tidak valid.")

    return GoogleIdentity(
        sub=sub,
        email=email,
        email_verified=email_verified,
        is_google_hosted_email=is_google_hosted_email,
        full_name=full_name,
        avatar_url=avatar_url,
        nonce=nonce,
    )