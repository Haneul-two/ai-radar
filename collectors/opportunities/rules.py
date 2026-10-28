"""관련성·유형·날짜·자격·마스킹 규칙과 schemaVersion 2 항목 정규화/검증."""
import hashlib
import html
import re
from datetime import date, datetime, timedelta, timezone

from .urlsafe import canonical_url, is_safe_https_url

SEOUL = timezone(timedelta(hours=9))  # 대한민국은 DST가 없어 고정 오프셋으로 충분하다(Windows tzdata 의존 회피)
KINDS = ("event", "contest", "hackathon")
MODES = ("online", "offline", "hybrid", "unknown")
COUNTRIES = ("KR", "GLOBAL")
SOURCE_STATUSES = ("open", "closed", "unknown")
UNKNOWN_TEXT = "확인 필요"
DESCRIPTION_LIMIT = 200
ARCHIVE_DAYS = 90

ITEM_KEYS = (
    "id", "kind", "title", "organizer", "description", "tags", "mode", "region", "country",
    "startDate", "endDate", "registrationStartDate", "deadlineDate", "deadlineAt", "eligibility",
    "eligibilityVerified", "fee", "prize", "url", "sourceUrl", "sourceId", "sourceName",
    "verifiedAt", "dateNote", "sourceStatus", "stale",
)

_AI_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:ai|a\.i\.|llms?|genai|ax)(?![A-Za-z0-9])"  # AX = AI 전환(기업 챌린지 제목에 AI 없이 쓰임)
    r"|인공지능|머신러닝|딥러닝|기계학습|생성형"
    r"|machine learning|deep learning|artificial intelligence|generative",
    re.IGNORECASE,
)
_HACK_RE = re.compile(r"해커톤|해커 톤|hackathon", re.IGNORECASE)
_CONTEST_RE = re.compile(r"공모전|경진대회|경연|콘테스트|챌린지|대회|contest|competition|challenge|datathon", re.IGNORECASE)
_EVENT_RE = re.compile(r"컨퍼런스|콘퍼런스|박람회|세미나|밋업|포럼|엑스포|웨비나|페스타|축제|summit|conference|expo|meetup|seminar|forum|webinar|festa|festival|(?<![a-z])ai day", re.IGNORECASE)
_EXCLUDE_RE = re.compile(r"부트캠프|bootcamp|수강생|교육생|강의|강좌|채용 ?공고|신입 ?채용|경력 ?채용|인턴 ?채용|job opening", re.IGNORECASE)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(r"(?<![\w.-])(?:\+?82[-.\s]?)?\(?0?\d{1,2}\)?[-.\s]?\d{3,4}[-.\s]\d{4}(?![\w-])")
_LONG_DIGITS_RE = re.compile(r"(?<!\d)0\d{9,10}(?!\d)")
CONTACT_PLACEHOLDER = "[연락처 생략]"

_TAG_RE = re.compile(r"<[^>]*>")
_DATE_RE = re.compile(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})$")


def clean_text(value):
    """HTML 태그/엔티티와 공백을 정리한다. 주입 방지를 위해 태그는 전부 제거한다."""
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = _TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def mask_contacts(text):
    text = _EMAIL_RE.sub(CONTACT_PLACEHOLDER, text)
    text = _PHONE_RE.sub(CONTACT_PLACEHOLDER, text)
    return _LONG_DIGITS_RE.sub(CONTACT_PLACEHOLDER, text)


def shorten(text, limit=DESCRIPTION_LIMIT):
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def is_ai_related(title, tags=(), description=""):
    return bool(_AI_RE.search(" ".join([title or "", *(tags or ()), description or ""])))


def is_excluded_title(title):
    """부트캠프·강의·채용 공고. 해커톤/대회/행사 단어가 제목에 있으면 제외하지 않는다(태그는 보지 않는다)."""
    title = title or ""
    if _HACK_RE.search(title) or _CONTEST_RE.search(title) or _EVENT_RE.search(title):
        return False
    return bool(_EXCLUDE_RE.search(title))


def classify_kind(title, default=None):
    if is_excluded_title(title):
        return None
    for regex, kind in ((_HACK_RE, "hackathon"), (_CONTEST_RE, "contest"), (_EVENT_RE, "event")):
        if regex.search(title or ""):
            return kind
    return default


