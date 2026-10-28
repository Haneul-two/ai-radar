"""링커리어(linkareer.com) 공모전 목록 + 상세. 기업 단독 챌린지(예: LOTTE AX CHALLENGE)가 일찍 올라오는 모음 사이트다.
목록·상세 모두 서버 렌더링 __NEXT_DATA__의 Apollo 캐시에 있다. 목록은 접수중(OPEN)만, 최신 등록순.
광고 영역 Activity도 캐시에 섞여 있으므로 activities 쿼리 노드에 든 항목만 읽는다. 마감 시각은 epoch ms(KST 23:59:59.999)."""
import json
from datetime import datetime

from bs4 import BeautifulSoup

from .. import rules
from ..errors import FetchError, StructureError
from ..urlsafe import is_safe_https_url
from .base import CollectResult, domestic_region, fail_if_every_fetch_failed
from .dacon import infer_mode

SOURCE_ID = "linkareer"
SOURCE_NAME = "링커리어"
SOURCE_URL = "https://linkareer.com/list/contest"
PAGE_LIMIT = 40  # 접수중 공모전 약 660건(2026-10) ÷ 20건. 빈/반복 페이지에서 먼저 멈춘다
ITEM_LIMIT = 120  # 상세 조회 하드 상한(2026-10 AI 후보 약 90건). --max-items가 더 작으면 그 값
_LIST = "https://linkareer.com/list/contest?filterType=CATEGORY&orderBy_direction=DESC&orderBy_field=CREATED_AT&page={page}"


def page_url(page):
    return _LIST.format(page=page)


def detail_url(act_id):
    return f"https://linkareer.com/activity/{act_id}"


def _state(text):
    script = BeautifulSoup(text, "html.parser").find("script", id="__NEXT_DATA__")
    try:
        state = json.loads(script.string)["props"]["pageProps"]["__APOLLO_STATE__"] if script else None
    except (ValueError, KeyError, TypeError) as exc:
        raise StructureError(f"링커리어 __NEXT_DATA__ 파싱 실패: {exc}") from exc
    if not isinstance(state, dict):
        raise StructureError("링커리어 페이지에 Apollo 캐시가 없음")
    return state


def _kst_iso(ms):
    if not isinstance(ms, int) or isinstance(ms, bool):
        return None
    return datetime.fromtimestamp(ms / 1000, rules.SEOUL).replace(microsecond=0).isoformat()


def parse_listing(text):
    state = _state(text)
    query = next((v for k, v in (state.get("ROOT_QUERY") or {}).items() if k.startswith("activities(")), None)
    if not isinstance(query, dict) or not isinstance(query.get("nodes"), list):
        raise StructureError("링커리어 목록에 activities 쿼리 결과가 없음")
    rows = []
    for node in query["nodes"]:
        act = state.get((node or {}).get("__ref", ""), {})
        if act.get("id") and act.get("title"):
            rows.append({"id": str(act["id"]), "title": act["title"], "closeAt": act.get("recruitCloseAt")})
    if query["nodes"] and not rows:
        raise StructureError("링커리어 목록 노드에서 제목을 읽지 못함")
    return rows


def parse_detail(text, act_id):
    state = _state(text)
    act = state.get(f"Activity:{act_id}")
    if not isinstance(act, dict) or not act.get("title"):
        raise StructureError(f"링커리어 상세에 Activity:{act_id}가 없음")
    names = lambda key: [state.get(r.get("__ref", ""), {}).get("name") for r in act.get(key) or [] if isinstance(r, dict)]  # noqa: E731
    reward = act.get("tenThousandUnitOfReward")
    start = _kst_iso(act.get("recruitStartAt"))
    homepage = act.get("homepageURL")
    return {
        "title": act["title"], "organizer": act.get("organizationName"), "closeAt": act.get("recruitCloseAt"),
        "registrationStartDate": start[:10] if start else None, "deadlineAt": _kst_iso(act.get("recruitCloseAt")),
        "eligibility": ", ".join(n for n in names("targets") if n) or None, "interests": [n for n in names("interests") if n],
        "prize": f"총 상금 {reward:,}만원" if isinstance(reward, int) and reward > 0 else None,
        "homepage": homepage if is_safe_https_url(homepage) else None,
    }


def build_raw(row, detail):
    title = row["title"]
    mode = infer_mode(title, "")
    page = detail_url(row["id"])
    return {
        "kind": rules.classify_kind(title, "contest"), "title": title, "organizer": detail["organizer"],
        "description": "링커리어에 등록된 공모전" + (f". 분야: {', '.join(detail['interests'])}" if detail["interests"] else ""),
        "tags": ["AI", *detail["interests"]], "mode": mode, "region": domestic_region(mode), "country": "KR",
        "startDate": None, "endDate": None, "registrationStartDate": detail["registrationStartDate"],
        "deadlineDate": None, "deadlineAt": detail["deadlineAt"],
        "eligibility": detail["eligibility"] or rules.UNKNOWN_TEXT, "eligibilityVerified": bool(detail["eligibility"]),
        "fee": rules.UNKNOWN_TEXT, "prize": detail["prize"], "url": detail["homepage"] or page, "sourceUrl": page,
        "sourceName": SOURCE_NAME, "dateNote": "링커리어 등록 접수 기간 기준. 세부 일정은 공고 원문 확인 필요" if detail["deadlineAt"] else "접수 마감 확인 필요",
        "sourceStatus": "open",  # 목록은 접수중(OPEN) 필터 결과다
    }


def item_limit(max_items):
    return ITEM_LIMIT if max_items is None else max(0, min(max_items, ITEM_LIMIT))


def _is_candidate(row):
    return rules.is_ai_related(row["title"]) and rules.classify_kind(row["title"], "contest")


def collect(fetcher, now, max_items=None):
    limit = item_limit(max_items)
    rows, seen, pages_read = [], set(), 0
    for page in range(1, PAGE_LIMIT + 1):
        if len(rows) >= limit:
            break
        # 이후 페이지 오류도 소스 실패로 넘겨 부분 결과가 완전 성공으로 보이지 않게 한다
        listing = parse_listing(fetcher.get(page_url(page)).text)
        pages_read += 1
        new = [r for r in listing if r["id"] not in seen]
        if not new:
            break  # 빈 페이지이거나 이미 본 페이지 반복
        seen.update(r["id"] for r in new)
        rows.extend(r for r in new if _is_candidate(r))
    rows = rows[:limit]
    items, failures = [], []
    for row in rows:
        try:
            detail = parse_detail(fetcher.get(detail_url(row["id"])).text, row["id"])
            if detail["closeAt"] != row["closeAt"]:
                raise StructureError(f"링커리어 목록 마감과 상세 마감이 다름({row['id']})")
        except (FetchError, StructureError) as exc:
            failures.append(exc)
            continue
        items.append(build_raw(row, detail))
    fail_if_every_fetch_failed(len(rows), failures, "링커리어")
    return CollectResult(items, f"AI 후보 {len(rows)}건({pages_read}페이지 확인) 중 {len(items)}건 사용, 상세 조회·검증 실패 {len(failures)}건")
