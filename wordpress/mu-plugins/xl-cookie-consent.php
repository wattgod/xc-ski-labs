<?php
/**
 * XC Ski Labs — Cookie Consent Banner + Consent Mode v2
 *
 * Sets consent mode defaults BEFORE GA4 loads (priority 0),
 * then injects banner HTML in footer (priority 99).
 *
 * Cookie: xl_consent (accepted|declined), 1-year expiry.
 */

defined('ABSPATH') || exit;

// ── Consent Mode defaults (must fire BEFORE GA4) ────────────
add_action('wp_head', function () {
    ?>
<!-- XC Ski Labs Consent Mode v2 -->
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
(function() {
    var consent = (document.cookie.match(/xl_consent=([^;]+)/) || [])[1];
    var granted = (consent === 'accepted') ? 'granted' : 'denied';
    gtag('consent', 'default', {
        'analytics_storage': granted,
        'ad_storage': 'denied',
        'ad_user_data': 'denied',
        'ad_personalization': 'denied',
        'functionality_storage': 'granted',
        'security_storage': 'granted'
    });
})();
</script>
<!-- /XC Ski Labs Consent Mode v2 -->
    <?php
}, 0);

// ── Cookie consent banner ────────────────────────────────────
add_action('wp_footer', function () {
    ?>
<style>
.xl-consent-banner {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: #1a2332;
    color: #e8edf2;
    border-top: 3px solid #d4ac0d;
    padding: 16px 20px;
    font-family: 'Sometype Mono', monospace;
    font-size: 0.8rem;
    display: none;
}
.xl-consent-banner.show { display: block; }
.xl-consent-inner {
    max-width: 900px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}
.xl-consent-text {
    flex: 1;
    min-width: 200px;
    line-height: 1.5;
}
.xl-consent-text a {
    color: #5dade2;
    text-decoration: underline;
}
.xl-consent-btns {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}
.xl-consent-btn {
    font-family: 'Sometype Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 8px 16px;
    border: 2px solid #e8edf2;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.xl-consent-accept {
    background: #1b7260;
    color: #e8edf2;
}
.xl-consent-accept:hover { background: #357a88; }
.xl-consent-decline {
    background: transparent;
    color: #9ca8b8;
    border-color: #4a5568;
}
.xl-consent-decline:hover { color: #e8edf2; border-color: #e8edf2; }
</style>
<div class="xl-consent-banner" id="xl-consent-banner">
    <div class="xl-consent-inner">
        <div class="xl-consent-text">
            We use cookies for analytics to improve the experience.
            <a href="/privacy/">Privacy policy</a>.
        </div>
        <div class="xl-consent-btns">
            <button class="xl-consent-btn xl-consent-accept" onclick="xlConsent('accepted')">Accept</button>
            <button class="xl-consent-btn xl-consent-decline" onclick="xlConsent('declined')">Decline</button>
        </div>
    </div>
</div>
<script>
function xlConsent(choice) {
    document.cookie = 'xl_consent=' + choice + ';path=/;max-age=31536000;SameSite=Lax;Secure';
    var storage = (choice === 'accepted') ? 'granted' : 'denied';
    if (typeof gtag === 'function') {
        gtag('consent', 'update', { 'analytics_storage': storage });
    }
    document.getElementById('xl-consent-banner').classList.remove('show');
}
(function() {
    if (!/xl_consent=/.test(document.cookie)) {
        document.getElementById('xl-consent-banner').classList.add('show');
    }
})();
</script>
    <?php
}, 99);
