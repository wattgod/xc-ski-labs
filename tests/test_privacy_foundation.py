"""Privacy behavior for shared assets and the coaching application draft."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from wordpress.generate_coaching_apply import build_form_js

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="Node.js is needed to execute the browser script")
def test_analytics_never_contacts_google_before_acceptance():
    script = (ROOT / "web/xc-assets/analytics.js").read_text()
    harness = r"""
const vm = require('vm'), assert = require('assert');
const script = require('fs').readFileSync(0, 'utf8');
function boot(cookie) {
  const requests = [];
  const window = {dataLayer: []};
  const document = {
    cookie,
    createElement: () => ({}),
    head: {appendChild: tag => requests.push(tag.src)}
  };
  vm.runInNewContext(script, {window, document, Date});
  return {window, requests};
}
const undecided = boot('');
assert.deepStrictEqual(undecided.requests, []);
undecided.window.gtag('event', 'sensitive_input');
assert.equal(undecided.window.dataLayer.length, 0);
undecided.window.gtag('consent', 'update', {analytics_storage: 'granted'});
assert.equal(undecided.requests.length, 1);
assert.equal(undecided.window.dataLayer.at(-1)[0], 'config');
undecided.window.gtag('consent', 'update', {analytics_storage: 'denied'});
assert.equal(undecided.window.dataLayer.at(-1)[2].analytics_storage, 'denied');
assert.deepStrictEqual(boot('xl_consent=declined').requests, []);
assert.equal(boot('xl_consent=accepted').requests.length, 1);
"""
    result = subprocess.run([NODE, "-e", harness], input=script, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is needed to execute the browser script")
def test_coaching_draft_excludes_health_and_removes_legacy_draft():
    script = re.sub(r"^<script>|</script>$", "", build_form_js().strip())
    harness = r"""
const vm = require('vm'), assert = require('assert');
const script = require('fs').readFileSync(0, 'utf8');
const stored = new Map([['xcskilabs_coaching_form', JSON.stringify({injuries:'old injury'})]]);
const fields = [
  {name:'primary_goal', type:'radio', checked:true, value:'specific_race'},
  {name:'injuries', type:'textarea', value:'knee injury'},
  {name:'medications', type:'textarea', value:'prescription'},
  {name:'name', type:'text', value:'Test Athlete'}
];
const handlers = {};
const classList = {add(){}, remove(){}};
const form = {elements: fields, addEventListener:(name, cb) => handlers[name]=cb,
  querySelectorAll:() => []};
const nodes = {coachingForm:form, progressFill:{style:{}}, progressPct:{},
  saveIndicator:{classList}, glToast:{classList}};
const document = {getElementById:name => nodes[name] || null, querySelectorAll:() => []};
const localStorage = {getItem:key => stored.get(key) || null,
  setItem:(key,value) => stored.set(key,value), removeItem:key => stored.delete(key)};
const window = {location:{search:''}};
vm.runInNewContext(script, {window, document, localStorage, setTimeout:() => 1,
  clearTimeout:() => {}, Date});
assert.equal(stored.has('xcskilabs_coaching_form'), false);
handlers.input({target:{name:'injuries'}});
assert.equal(stored.has('xcskilabs_coaching_form_v2'), false);
handlers.input({target:{name:'primary_goal'}});
const draft = JSON.parse(stored.get('xcskilabs_coaching_form_v2'));
assert.equal(draft.values.primary_goal, 'specific_race');
assert.equal('injuries' in draft.values, false);
assert.equal('medications' in draft.values, false);
assert.equal('name' in draft.values, false);
assert.ok(draft.savedAt > Date.now()-1000);
"""
    result = subprocess.run([NODE, "-e", harness], input=script, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_self_hosted_fonts_have_local_files_and_licenses():
    assets = ROOT / "web/xc-assets"
    css = (assets / "fonts.css").read_text()
    assert "fonts.googleapis.com" not in css
    assert "fonts.gstatic.com" not in css
    for name in re.findall(r"/xc-assets/fonts/(font-\d+\.woff2)", css):
        assert (assets / "fonts" / name).is_file()
    assert len(list((assets / "fonts").glob("*-OFL.txt"))) == 3
