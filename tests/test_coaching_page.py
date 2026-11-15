#!/usr/bin/env python3
"""
XC Ski Labs: tests for the /coaching/ landing page ("Field Notes").

Rebuilt 2026-11-15 on Gravel God's Field Notes structure, in the Sledge
Stores brand: hero + ID card (real photo crossfading to the v6.7 xc-outfit
cartoon) -> fit -> what you get -> a week with me -> how it works ->
levels with the 3-question picker -> FAQ -> close. Section ids, data-cta
names and the image upload order match Gravel God's coaching page.

Run: pytest tests/test_coaching_page.py -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
OUTPUT_DIR = PROJECT_ROOT / "output"

sys.path.insert(0, str(WORDPRESS_DIR))

import generate_coaching  # noqa: E402
from generate_coaching import (  # noqa: E402
    APPLY_URL,
    GA4_ID,
    HERO_H1,
    HERO_SUB,
    ID_BIO,
    ID_ROWS,
    IMAGES,
    IMG_SRC_DIR,
    PICKER_QUESTIONS,
    SITE_BASE_URL,
    TIERS,
    build_nav,
    build_footer,
    build_hero,
    build_id_card,
    build_fit,
    build_terms,
    build_week,
    build_how_it_works,
    build_fit_check,
    build_tiers,
    build_faq,
    build_close,
    build_mobile_sticky_cta,
    build_page_js,
    build_jsonld,
    build_css,
    generate_page,
    write_coaching_images,
)

SECTION_IDS = ("hero", "fit", "terms", "week", "how-it-works", "tiers", "faq", "final-cta")


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def coaching_html(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("coaching-out")
    path = generate_page(output_dir=out_dir)
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def coaching_css():
    return build_css()


def _visible_text(html_doc: str) -> str:
    """Strip <script> and <style> blocks, then the remaining tags, leaving
    only what a reader actually sees."""
    no_script = re.sub(r"<script.*?</script>", "", html_doc, flags=re.DOTALL)
    no_style = re.sub(r"<style.*?</style>", "", no_script, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", "", no_style)


# ── Page generation ──────────────────────────────────────────────


class TestPageGeneration:
    def test_generator_runs_clean(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_coaching.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"generate_coaching.py failed: {result.stderr[-500:]}"
        assert (OUTPUT_DIR / "coaching" / "index.html").exists()

    def test_returns_html(self, coaching_html):
        assert "<!DOCTYPE html>" in coaching_html

    def test_has_canonical(self, coaching_html):
        assert 'rel="canonical"' in coaching_html
        assert f"{SITE_BASE_URL}/coaching/" in coaching_html

    def test_has_robots_index_follow(self, coaching_html):
        assert 'name="robots"' in coaching_html
        assert 'content="index, follow"' in coaching_html

    def test_has_meta_description(self, coaching_html):
        assert 'name="description"' in coaching_html

    def test_has_title(self, coaching_html):
        assert "<title>" in coaching_html
        assert "Coaching" in coaching_html


# ── GA4 + consent ────────────────────────────────────────────────


class TestGA4AndConsent:
    def test_ga4_present(self, coaching_html):
        assert GA4_ID in coaching_html
        assert "googletagmanager.com" in coaching_html

    def test_ga4_in_head(self, coaching_html):
        head = coaching_html.split("</head>")[0]
        assert GA4_ID in head

    def test_consent_gated(self, coaching_html):
        assert "xl_consent" in coaching_html

    def test_consent_banner_accept_decline(self, coaching_html):
        assert "xl-consent-banner" in coaching_html
        assert "Accept" in coaching_html
        assert "Decline" in coaching_html

    def test_consent_sets_cookie(self, coaching_html):
        assert "xl_consent=accepted" in coaching_html
        assert "xl_consent=declined" in coaching_html


# ── JSON-LD ──────────────────────────────────────────────────────


class TestJSONLD:
    def test_has_jsonld(self, coaching_html):
        assert 'application/ld+json' in coaching_html
        assert '"@type":"WebPage"' in coaching_html
        assert '"@type":"Service"' in coaching_html

    def test_jsonld_references_coaching_url(self):
        ld = build_jsonld()
        assert f"{SITE_BASE_URL}/coaching/" in ld

    def test_uses_safe_json_for_script(self):
        """A '</script>' payload must never be able to break out of the
        <script> tag (repo pitfall #4)."""
        from generate_coaching import _safe_json_for_script
        payload = {"a": "</script><script>alert(1)</script>"}
        safe = _safe_json_for_script(payload)
        assert "</script>" not in safe


# ── Hero ─────────────────────────────────────────────────────────



# ── Structure (matches Gravel God's Field Notes page) ───────────


class TestStructure:
    def test_sections_in_order(self, coaching_html):
        positions = [coaching_html.find(f'id="{sid}"') for sid in SECTION_IDS]
        assert all(p > 0 for p in positions), dict(zip(SECTION_IDS, positions))
        assert positions == sorted(positions)

    def test_numbered_section_heads(self, coaching_html):
        for num, title in (("01", "Fit check"), ("02", "What you get"), ("03", "A week with me"),
                           ("04", "How it works"), ("05", "Levels and prices"), ("06", "Questions")):
            assert f'<span class="gl-coach-sec-num">{num}</span><h2 class="gl-coach-sec-title">{title}</h2>' in coaching_html

    def test_one_h1(self, coaching_html):
        assert coaching_html.count("<h1") == 1

    def test_no_placeholder_proof_or_capacity_sections(self, coaching_html):
        visible = _visible_text(coaching_html).lower()
        for word in ("placeholder", "not built", "proof slot", "spots left", "capacity", "coming soon", "lorem"):
            assert word not in visible, word
        for sid in ("proof", "results", "capacity", "honest-check", "problem", "deliverables"):
            assert f'id="{sid}"' not in coaching_html


class TestHero:
    def test_headline_and_sub_unchanged(self):
        assert HERO_H1 == "Ski coaching for people who&rsquo;ll roller ski in July to pass people in February."
        assert HERO_SUB.startswith("I plan your dryland and your snow weeks around your races")
        assert HERO_SUB.endswith("From $199 every 4 weeks.")
        hero = build_hero()
        assert f"<h1>{HERO_H1}</h1>" in hero
        assert HERO_SUB in hero

    def test_hero_cta(self):
        hero = build_hero()
        assert f'href="{APPLY_URL}"' in hero
        assert 'data-cta="hero_apply"' in hero
        assert "I reply within 48 hours." in hero

    def test_hero_holds_id_card(self):
        assert 'class="gl-coach-id"' in build_hero()


class TestIdCard:
    def test_bio_line(self):
        assert ID_BIO == "I&rsquo;m Matti Rowe. Peddler of skis, bikes and hot takes, and really fast clients."
        assert f'<p class="gl-coach-id-bio">{ID_BIO}</p>' in build_id_card()

    def test_rows_are_public_facts(self):
        card = build_id_card()
        labels = [label for label, _ in ID_ROWS]
        assert labels == ["Skis", "Day job", "Bikes", "Team", "Talent"]
        for label, value in ID_ROWS:
            assert f"<dt>{label}</dt><dd>{value}</dd>" in card
        assert "Twelve years at TrainingPeaks" in card
        assert "Cat 1" in card

    def test_no_invented_ski_results(self):
        text = " ".join(v for _, v in ID_ROWS).lower()
        for word in ("finish", "podium", "place", "win", "won", "birkie", "vasaloppet", "medal"):
            assert not re.search(rf"\b{word}\b", text), word

    def test_photo_and_cartoon(self):
        card = build_id_card()
        assert 'class="gl-coach-id-real" src="/coaching/img/matti-pizza.webp"' in card
        assert 'class="gl-coach-id-toon" src="/coaching/img/matti-pizza-xc.webp"' in card
        # The real photo carries the description; the cartoon is decoration.
        assert re.search(r'gl-coach-id-real"[^>]*alt="[^"]{20,}"', card)
        assert re.search(r'gl-coach-id-toon"[^>]*alt="" aria-hidden="true"', card)
        assert 'width="720" height="960"' in card

    def test_photo_is_preloaded(self, coaching_html):
        head = coaching_html.split("</head>")[0]
        assert '<link rel="preload" as="image" href="/coaching/img/matti-pizza.webp">' in head


class TestImages:
    @pytest.mark.parametrize("key", ["photo", "cartoon"])
    def test_image_exists_at_its_size(self, key):
        from PIL import Image
        name, w, h = IMAGES[key]
        path = IMG_SRC_DIR / name
        assert path.is_file(), path
        with Image.open(path) as im:
            assert im.format == "WEBP"
            assert im.size == (w, h) == (720, 960)

    def test_cartoon_is_opaque(self):
        """A transparent cartoon lets the photo show through mid-crossfade."""
        from PIL import Image
        with Image.open(IMG_SRC_DIR / IMAGES["cartoon"][0]) as im:
            assert im.mode == "RGB" or im.getextrema()[3][0] == 255

    def test_write_copies_every_image(self, tmp_path):
        dest = write_coaching_images(tmp_path)
        assert dest == tmp_path / "coaching" / "img"
        for name, _w, _h in IMAGES.values():
            assert (dest / name).read_bytes() == (IMG_SRC_DIR / name).read_bytes()

    def test_generate_page_writes_images(self, tmp_path):
        generate_page(output_dir=tmp_path)
        for name, _w, _h in IMAGES.values():
            assert (tmp_path / "coaching" / "img" / name).is_file()

    def test_missing_image_refuses(self, tmp_path, monkeypatch):
        src = tmp_path / "src"
        src.mkdir()
        shutil.copy2(IMG_SRC_DIR / IMAGES["photo"][0], src / IMAGES["photo"][0])
        monkeypatch.setattr(generate_coaching, "IMG_SRC_DIR", src)
        with pytest.raises(FileNotFoundError):
            write_coaching_images(tmp_path / "out")


class TestCrossfade:
    def test_swap_animation(self, coaching_css):
        assert "@keyframes gl-coach-idswap" in coaching_css
        assert re.search(r"\.gl-coach-id-toon \{[^}]*animation: gl-coach-idswap", coaching_css)

    def test_reduced_motion_shows_the_photo_only(self, coaching_css):
        blocks = re.findall(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", coaching_css, re.S)
        assert any(re.search(r"\.gl-coach-id-toon \{[^}]*animation: none;[^}]*opacity: 0;", b) for b in blocks)

    def test_without_animation_the_photo_shows(self, coaching_css):
        # The cartoon starts hidden; only the keyframes bring it in.
        assert re.search(r"\.gl-coach-id-toon \{ opacity: 0;", coaching_css)


class TestFit:
    def test_fit_lists(self):
        fit = build_fit()
        assert 'id="fit"' in fit
        assert "Coaching fits if" in fit
        assert "Probably not a fit if" in fit
        assert fit.count("gl-coach-mark--yes") == 3
        assert fit.count("gl-coach-mark--no") == 3


class TestTerms:
    def test_five_items(self):
        terms = build_terms()
        assert 'id="terms"' in terms
        assert len(re.findall(r'<p class="gl-coach-label">0\d</p>', terms)) == 5
        assert "I read your sessions." in terms


class TestWeek:
    def test_three_level_columns(self):
        week = build_week()
        assert 'id="week"' in week
        for _key, name, _price in TIERS:
            assert f"<h3>{name}</h3>" in week
        assert "A thaw, a cold, a trip" in week


class TestHowItWorks:
    def test_five_steps(self):
        how = build_how_it_works()
        assert 'id="how-it-works"' in how
        assert len(re.findall(r'class="gl-coach-num">0\d<', how)) == 5
        assert "48 hours" in how


class TestTiers:
    def test_three_crates(self):
        tiers = build_tiers()
        assert 'id="tiers"' in tiers
        for key, name, price in TIERS:
            assert f'data-tier="{key}"' in tiers
            assert f'<p class="xc-price">{price}</p>' in tiers
            assert f'href="{APPLY_URL}?tier={key}"' in tiers
            assert f'data-cta="tier_{key}"' in tiers
        assert tiers.count('class="xc-crate gl-coach-tier"') == 3
        assert tiers.count("every 4 weeks") >= 3

    def test_no_crate_is_salmon_before_the_picker_answers(self):
        """One salmon object per page (Sledge Stores): the picker marks it."""
        assert "xc-crate--splash" not in build_tiers()

    def test_ribbon_shows_only_on_the_marked_crate(self, coaching_css):
        assert ".gl-coach-crates .xc-ribbon { display: none; }" in coaching_css
        assert ".gl-coach-crates .xc-crate--splash .xc-ribbon { display: block; }" in coaching_css

    def test_setup_fee_and_cancelling(self):
        tiers = build_tiers()
        assert "$99 setup fee" in tiers
        assert "No cancellation fee." in tiers


class TestPicker:
    def test_picker_is_hidden_without_js(self):
        picker = build_fit_check()
        assert '<form class="gl-coach-picker" id="gl-coach-picker"' in picker
        assert re.search(r'id="gl-coach-picker"[^>]*hidden>', picker)
        assert re.search(r'id="gl-coach-picker-out"[^>]*hidden>', picker)

    def test_three_questions_three_answers(self):
        picker = build_fit_check()
        assert len(PICKER_QUESTIONS) == 3
        for qi, (_text, options) in enumerate(PICKER_QUESTIONS, start=1):
            assert len(options) == 3
            for ai in (1, 2, 3):
                assert f'name="gl-coach-q{qi}" value="{ai}"' in picker

    def test_all_27_combinations(self):
        """Run the page's own script under node with a stub DOM."""
        js = build_page_js().replace("<script>", "").replace("</script>", "")
        harness = r"""
const answers = {};
let onChange = null;
const marked = {};
const crates = ['min', 'mid', 'max'].map(t => ({
  getAttribute: () => t,
  classList: { toggle: (c, on) => { if (c === 'xc-crate--splash') marked[t] = on; } },
}));
const form = {
  hidden: true,
  addEventListener: (ev, fn) => { onChange = fn; },
  querySelector: sel => { const q = sel.match(/q(\d)/)[1]; return answers[q] ? { value: String(answers[q]) } : null; },
};
const out = { hidden: true, textContent: '' };
global.document = {
  querySelectorAll: sel => sel.indexOf('gl-coach-tier') !== -1 ? crates : [],
  getElementById: id => id === 'gl-coach-picker' ? form : id === 'gl-coach-picker-out' ? out : null,
};
""" + js + r"""
const res = [];
for (const a of [1, 2, 3]) for (const b of [1, 2, 3]) for (const c of [1, 2, 3]) {
  answers[1] = a; answers[2] = b; answers[3] = c;
  onChange({ target: { name: 'gl-coach-q3', value: String(c) } });
  res.push({ tier: Object.keys(marked).filter(k => marked[k]), label: out.textContent });
}
console.log(JSON.stringify({ shown: !form.hidden && !out.hidden, res }));
"""
        node = shutil.which("node")
        if not node:
            pytest.skip("node not installed")
        run = subprocess.run([node, "-e", harness], capture_output=True, text=True, timeout=30)
        assert run.returncode == 0, run.stderr
        data = json.loads(run.stdout)
        assert data["shown"] is True
        names = {1: "min", 2: "mid", 3: "max"}
        prices = {key: price for key, _n, price in TIERS}
        display = {key: n for key, n, _p in TIERS}
        combos = [(a, b, c) for a in (1, 2, 3) for b in (1, 2, 3) for c in (1, 2, 3)]
        for (a, b, c), got in zip(combos, data["res"]):
            # Three integers over 3 never land on .5, so round() agrees with Math.round.
            want = names[round((a + b + c) / 3)]
            assert got["tier"] == [want], (a, b, c, got)
            assert got["label"] == f"I’d pick {display[want]}: {prices[want]} every 4 weeks."

    def test_picker_events(self):
        js = build_page_js()
        assert "coaching_fitcheck_answer" in js
        assert "coaching_fitcheck_result" in js
        assert "coaching_faq_open" in js
        assert "'cta_click'" in js


class TestFAQ:
    def test_native_disclosure(self):
        faq = build_faq()
        assert 'id="faq"' in faq
        assert faq.count('<details class="gl-coach-faq-item">') == 9
        assert 'role="button"' not in faq

    def test_first_answer_is_the_reply_time(self):
        assert "You hear back from me within 48 hours, yes or no, with the reason." in build_faq()


class TestClose:
    def test_close(self):
        close = build_close()
        assert 'id="final-cta"' in close
        assert "<h2>Start your file</h2>" in close
        assert 'data-cta="final_fill_intake"' in close
        assert f'href="{APPLY_URL}"' in close

    def test_contact_line(self):
        assert 'href="mailto:gravelgodcoaching@gmail.com"' in build_close()

    def test_no_close_art(self):
        """No real xc v6.7 close art exists, so the close has no image."""
        assert "<img" not in build_close()


class TestDataCta:
    def test_gravel_god_cta_names(self, coaching_html):
        found = set(re.findall(r'data-cta="([\w-]+)"', coaching_html))
        assert found == {"hero_apply", "tier_min", "tier_mid", "tier_max", "final_fill_intake", "sticky_cta"}


class TestNoReadingApplicationsLine:
    def test_no_reads_applications_wording(self, coaching_html):
        visible = _visible_text(coaching_html).lower()
        for phrase in ("read every application", "read your application", "reads every application",
                       "i read applications", "read each application"):
            assert phrase not in visible

class TestMobileStickyCTA:
    def test_sticky_cta_present(self, coaching_html):
        assert "gl-coach-sticky-cta" in coaching_html

    def test_sticky_cta_link(self):
        sticky = build_mobile_sticky_cta()
        assert "APPLY FOR SKI COACHING &rarr;" in sticky
        assert f'href="{APPLY_URL}"' in sticky

    def test_sticky_cta_page_bottom_padding(self, coaching_css):
        """Repo pitfall #32: without padding-bottom on the page, the
        sticky CTA overlaps the footer on short pages."""
        assert "gl-coach-page" in coaching_css
        assert "padding-bottom: 80px;" in coaching_css


# ── Nav / Footer / CTAs ──────────────────────────────────────────


class TestNavAndCTAs:
    def test_nav_coaching_link_and_active(self):
        nav = build_nav()
        assert f'href="/coaching/" class="active">Coaching</a>' in nav

    def test_footer_coaching_link(self):
        footer = build_footer()
        assert 'href="/coaching/">Coaching</a>' in footer

    def test_apply_url_constant(self):
        assert APPLY_URL == "/coaching/apply/"

    def test_all_ctas_point_to_apply(self, coaching_html):
        """Hero, all three tier CTAs, close, and sticky all point at
        /coaching/apply/ — never at /coaching/ (which would self-link)."""
        assert coaching_html.count(f'href="{APPLY_URL}"') >= 3  # hero, close, sticky
        assert f'{APPLY_URL}?tier=min' in coaching_html
        assert f'{APPLY_URL}?tier=mid' in coaching_html
        assert f'{APPLY_URL}?tier=max' in coaching_html


# ── Visual / brand compliance ────────────────────────────────────



# ── Brand compliance (Sledge Stores) ─────────────────────────────


class TestBrandCompliance:
    def test_no_border_radius(self, coaching_css):
        for m in re.finditer(r"border-radius:\s*([^;!}]+)", coaching_css):
            # Square everywhere; only the round eyelets on tags are 50%.
            assert m.group(1).strip() in ("0", "50%"), f"Non-zero border-radius: {m.group(0)}"

    def test_no_box_shadow(self, coaching_css):
        for m in re.finditer(r"box-shadow:\s*([^;}]+)", coaching_css):
            value = m.group(1).strip().replace(" !important", "")
            # No elevation. An inset line draws the button underline and the
            # eyelet rings, and is allowed.
            assert value == "none" or value.startswith("inset "), f"Non-none box-shadow: {m.group(0)}"

    def test_only_the_id_card_images(self, coaching_html):
        body = coaching_html.split("<body>", 1)[1]
        body = re.sub(r'<img class="gl-brand-mark"[^>]*>', "", body)
        imgs = re.findall(r"<img[^>]*>", body)
        assert len(imgs) == 2
        assert all("gl-coach-id-" in i for i in imgs)

    def test_correct_class_prefix(self, coaching_css):
        exempt_modifiers = {"active", "accept", "visible", "open"}
        leading = re.findall(r"(?<![\w.-])\.([a-zA-Z][\w-]*)", coaching_css)
        for cls in set(leading):
            if cls in exempt_modifiers:
                continue
            assert cls.startswith(("gl-", "xc-")), f"Non gl-/xc- prefixed class in coaching CSS: .{cls}"

    def test_stencil_headline_tokens(self, coaching_css):
        assert "var(--font-stencil)" in coaching_css
        assert "var(--font-label)" in coaching_css


class TestNoTestimonials:
    def test_no_blockquote(self, coaching_html):
        assert "<blockquote" not in coaching_html.lower()

    def test_no_testimonial_markup(self, coaching_html):
        assert "testimonial" not in coaching_html.lower()


# ── Restraint / banned-word guard ────────────────────────────────


BANNED_VISIBLE_TEXT = [
    "unlock",
    "transform",
    "crush",
    "TERMS OF WORK",
    "COURSES ON FILE",
    "$14.95",
    "suffer smarter",
]


class TestRestraintGuard:
    @pytest.mark.parametrize("phrase", BANNED_VISIBLE_TEXT)
    def test_banned_phrase_absent_from_visible_text(self, coaching_html, phrase):
        visible = _visible_text(coaching_html)
        assert phrase.lower() not in visible.lower(), (
            f"Banned phrase found in visible coaching page text: {phrase!r}"
        )

    def test_no_defensive_messaging(self, coaching_html):
        lower = coaching_html.lower()
        assert "no sponsors" not in lower
        assert "not sponsored" not in lower
        assert "no affiliates" not in lower


# ── Site-wide nav retarget ───────────────────────────────────────
# Every generator's nav-menu "Coaching" link must point at /coaching/
# now that the landing page exists. Explicit apply/CTA buttons (e.g.
# "Apply", "Coaching application") and the intake form's own post-
# submit redirect are exempt and must keep pointing at /coaching/apply/.


class TestSiteWideNavRetarget:
    def _generated(self, relpath: str) -> str:
        path = OUTPUT_DIR / relpath
        if not path.exists():
            pytest.skip(f"Page not generated: {relpath}")
        return path.read_text(encoding="utf-8")

    @pytest.mark.parametrize("relpath", [
        "vasaloppet/index.html",
        "index.html",
        "about/index.html",
        "training-plans/index.html",
        "questionnaire/index.html",
        "coaching/apply/index.html",
        "search/index.html",
    ])
    def test_nav_coaching_link_is_landing_page(self, relpath):
        html = self._generated(relpath)
        assert 'href="/coaching/">Coaching</a>' in html or \
               'href="/coaching/" class="active">Coaching</a>' in html, (
            f"{relpath}: nav 'Coaching' link does not point at /coaching/"
        )

    def test_about_cta_still_points_to_apply(self):
        html = self._generated("about/index.html")
        assert 'href="/coaching/apply/">Coaching application</a>' in html

    def test_homepage_coaching_link_points_to_the_coaching_page(self):
        html = self._generated("index.html")
        assert '<a href="/coaching/" data-ga="ladder_coaching">Coaching</a>' in html

    def test_apply_form_redirect_unchanged(self):
        html = self._generated("coaching/apply/index.html")
        assert 'value="https://xcskilabs.com/coaching/apply/?submitted=true"' in html


# ── Copy guards (Matti, 2026-11-15 rewrite) ─────────────────────


class TestCoachingCopy2026Rewrite:
    BANNED = [
        "better than you think",
        "Not an AI",
        "not an AI",
        "monthly",
        "/mo",
        "per month",
        "Matt ",
        "your coach",
        "GET ME IN YOUR CORNER",
        "Most athletes belong here",
        "Someone reads",
        "difference between a plan and coaching",
    ]

    def test_banned_phrases_absent(self, coaching_html):
        hits = [b for b in self.BANNED if b in coaching_html]
        assert hits == [], hits

    def test_one_reply_time(self, coaching_html):
        assert "48 hours" in coaching_html
        assert "24 hours" not in coaching_html
        assert "within a day" not in coaching_html

    def test_contact_is_gravelgodcoaching(self):
        c = build_faq()
        assert 'href="mailto:gravelgodcoaching@gmail.com"' in c

    def test_setup_fee_faq(self, coaching_html):
        assert "What&rsquo;s the $99 setup fee?" in coaching_html


# ── Deploy: images before the page ──────────────────────────────


class TestDeployUploadsImagesFirst:
    def _deploy(self, monkeypatch, tmp_path, scp_ok=lambda remote: True):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        import deploy
        generate_page(output_dir=tmp_path / "output")
        (tmp_path / "output" / "coaching" / "apply").mkdir(parents=True, exist_ok=True)
        (tmp_path / "output" / "coaching" / "apply" / "index.html").write_text("apply")
        calls = []
        monkeypatch.setattr(deploy, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(deploy, "get_ssh_credentials", lambda: ("h", "u", "22"))
        monkeypatch.setattr(deploy, "get_remote_base", lambda: "/base")
        monkeypatch.setattr(deploy, "_ssh_run", lambda h, u, p, cmd: (calls.append(("ssh", cmd)) or (True, "", "")))

        def scp(h, u, p, local, remote):
            calls.append(("scp", remote))
            return scp_ok(remote)

        monkeypatch.setattr(deploy, "_scp_upload", scp)
        return deploy.sync_coaching(), [c[1] for c in calls if c[0] == "scp"]

    def test_images_upload_before_the_page(self, monkeypatch, tmp_path):
        ok, uploads = self._deploy(monkeypatch, tmp_path)
        assert ok is True
        assert uploads[:2] == ["/base/coaching/img/matti-pizza-xc.webp", "/base/coaching/img/matti-pizza.webp"]
        assert uploads[2:] == ["/base/coaching/index.html", "/base/coaching/apply/index.html"]

    def test_failed_image_upload_stops_the_page(self, monkeypatch, tmp_path):
        ok, uploads = self._deploy(monkeypatch, tmp_path, scp_ok=lambda remote: "/img/" not in remote)
        assert ok is False
        assert not any(u.endswith("index.html") for u in uploads)
