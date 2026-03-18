(function () {
  const COOKIE_KEY = 'ttb_consent';

  // Restore consent if already given
  function restoreConsent() {
    const saved = localStorage.getItem(COOKIE_KEY);
    if (saved === 'granted') {
      updateConsent('granted');
      return true;
    }
    if (saved === 'denied') {
      return true; // already decided, don't show banner
    }
    return false;
  }

  function updateConsent(state) {
    if (typeof gtag === 'function') {
      gtag('consent', 'update', {
        analytics_storage: state,
        ad_storage: state,
        ad_user_data: state,
        ad_personalization: state
      });
    }
  }

  function removeBanner() {
    const b = document.getElementById('ttb-consent-banner');
    if (b) b.remove();
  }

  function showBanner() {
    const banner = document.createElement('div');
    banner.id = 'ttb-consent-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML = `
      <style>
        #ttb-consent-banner {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          z-index: 99999;
          background: #1a1a2e;
          color: #f0f0f0;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-size: 14px;
          padding: 16px 20px;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 12px;
          justify-content: space-between;
          box-shadow: 0 -4px 20px rgba(0,0,0,0.35);
          border-top: 3px solid #e63946;
        }
        #ttb-consent-banner .ttb-consent-text {
          flex: 1 1 300px;
          line-height: 1.5;
        }
        #ttb-consent-banner .ttb-consent-text a {
          color: #90caf9;
          text-decoration: underline;
        }
        #ttb-consent-banner .ttb-consent-btns {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }
        #ttb-consent-banner button {
          padding: 9px 20px;
          border: none;
          border-radius: 5px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.2s;
          white-space: nowrap;
        }
        #ttb-consent-banner button:hover { opacity: 0.85; }
        #ttb-consent-accept {
          background: #e63946;
          color: #fff;
        }
        #ttb-consent-decline {
          background: #333;
          color: #ccc;
          border: 1px solid #555 !important;
        }
      </style>
      <div class="ttb-consent-text">
        🍪 We use cookies and analytics to improve your experience and understand how our content is used.
        By clicking <strong>Accept</strong>, you consent to our use of analytics cookies.
        See our <a href="/TheTechBrief/legal/privacy.html">Privacy Policy</a> for details.
      </div>
      <div class="ttb-consent-btns">
        <button id="ttb-consent-decline">Decline</button>
        <button id="ttb-consent-accept">Accept All</button>
      </div>
    `;
    document.body.appendChild(banner);

    document.getElementById('ttb-consent-accept').addEventListener('click', function () {
      localStorage.setItem(COOKIE_KEY, 'granted');
      updateConsent('granted');
      removeBanner();
    });

    document.getElementById('ttb-consent-decline').addEventListener('click', function () {
      localStorage.setItem(COOKIE_KEY, 'denied');
      updateConsent('denied');
      removeBanner();
    });
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    if (!restoreConsent()) {
      showBanner();
    }
  }
})();
