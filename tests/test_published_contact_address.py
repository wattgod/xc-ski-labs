"""Sweep ALL-11: no page may print an xcskilabs.com mailbox nobody reads.

coach@xcskilabs.com bounced (550) on 14 Nov 2026 and coaching@xcskilabs.com
is an unread SiteGround mailbox. Riders are pointed at Matti's address.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEAD = ("coach@xcskilabs.com", "coaching@xcskilabs.com")
CONTACT = "gravelgodcoaching@gmail.com"


def _sources():
    for folder in ("wordpress", "scripts", "web"):
        for path in (ROOT / folder).rglob("*"):
            if path.suffix in {".py", ".html", ".js", ".txt"} and path.is_file():
                yield path


def test_no_generator_publishes_a_dead_xc_mailbox():
    hits = []
    for path in _sources():
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if any(addr in line for addr in DEAD):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert not hits, f"dead XC mailbox published: {hits}"


def test_contact_constants_point_at_matti():
    for rel in ("wordpress/generate_exit_interview.py", "wordpress/generate_goals.py",
                "scripts/generate_llms_txt.py"):
        assert CONTACT in (ROOT / rel).read_text(), rel


def test_guide_gate_unlocks_only_after_the_worker_stores_the_email():
    """Sweep ALL-03: guide_unlock counted only on a stored capture."""
    src = (ROOT / "scripts" / "generate_guide.py").read_text()
    assert "formsubmit.co" not in src
    block = src[src.index("fueling-lead-intake.gravelgodcoaching.workers.dev"):]
    block = block[:block.index("</script>")]
    assert ".catch(function(){});" not in block
    then_at = block.index(".then(function(r)")
    assert block.index("if (!r.ok) throw") > then_at
    assert block.index("gtag('event', 'guide_unlock'") > then_at
    assert block.index("unlock();") > then_at
    assert "data-guide-gate-error" in src


def test_guide_gate_never_puts_the_email_in_the_url():
    src = (ROOT / "scripts" / "generate_guide.py").read_text()
    assert '<form class="gl-guide-gate-form" data-guide-gate-form method="post">' in src
