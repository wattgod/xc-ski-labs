/* XC Ski Labs analytics: the browser contacts Google only after consent. */
(function () {
  'use strict';
  if (window.xcAnalytics) return;

  var measurementId = 'G-3JQLSQLPPM';
  var consent = (document.cookie.match(/(?:^|;\s*)xl_consent=([^;]+)/) || [])[1];
  var enabled = false;
  var loaded = false;
  window.dataLayer = window.dataLayer || [];
  function queue() { window.dataLayer.push(arguments); }

  function grant() {
    if (enabled) return;
    enabled = true;
    queue('consent', 'default', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    if (!loaded) {
      loaded = true;
      var script = document.createElement('script');
      script.async = true;
      script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
      document.head.appendChild(script);
      queue('js', new Date());
      queue('config', measurementId);
    } else {
      queue('consent', 'update', { analytics_storage: 'granted' });
    }
  }

  function revoke() {
    if (loaded) {
      queue('consent', 'update', { analytics_storage: 'denied' });
    }
    enabled = false;
  }

  window.gtag = function () {
    if (arguments[0] === 'consent' && arguments[1] === 'update') {
      if (arguments[2] && arguments[2].analytics_storage === 'granted') grant();
      else revoke();
      return;
    }
    // Legacy page templates may repeat initialization after an accept click.
    if (arguments[0] === 'js' || arguments[0] === 'config') return;
    if (enabled) window.dataLayer.push(arguments);
  };

  window.xcAnalytics = { grant: grant, revoke: revoke };
  if (consent === 'accepted') grant();
})();
