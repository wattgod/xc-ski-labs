"""XC Ski Labs exit interview in a real 390px browser."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "wordpress"))

from generate_exit_interview import WORKER_URL, generate_page  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None


def _has_chromium():
    if sync_playwright is None:
        return False
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _has_chromium(), reason="playwright or Chromium not installed")
PAGE_URL = "https://xcskilabs.com/coaching/exit/"


def _run(worker_status=200, *, storage_disabled=False, stale_identity=False):
    captured = {}

    def handle(route):
        request = route.request
        if request.url.startswith(PAGE_URL):
            captured.setdefault("page_requests", []).append(request.url)
            return route.fulfill(status=200, content_type="text/html", body=generate_page())
        if request.url.startswith("https://www.googletagmanager.com/"):
            return route.fulfill(status=200, content_type="text/javascript",
                                 body="window.__gaLocation=window.location.href")
        if request.url.startswith(WORKER_URL):
            captured["worker"] = json.loads(request.post_data)
            return route.fulfill(status=worker_status, content_type="application/json",
                                 body=json.dumps({"success": worker_status == 200}))
        return route.abort()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        if storage_disabled:
            page.add_init_script("Storage.prototype.setItem=function(){throw new Error('blocked')}")
        if stale_identity:
            page.add_init_script("""if(location.hostname==='xcskilabs.com'&&!sessionStorage.getItem('seeded')){
              localStorage.setItem('xcskilabs_athlete_exit_v1',JSON.stringify({name:'Old Skier',email:'old@example.com',athlete:'old-skier'}));
              sessionStorage.setItem('seeded','yes');
            }""")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/*", handle)
        page.goto(PAGE_URL + "?utm_source=coach#?name=Test+Skier&email=test%40example.com&athlete=test-skier")
        page.wait_for_function("() => window.__gaLocation !== undefined")
        address = {"href": page.url, "ga": page.evaluate("window.__gaLocation")}
        prefilled = {key: page.input_value(f"#{key}") for key in ("name", "email", "athlete")}
        prefilled_after_reload = prefilled
        if not storage_disabled:
            page.reload()
            page.wait_for_function("() => window.__gaLocation !== undefined")
            prefilled_after_reload = {
                key: page.input_value(f"#{key}") for key in ("name", "email", "athlete")
            }
        page.click('label.gl-choice:has(input[name="exit_reason"][value="time"])')
        page.focus('input[name="recommend"][value="0"]')
        for _ in range(8):
            page.keyboard.press("ArrowRight")
        page.fill("#change_one", "x" * 4100)
        capped = len(page.input_value("#change_one"))
        layout = page.evaluate("""() => {
          const scale=[...document.querySelectorAll('.gl-exit-scale-option')].map(e=>e.getBoundingClientRect());
          return {innerWidth,scrollWidth:document.documentElement.scrollWidth,count:scale.length,
            tops:scale.map(r=>Math.round(r.top)),left:Math.min(...scale.map(r=>r.left)),
            right:Math.max(...scale.map(r=>r.right)),minWidth:Math.min(...scale.map(r=>r.width)),
            minHeight:Math.min(...scale.map(r=>r.height)),picked:document.querySelector('input[name="recommend"]:checked')?.value};
        }""")
        page.click("#exit-submit")
        if worker_status == 200:
            page.wait_for_selector("#exit-success:not([hidden])")
        else:
            page.wait_for_selector("#message.error")
        was_success = page.is_visible("#exit-success")
        was_form = page.is_visible("#exit-form")
        post_success = None
        if worker_status == 200:
            page.reload()
            post_success = {
                key: page.input_value(f"#{key}") for key in ("name", "email", "athlete")
            }
        result = {"captured": captured, "errors": errors, "address": address, "prefilled": prefilled,
                  "prefilled_after_reload": prefilled_after_reload, "post_success": post_success,
                  "capped": capped, "layout": layout,
                  "success": was_success, "form": was_form,
                  "message": page.inner_text("#message")}
        browser.close()
        return result


@pytest.fixture(scope="module")
def run():
    return _run()


def test_submission_and_private_link(run):
    assert run["errors"] == []
    assert run["prefilled"] == {"name": "Test Skier", "email": "test@example.com", "athlete": "test-skier"}
    assert run["prefilled_after_reload"] == run["prefilled"]
    assert "name=" not in run["address"]["href"] and "email=" not in run["address"]["ga"]
    assert run["address"]["href"].endswith("?utm_source=coach")
    assert all("name=" not in url and "email=" not in url and "athlete=" not in url
               for url in run["captured"]["page_requests"])
    body = run["captured"]["worker"]
    assert body["source"] == "athlete_exit" and body["brand"] == "xcskilabs"
    assert body["goal_answers"]["recommend"] == "8"
    assert run["success"] and not run["form"] and run["capped"] == 4000
    assert run["post_success"] == {"name": "", "email": "", "athlete": ""}


def test_mobile_layout(run):
    layout = run["layout"]
    assert layout["scrollWidth"] <= layout["innerWidth"] == 390
    assert layout["count"] == 11 and len(set(layout["tops"])) == 1
    assert layout["left"] >= 0 and layout["right"] <= 390
    assert layout["minWidth"] >= 24 and layout["minHeight"] >= 44
    assert layout["picked"] == "8"


def test_failure_preserves_the_form_and_never_shows_success():
    failed = _run(worker_status=503)
    assert failed["captured"]["worker"]
    assert not failed["success"] and failed["form"]
    assert "saved in this browser" in failed["message"]


def test_personal_link_overrides_stale_identity():
    result = _run(stale_identity=True)
    assert result["prefilled"] == {
        "name": "Test Skier", "email": "test@example.com", "athlete": "test-skier",
    }
    assert result["captured"]["worker"]["athlete"] == "test-skier"


def test_storage_failure_message_does_not_promise_a_saved_draft():
    failed = _run(worker_status=503, storage_disabled=True)
    assert "could not save a draft" in failed["message"]
    assert "answers are saved" not in failed["message"]
