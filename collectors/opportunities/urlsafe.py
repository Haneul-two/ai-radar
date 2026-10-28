"""URL 검증: 공인 HTTPS 443, userinfo 없음, fetch 허용목록, 정규화."""
import ipaddress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ALLOWED_HOST_SUFFIXES = ("devpost.com",)
ALLOWED_HOSTS = {
    "wevity.com", "www.wevity.com", "dacon.io", "www.dacon.io", "aisummit.co.kr", "www.aisummit.co.kr",
    "seochoai.kr", "www.seochoai.kr", "www.nvidia.com", "aifesta.kr", "www.aifesta.kr",
    "www.contestkorea.com", "aiexpo.co.kr", "www.showala.com", "raw.githubusercontent.com", "lotteaxchallenge.com", "linkareer.com",  # 정확한 호스트만(하위 도메인·와일드카드 아님)
}
_TRACKING_PREFIXES = ("utm_",)


def _parts(url):
    if not isinstance(url, str) or not url or url != url.strip():
        return None
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username is not None or parts.password is not None:
        return None
    if port not in (None, 443):
        return None
    return parts


def is_safe_https_url(url):
    parts = _parts(url)
    if parts is None:
        return False
    host = parts.hostname.lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return "." in host


def is_fetch_allowed(url):
    if not is_safe_https_url(url):
        return False
    host = urlsplit(url).hostname.lower()
    if host in ALLOWED_HOSTS:
        return True
    return any(host == s or host.endswith("." + s) for s in ALLOWED_HOST_SUFFIXES)


def canonical_url(url):
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith(_TRACKING_PREFIXES)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(sorted(query)), ""))
