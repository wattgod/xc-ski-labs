"""XC Ski Labs /coaching/exit/ page and its release surface."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "wordpress"))

import generate_exit_interview as exit_page  # noqa: E402


ANSWER_KEYS = {
    "exit_reason", "exit_story", "stay_lever", "recommend", "keep_doing",
    "change_one", "what_changed", "quote", "not_for", "share_as", "age_group",
    "where_site", "where_social", "where_email", "where_tp", "connection",
    "reference", "come_back", "checkin", "need_zones", "need_notes",
    "need_billing", "need_tp", "last_word",
}


def _field_names():
    names = set()
    for section in exit_page.SECTIONS:
        for field in section["fields"]:
            fields = field.get("fields", [field])
            for item in fields:
                if item["kind"] == "checks":
                    names.update(value for value, _ in item["options"])
                elif item["kind"] != "note":
                    names.add(item["name"])
    return names


def test_form_reproduces_every_exit_answer():
    assert _field_names() == ANSWER_KEYS | {"name", "email", "athlete"}


def test_worker_submission_is_xc_scoped_and_storage_required():
    page = exit_page.generate_page()
    assert "source:'athlete_exit'" in page
    assert "brand:'xcskilabs'" in page
    assert exit_page.WORKER_URL in page
    assert "if(!response.ok)throw new Error('worker failed')" in page
    assert "localStorage.removeItem(STORAGE_KEY)" in page
    assert "formsubmit.co" not in page.lower()


def test_brand_language_and_print_tokens_are_xc_specific():
    page = exit_page.generate_page()
    assert "XC Ski Labs social posts" in page
    assert "xcskilabs.com" in page
    assert "Emails to skiers thinking about coaching" in page
    assert "If a skier asked" in page
    assert "Or skiing off a plan" in page
    assert "Roadie Labs social posts" not in page
    assert "var(--gl-paper)" in page and "var(--gl-rust)" in page
    assert "border-radius" not in exit_page.build_exit_css()
    assert "box-shadow" not in exit_page.build_exit_css()


def test_private_link_is_stripped_before_analytics_and_page_is_not_indexed():
    page = exit_page.generate_page()
    assert page.index("history.replaceState") < page.index('/xc-assets/analytics.js')
    assert "window.location.hash" in page
    assert "new URLSearchParams(window.location.search)" not in exit_page.personal_link_js()
    assert '<meta name="robots" content="noindex, nofollow">' in page
    assert 'href="https://xcskilabs.com/coaching/exit/"' in page


def test_answer_limits_and_mobile_score_row():
    page = exit_page.generate_page()
    assert f'maxlength="{exit_page.MAX_ANSWER_LEN}"' in page
    for score in range(11):
        assert f'name="recommend" value="{score}"' in page
    assert "overflow-x:auto" in page


def test_generator_writes_the_deploy_artifact(tmp_path):
    old = sys.argv
    try:
        sys.argv = ["generate_exit_interview.py", "--output-dir", str(tmp_path)]
        exit_page.main()
    finally:
        sys.argv = old
    output = tmp_path / "index.html"
    assert output.exists() and "Before You Go" in output.read_text()


def test_release_script_exposes_a_scoped_exit_sync():
    source = (ROOT / "scripts" / "deploy.py").read_text()
    preflight = (ROOT / "scripts" / "preflight.py").read_text()
    assert '"coaching-exit"' in source
    assert '"coaching-exit"' in preflight
    assert "def sync_exit_interview(" in source
    assert '"--sync-exit-interview"' in source
    assert '"coaching/exit"' in source
