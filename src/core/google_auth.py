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
        self._default_timeout = timeout

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self._default_timeout)
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

    sub = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    email_verified = claims.get("email_verified") is True

    if not sub or not email or not email_verified:
        raise GoogleTokenInvalidError(
            "Akun Google tidak memiliki identitas atau email terverifikasi yang valid."
        )

    hosted_domain = str(claims.get("hd") or "").strip()
    is_google_hosted_email = email.endswith(("@gmail.com", "@googlemail.com")) or bool(hosted_domain)

    full_name = str(claims.get("name") or "").strip() or email.split("@")[0]
    avatar_url = str(claims.get("picture") or "").strip() or None
    nonce = str(claims.get("nonce") or "").strip() or None

    return GoogleIdentity(
        sub=sub,
        email=email,
        email_verified=email_verified,
        is_google_hosted_email=is_google_hosted_email,
        full_name=full_name,
        avatar_url=avatar_url,
        nonce=nonce,
    )