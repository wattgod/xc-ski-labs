"""Contract tests for the XC Ski Labs coaching welcome page."""

import subprocess

import pytest

from wordpress.generate_coaching_welcome import (
    TRAININGPEAKS_ATTACH_URL,
    build_page_js,
    build_welcome,
    generate_page,
)


@pytest.fixture(scope="module")
def welcome_html(tmp_path_factory):
    path = generate_page(tmp_path_factory.mktemp("coaching-welcome"))
    return path.read_text(encoding="utf-8")


def test_expected_route_and_private_indexing(welcome_html):
    assert "https://xcskilabs.com/coaching/welcome/" in welcome_html
    assert 'content="noindex, nofollow"' in welcome_html


def test_trainingpeaks_and_premium_contract():
    content = build_welcome()
    assert TRAININGPEAKS_ATTACH_URL in content
    assert "If you are attached already, skip it." in content
    assert "TrainingPeaks Premium is included" in content


def test_success_page_does_not_reopen_pre_payment_gates():
    content = build_welcome()
    assert "agreement, or data-consent gates" not in content
    assert "Check your email and book" in content
    assert "do not stack it onto the next day" in content


def test_generated_javascript_parses():
    script = build_page_js().replace("<script>", "").replace("</script>", "")
    result = subprocess.run(
        ["node", "-e", f"new Function({script!r})"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