def parse_date(value):
    if not isinstance(value, str):
        return None
    m = _DATE_RE.match(value.strip())
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def parse_iso_datetime(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def seoul_date_from_iso(value):
    parsed = parse_iso_datetime(value)
    return parsed.astimezone(SEOUL).date().isoformat() if parsed else None


_GLOBAL_RE = re.compile(r"all countries|worldwide|world-wide|globally|anywhere in the world|any country")
_SOUTH_RE = re.compile(
    r"(?<!north )(?<!north-)\b(?:south korea|republic of korea|korea|rok)\b"
    r"|(?<![a-z])kr(?![a-z])|(?<![가-힣])(?:대한민국|한국)"
)
_EXCLUSION_RE = re.compile(r"exclud\w*|except\w*|other than")
# 한국 앞에서 제외를 뜻하는 말 / 한국 뒤에서 제외를 뜻하는 말
_NEG_BEFORE_RE = re.compile(r"exclud\w*|except\w*|other than|not eligible|ineligible|no participation|not (?:open|available) to|not permitted|prohibited")
_NEG_AFTER_RE = re.compile(r"\b(?:not eligible|ineligible|(?:is|are) (?:excluded|not allowed|not permitted|not open|prohibited)|cannot participate|no participation)")
_FILLER_LEAD_RE = re.compile(r"(?:(?:standard|certain|some|exceptions?|countries|territories|and|or|the|of|a|an)\b[\s,]*)+")
_NOT_COUNTRY_RE = re.compile(r"\b(?:see|rules?|terms|tbd|tba|etc|details?|below|above|link|official|none|varies)\b")
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[.;])\s+|[;\n]")
_INVITE_ONLY_RE = re.compile(r"\b(?:internal|private)\s+(?:\w+\s+)?(?:competition|contest|hackathon|challenge)\b|\binvite[- ]?only\b", re.IGNORECASE)


def is_invite_only_title(title):
    """제목에 internal/private/invite-only 대회로 드러난 항목. 공개 참가 증거가 아니므로 보수적으로 제외한다."""
    return bool(_INVITE_ONLY_RE.search(title or ""))


def _is_country_list(tail):
    """'(Brazil, Cuba, ...)'처럼 실제 국가명으로 보이는 괄호 목록인가. 'see rules'·TBD·빈 괄호는 아니다."""
    m = re.match(r"\(([^)]*)\)", tail)
    names = [n.strip() for n in m[1].split(",")] if m else []
    return bool(names) and all(re.fullmatch(r"[a-z][a-z .'-]*", n) and not _NOT_COUNTRY_RE.search(n) for n in names)


def korea_allowed(text):
    """한국(남한) 참가 허용 증거 판정. 북한 제외 문구는 한국 제외로 보지 않는다.
    한국에 대한 제외 문맥은 무조건 거부하고, 한국 명시 포함 또는 확인된 제외 목록(한국 없음)을 가진 worldwide만 승인한다."""
    t = (text or "").lower().replace("’", "'")
    t = re.sub(r"korea,\s*democratic people's republic of|democratic people's republic of korea|dprk", "north korea", t)
    t = re.sub(r"korea,\s*republic of", "south korea", t)
    if not t.strip():
        return False
    south = False
    for clause in _CLAUSE_SPLIT_RE.split(t):
        for m in _SOUTH_RE.finditer(clause):
            if _NEG_BEFORE_RE.search(clause[:m.start()]) or _NEG_AFTER_RE.search(clause[m.end():]):
                return False
            south = True
    if south:
        return True
    if not _GLOBAL_RE.search(t):
        return False
    for m in _EXCLUSION_RE.finditer(t):
        rest = t[m.end():].lstrip()
        lead = _FILLER_LEAD_RE.match(rest)
        tail = rest[lead.end():] if lead else rest
        if (lead and not tail.startswith("(")) or (tail.startswith("(") and not _is_country_list(tail)):
            return False  # 'standard exceptions'처럼 제외 국가 목록을 확인할 수 없으면 한국 참가 증거가 아니다
    return True


def _opt_text(value):
    text = mask_contacts(clean_text(value))
    return text or None


def stable_id(source_id, source_url):
    return f"{source_id}-{hashlib.sha1(canonical_url(source_url).encode('utf-8')).hexdigest()[:12]}"


