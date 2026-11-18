"""iCalendar(RFC 5545) VEVENT 최소 읽기. 루마 공식 구독 피드용이며 반복 규칙(RRULE)은 해석하지 않는다."""
from datetime import datetime, timezone

from .. import rules
from ..errors import StructureError


def _unfold(text):
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line[:1] in (" ", "\t") and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _unescape(value):
    out, i = [], 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append("\n" if nxt in "nN" else nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_moment(value, params):
    """DTSTART/DTEND 값 → 한국 시각 datetime. UTC(Z)·날짜(VALUE=DATE)·TZID=Asia/Seoul만 받고 나머지는 None."""
    try:
        if params.get("VALUE") == "DATE" or len(value) == 8:
            day = datetime.strptime(value, "%Y%m%d")
            return day.replace(tzinfo=rules.SEOUL)
        if value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(rules.SEOUL)
        if params.get("TZID") == "Asia/Seoul":
            return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=rules.SEOUL)
    except ValueError:
        return None
    return None


def parse_events(text):
    """VCALENDAR 텍스트 → [{NAME: (value, params)}]. VCALENDAR가 아니면 구조 오류."""
    lines = _unfold(text)
    if not any(line.strip() == "BEGIN:VCALENDAR" for line in lines):
        raise StructureError("iCal 피드가 아님(BEGIN:VCALENDAR 없음)")
    events, current = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *raw_params = head.split(";")
            params = dict(p.split("=", 1) for p in raw_params if "=" in p)
            current.setdefault(name.upper(), (_unescape(value), params))
    return events
