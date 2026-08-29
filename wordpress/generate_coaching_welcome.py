#!/usr/bin/env python3
"""Generate XC Ski Labs' post-payment coaching welcome page."""

import argparse
from pathlib import Path

try:
    from .generate_coaching import (
        GA4_ID,
        SITE_BASE_URL,
        build_cookie_consent,
        build_css as build_coaching_css,
        build_footer,
        build_nav,
    )
except ImportError:
    from generate_coaching import (
        GA4_ID,
        SITE_BASE_URL,
        build_cookie_consent,
        build_css as build_coaching_css,
        build_footer,
        build_nav,
    )


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
TRAININGPEAKS_ATTACH_URL = (
    "https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU"
)


def build_welcome_css() -> str:
    return build_coaching_css() + """
.gl-welcome {
  max-width: 680px;
  margin: 0 auto;
  padding: 64px 24px;
}
.gl-welcome-mark {
  width: 56px;
  height: 56px;
  border: 3px solid var(--gl-swix-red);
  color: var(--gl-swix-red);
  font-family: var(--gl-font-data);
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 50px;
  text-align: center;
}
.gl-welcome h1 {
  margin: 24px 0 12px;
  color: var(--gl-carbon);
  font-size: clamp(1.7rem, 5vw, 2.5rem);
}
.gl-welcome-intro {
  margin: 0 0 40px;
  color: var(--gl-muted);
  font-size: 1.05rem;
}
.gl-welcome-step {
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 16px;
  padding: 24px 0;
  border-top: 2px solid var(--gl-carbon);
}
.gl-welcome-step-num {
  font-family: var(--gl-font-data);
  font-weight: 700;
  color: var(--gl-swix-red);
}
.gl-welcome-step h2 { margin: 0 0 8px; font-size: 1.15rem; }
.gl-welcome-step p { margin: 0; color: var(--gl-muted); }
.gl-welcome-cta {
  display: inline-block;
  margin-top: 14px;
  padding: 12px 20px;
  border: 3px solid var(--gl-carbon);
  background: var(--gl-swix-red);
  color: var(--gl-white);
  font-family: var(--gl-font-data);
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .06em;
  text-decoration: none;
  text-transform: uppercase;
}
@media (max-width: 520px) {
  .gl-welcome { padding: 44px 18px; }
}
"""


def build_welcome() -> str:
    return f"""
<main class="gl-welcome" data-product-type="coaching">
  <div class="gl-welcome-mark">&check;</div>
  <h1>You&rsquo;re in.</h1>
  <p class="gl-welcome-intro">Payment is complete. TrainingPeaks Premium is included with your coaching.</p>

  <section class="gl-welcome-step">
    <div class="gl-welcome-step-num">01</div>
    <div>
      <h2>Connect TrainingPeaks</h2>
      <p>If you are not already attached to my coaching account, use this link. If you are attached already, skip it.</p>
      <a class="gl-welcome-cta" href="{TRAININGPEAKS_ATTACH_URL}" target="_blank" rel="noopener" data-cta="connect_trainingpeaks">Connect TrainingPeaks</a>
    </div>
  </section>

  <section class="gl-welcome-step">
    <div class="gl-welcome-step-num">02</div>
    <div>
      <h2>Check your email and book</h2>
      <p>Your private onboarding guide includes your kickoff-call booking link, what your tier includes, and exactly how we communicate. You do not need to submit the application again.</p>
    </div>
  </section>

  <section class="gl-welcome-step">
    <div class="gl-welcome-step-num">03</div>
    <div>
      <h2>Run the first block</h2>
      <p>Your TrainingPeaks calendar is the source of truth. Comment after each workout; if you miss one, do not stack it onto the next day. Tell me what happened and I will adjust it.</p>
    </div>
  </section>
</main>"""


def build_page_js() -> str:
    return """<script>
(function() {
  var params = new URLSearchParams(window.location.search);
  var sessionId = params.get('session_id') || '';
  if (typeof gtag === 'function') {
    gtag('event', 'coaching_welcome_view', {transaction_id: sessionId});
  }
  document.querySelectorAll('[data-cta]').forEach(function(link) {
    link.addEventListener('click', function() {
      if (typeof gtag === 'function') {
        gtag('event', 'cta_click', {source: 'coaching_welcome', cta_name: link.getAttribute('data-cta')});
      }
    });
  });
})();
</script>"""


def generate_page(output_dir: Path | None = None) -> Path:
    output_dir = output_dir or OUTPUT_DIR
    out_path = output_dir / "coaching" / "welcome" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_url = f"{SITE_BASE_URL}/coaching/welcome/"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to Coaching | XC Ski Labs</title>
  <meta name="description" content="XC Ski Labs coaching setup and TrainingPeaks connection steps.">
  <meta name="robots" content="noindex, nofollow">
  <link rel="canonical" href="{canonical_url}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  <style>{build_welcome_css()}</style>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
  <script>
  window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
  (function(){{var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
  if(c==='declined')return;gtag('js',new Date());gtag('config','{GA4_ID}')}})();
  </script>
</head>
<body>
{build_nav()}
{build_welcome()}
{build_footer()}
{build_cookie_consent()}
{build_page_js()}
</body>
</html>"""
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate XC Ski Labs coaching welcome page")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    result = generate_page(args.output_dir)
    print(f"Generated: {result}")
