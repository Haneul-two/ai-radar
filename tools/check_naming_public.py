"""Verify AI Radar's renamed public site against the local deployed dataset."""
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://haneul-two.github.io/ai-radar/"


def main():
    public = {}
    for name in ("opportunities.json", "ingest-status.json"):
        response = requests.get(BASE + "data/" + name, timeout=30)
        response.raise_for_status()
        assert response.url.startswith(BASE)
        public[name] = response.json()
        local = json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
        assert public[name] == local, "Public and local dataset differ"
    status = public["ingest-status.json"]
    assert len(status["sources"]) == 10 and all(s["status"] == "ok" for s in status["sources"])
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for width in (1440, 390):
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("requestfailed", lambda r: errors.append(r.url))
            page.goto(BASE, wait_until="networkidle")
            expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
            assert page.title() == "AI 행사 모아보기"
            assert page.locator(".brand").inner_text().replace("\n", " ").strip() == "AI Radar"
            assert page.locator(".opp").count() > 0
            assert page.locator("#notices").inner_text().strip() == ""
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            count_text = page.locator("#result-count").inner_text()
            page.screenshot(path=str(ROOT / "docs/evidence" / f"naming-public-{width}.png"))
            page.goto(BASE + "?q=AI%20EXPO", wait_until="networkidle")
            expect(page.locator("#content")).to_have_attribute("aria-busy", "false")
            assert page.locator(".opp").count() > 0
            assert page.locator("#q").input_value() == "AI EXPO"
            assert page.locator(".opp[data-id='aiexpo-119c9024b15a']").count() == 1
            checks.append({"width": width, "titleAndBrand": True, "noticesEmpty": True,
                           "resultCount": count_text, "search": True, "overflow": False})
            page.close()
        browser.close()
    assert not errors, errors
    result = {"checkedAt": datetime.now(timezone.utc).isoformat(), "url": BASE,
              "datasetUpdatedAt": public["opportunities.json"]["updatedAt"],
              "storedItems": len(public["opportunities.json"]["items"]),
              "sourceStatuses": {s["id"]: s["status"] for s in status["sources"]},
              "checks": checks, "errors": errors}
    (ROOT / "docs/evidence/naming-production.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
