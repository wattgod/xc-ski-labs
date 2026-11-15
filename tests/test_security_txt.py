"""ALL-09: /.well-known/security.txt (RFC 9116)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXT = (PROJECT_ROOT / "web" / ".well-known" / "security.txt").read_text(encoding="utf-8")
FIELDS = dict(line.split(": ", 1) for line in TEXT.splitlines() if line and not line.startswith("#"))


def test_required_fields():
    assert FIELDS["Contact"] == "mailto:gravelgodcoaching@gmail.com"
    assert FIELDS["Canonical"] == "https://xcskilabs.com/.well-known/security.txt"


def test_expires_is_ahead_and_under_a_year_from_now_plus_slack():
    expires = datetime.strptime(FIELDS["Expires"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    # RFC 9116 recommends under a year; this test going red is the reminder to renew.
    assert now < expires < now + timedelta(days=400), "security.txt Expires needs renewing"


def test_deploy_ships_it():
    src = (PROJECT_ROOT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    assert ".well-known/security.txt" in src