def normalize_item(raw, source_id, verified_at):
    """원시 항목을 schemaVersion 2 항목으로 정규화한다. 계약을 어기면 None."""
    title = mask_contacts(clean_text(raw.get("title")))
    if not title or raw.get("kind") not in KINDS or is_excluded_title(title) or is_invite_only_title(title):
        return None
    tags = []
    for tag in raw.get("tags") or []:
        tag = mask_contacts(clean_text(tag))[:40]
        if tag and tag not in tags:
            tags.append(tag)
    tags = tags[:8]
    description = mask_contacts(clean_text(raw.get("description")))
    if not is_ai_related(title, tags, description):
        return None
    url, source_url = raw.get("url"), raw.get("sourceUrl")
    if not is_safe_https_url(url) or not is_safe_https_url(source_url):
        return None
    mode = raw.get("mode") if raw.get("mode") in MODES else "unknown"
    country = raw.get("country")
    if country not in COUNTRIES:
        return None
    verified = bool(raw.get("eligibilityVerified"))
    if country == "GLOBAL" and (mode != "online" or not verified):
        return None

    dates = {}
    for key in ("startDate", "endDate", "registrationStartDate", "deadlineDate"):
        value = raw.get(key)
        dates[key] = None if value is None else parse_date(value)
        if value is not None and dates[key] is None:
            return None
    deadline_at = raw.get("deadlineAt")
    if deadline_at is not None:
        seoul = seoul_date_from_iso(deadline_at)
        if seoul is None:
            return None
        dates["deadlineDate"] = seoul
        deadline_at = deadline_at.strip()
    if dates["startDate"] and dates["endDate"] and dates["startDate"] > dates["endDate"]:
        return None
    if dates["registrationStartDate"] and dates["deadlineDate"] and dates["registrationStartDate"] > dates["deadlineDate"]:
        return None

    status = raw.get("sourceStatus") if raw.get("sourceStatus") in SOURCE_STATUSES else "unknown"
    # 대체 확인 출처가 바뀌어도 AI EXPO의 기존 행사 ID는 유지한다.
    identity_url = source_url
    if source_id == "devevent" or (source_id == "aiexpo" and source_url.startswith("https://www.showala.com/ex/ex_detail.php?")):
        identity_url = url
    return {
        "id": stable_id(source_id, identity_url),
        "kind": raw["kind"],
        "title": title,
        "organizer": _opt_text(raw.get("organizer")),
        "description": shorten(description or title),
        "tags": tags,
        "mode": mode,
        "region": _opt_text(raw.get("region")) or "미정",
        "country": country,
        "startDate": dates["startDate"],
        "endDate": dates["endDate"],
        "registrationStartDate": dates["registrationStartDate"],
        "deadlineDate": dates["deadlineDate"],
        "deadlineAt": deadline_at,
        "eligibility": shorten(_opt_text(raw.get("eligibility")) or UNKNOWN_TEXT, 300),
        "eligibilityVerified": verified,
        "fee": _opt_text(raw.get("fee")) or UNKNOWN_TEXT,
        "prize": _opt_text(raw.get("prize")),
        "url": url,
        "sourceUrl": source_url,
        "sourceId": source_id,
        "sourceName": _opt_text(raw.get("sourceName")) or source_id,
        "verifiedAt": verified_at,
        "dateNote": _opt_text(raw.get("dateNote")),
        "sourceStatus": status,
        "stale": False,
    }


def validate_item(item):
    """저장된 항목이 계약을 지키는지 엄격히 검사한다. 위반 시 ValueError."""
    if not isinstance(item, dict) or set(item) != set(ITEM_KEYS):
        raise ValueError(f"항목 키가 계약과 다름: {sorted(set(item) ^ set(ITEM_KEYS)) if isinstance(item, dict) else type(item)}")
    for key in ("id", "title", "description", "region", "eligibility", "fee", "sourceId", "sourceName", "verifiedAt"):
        if not isinstance(item[key], str) or not item[key]:
            raise ValueError(f"{key} 문자열 필요")
    for key in ("organizer", "prize", "dateNote"):
        if item[key] is not None and not isinstance(item[key], str):
            raise ValueError(f"{key}는 문자열 또는 null")
    if item["kind"] not in KINDS or item["mode"] not in MODES or item["country"] not in COUNTRIES:
        raise ValueError("kind/mode/country 값 오류")
    if item["sourceStatus"] not in SOURCE_STATUSES:
        raise ValueError("sourceStatus 값 오류")
    if not isinstance(item["tags"], list) or not all(isinstance(t, str) for t in item["tags"]):
        raise ValueError("tags 오류")
    if not isinstance(item["eligibilityVerified"], bool) or not isinstance(item["stale"], bool):
        raise ValueError("boolean 필드 오류")
    for key in ("startDate", "endDate", "registrationStartDate", "deadlineDate"):
        if item[key] is not None and (parse_date(item[key]) != item[key]):
            raise ValueError(f"{key} 날짜 오류: {item[key]!r}")
    if item["deadlineAt"] is not None and seoul_date_from_iso(item["deadlineAt"]) is None:
        raise ValueError("deadlineAt은 시간대 포함 ISO여야 함")
    if parse_iso_datetime(item["verifiedAt"]) is None:
        raise ValueError("verifiedAt 형식 오류")
    for key in ("url", "sourceUrl"):
        if not is_safe_https_url(item[key]):
            raise ValueError(f"{key}는 안전한 https URL이어야 함")


def last_day(item):
    days = [d for d in (item.get("endDate"), item.get("deadlineDate")) if d]
    return max(days) if days else None


def is_archived(item, today):
    """종료일이 서울 기준 오늘보다 이전인 항목."""
    day = last_day(item)
    return day is not None and day < today.isoformat()


def is_expired_archive(item, today):
    """종료 후 ARCHIVE_DAYS를 넘긴 항목(날짜가 없으면 verifiedAt 기준)."""
    cutoff = (today - timedelta(days=ARCHIVE_DAYS)).isoformat()
    day = last_day(item)
    if day is not None:
        return day < cutoff
    verified = parse_iso_datetime(item.get("verifiedAt"))
    return verified is not None and verified.astimezone(SEOUL).date().isoformat() < cutoff


def meets_contract(item):
    """저장된 항목이 지금의 관련성/지역/자격/초대 전용 계약을 여전히 만족하는지(병합 시 stale 보존 차단용)."""
    if normalize_item(item, item["sourceId"], item["verifiedAt"]) is None:
        return False
    return item["country"] != "GLOBAL" or korea_allowed(item["eligibility"])
