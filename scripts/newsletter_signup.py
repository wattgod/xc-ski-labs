"""XC Ski Labs Weekly sign-up form.

A sign-up posts to the shared lead-intake Worker
(gravel-race-automation/workers/fueling-lead-intake) with
source=newsletter_subscribe and brand=xcskilabs. Mission Control enrolls the
address in xc_welcome_v1 and records newsletter_opt_in_at, which is the list
the weekly broadcast reads (gravel-race-automation scripts/send_xc_weekly.py).
The Worker refuses newsletter_subscribe without a brand, so a skier never
lands on a Gravel God list.

Every surface uses newsletter_form_html(placement). Each form carries its own
small script that binds every .xc-newsletter-form on the page not yet bound.
Success shows only after the Worker answers 2xx; anything else shows the
error line and keeps the typed address. Messages are set with textContent,
never innerHTML.
"""
from __future__ import annotations

import html
import re

LEAD_WORKER_URL = "https://fueling-lead-intake.gravelgodcoaching.workers.dev"
NEWSLETTER_SOURCE = "newsletter_subscribe"
NEWSLETTER_BRAND = "xcskilabs"

NEWSLETTER_FINE = "No spam. Unsubscribe anytime."
NEWSLETTER_BUTTON = "Sign me up"
NEWSLETTER_SUCCESS = "You're on the list. The first email is already on its way."
NEWSLETTER_ERROR = "That didn't go through. Try again in a minute."
NEWSLETTER_INVALID = "Enter a valid email address."

_PLACEMENT_RE = re.compile(r"^[a-z0-9_]{1,32}$")

_SCRIPT = """<script>
(function(){
  var URL='__WORKER__';
  var forms=document.querySelectorAll('form.xc-newsletter-form:not([data-bound])');
  Array.prototype.forEach.call(forms,function(form){
    form.setAttribute('data-bound','1');
    var box=form.parentNode;
    var ok=box.querySelector('.xc-newsletter-success');
    var err=box.querySelector('.xc-newsletter-error');
    var btn=form.querySelector('button');
    form.addEventListener('submit',function(e){
      e.preventDefault();
      if(err){err.textContent='';err.hidden=true;}
      if(form.website&&form.website.value) return;
      var email=form.email.value.trim();
      if(!email||!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email)){
        if(err){err.textContent='__INVALID__';err.hidden=false;}
        return;
      }
      var placement=form.getAttribute('data-placement')||'';
      if(btn) btn.disabled=true;
      fetch(URL,{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email:email,brand:'__BRAND__',source:'__SOURCE__',website:form.website?form.website.value:''})})
        .then(function(r){
          if(!r.ok) throw new Error('status '+r.status);
          if(typeof gtag==='function'){
            gtag('event','email_capture',{source:'__SOURCE__',placement:placement});
          }
          form.hidden=true;
          if(ok){ok.textContent='__SUCCESS__';ok.hidden=false;}
        })
        .catch(function(){
          if(btn) btn.disabled=false;
          if(err){err.textContent='__ERROR__';err.hidden=false;}
        });
    });
  });
})();
</script>"""


def _js_str(text: str) -> str:
    """Escape text for a single-quoted JS string inside an HTML <script>."""
    return (text.replace("\\", "\\\\").replace("'", "\\'")
            .replace("<", "\\x3c").replace(">", "\\x3e"))


def newsletter_script() -> str:
    return (_SCRIPT
            .replace("__WORKER__", LEAD_WORKER_URL)
            .replace("__BRAND__", NEWSLETTER_BRAND)
            .replace("__SOURCE__", NEWSLETTER_SOURCE)
            .replace("__INVALID__", _js_str(NEWSLETTER_INVALID))
            .replace("__SUCCESS__", _js_str(NEWSLETTER_SUCCESS))
            .replace("__ERROR__", _js_str(NEWSLETTER_ERROR)))


def newsletter_form_html(placement: str, *, fine_print: bool = True) -> str:
    """The sign-up form plus its script. `placement` tags analytics only."""
    if not _PLACEMENT_RE.match(placement):
        raise ValueError(f"bad newsletter placement: {placement!r}")
    fine = f'\n  <p class="xc-newsletter-fine">{html.escape(NEWSLETTER_FINE)}</p>' if fine_print else ""
    return f'''<div class="xc-newsletter">
  <form class="xc-newsletter-form" data-placement="{placement}" novalidate>
    <input type="text" name="website" value="" tabindex="-1" autocomplete="off" aria-hidden="true" class="xc-newsletter-hp">
    <label class="xc-newsletter-label" for="xc-newsletter-email-{placement}">Email address</label>
    <div class="xc-newsletter-row">
      <input type="email" name="email" id="xc-newsletter-email-{placement}" required placeholder="you@example.com" autocomplete="email" class="xc-newsletter-input">
      <button type="submit" class="xc-btn xc-newsletter-btn" data-ga="subscribe_click" data-ga-label="{placement}">{html.escape(NEWSLETTER_BUTTON)}</button>
    </div>
  </form>
  <p class="xc-newsletter-success" role="status" hidden></p>
  <p class="xc-newsletter-error" role="alert" hidden></p>{fine}
</div>
{newsletter_script()}'''


def newsletter_css() -> str:
    """Form CSS on the Sledge Stores book variables (tokens/tokens.css)."""
    return """
/* ── XC Ski Labs Weekly sign-up ── */
.xc-newsletter { max-width: 560px; }
.xc-newsletter-hp { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }
.xc-newsletter-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.xc-newsletter-row { display: flex; gap: 10px; }
.xc-newsletter-input { flex: 1; min-width: 0; min-height: 56px; padding: 10px 14px; box-sizing: border-box; font: 400 17px var(--font-body); color: var(--ink); background: var(--ground); border: 2px solid var(--ink); border-radius: 0; }
.xc-newsletter-input:focus-visible { outline: 3px solid var(--ink); outline-offset: 2px; }
.xc-newsletter-btn { flex: none; }
.xc-newsletter-success { margin: 10px 0 0; font: 800 18px/1.3 var(--font-label); letter-spacing: .04em; color: var(--ink); }
.xc-newsletter-error { margin: 10px 0 0; font: 600 15px/1.4 var(--font-body); color: var(--danger); }
.xc-newsletter-error::before { content: "\\26A0\\FE0E  "; }
.xc-newsletter-fine { margin: 10px 0 0; font: 400 14px/1.4 var(--font-body); color: var(--ink); }
@media (max-width: 600px) {
  .xc-newsletter-row { flex-direction: column; }
}
"""
