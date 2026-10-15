"""Subscription terms stay separate from the existing purchased-product ladder."""
import importlib.util
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/endure_offer.py"
spec = importlib.util.spec_from_file_location("endure_offer", MODULE)
offer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offer)

def test_signup_has_source_campaign_and_no_entitlement_bypass():
    url = urlparse(offer.SIGNUP_URL)
    assert url.scheme == "https" and url.netloc == "endurelabs.app"
    assert url.path == "/sign-up"
    query = parse_qs(url.query)
    assert query["utm_campaign"] == ["endure_trial"]
    assert query["utm_medium"] == ["referral"]
    assert set(query) == {"utm_source", "utm_medium", "utm_campaign", "utm_content"}

def test_offer_discloses_card_conversion_cancellation_and_eligibility():
    text = offer.get_endure_offer_html()
    for disclosure in ["Card required.", "bills automatically unless you cancel", "Cancel online", "eligible new subscribers", "https://endurelabs.app/help"]:
        assert disclosure in text
    assert 'aria-label="Endure training app"' in text
    assert "min-height:44px" in text
    assert "focus-visible" in text
    assert "&amp;utm_medium" in text

def test_generators_emit_offer_without_replacing_purchased_product_links():
    import sys
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "wordpress"))
    from scripts.generate_race_pages import build_footer
    from wordpress.generate_training_plans import build_footer as plans_footer
    from wordpress.generate_coaching import build_footer as coaching_footer
    from wordpress.generate_coaching_apply import build_footer as apply_footer
    for footer in [build_footer({}), plans_footer(), coaching_footer(), apply_footer()]:
        assert footer.count('class="endure-trial-offer"') == 1
        assert '/privacy/' in footer and '/terms/' in footer
