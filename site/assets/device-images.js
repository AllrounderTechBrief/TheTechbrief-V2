/**
 * device-images.js — The Tech Brief
 *
 * Client-side device image matcher.
 * Runs after page load, reads article card titles, and swaps in
 * a local press image when a known device name is found.
 *
 * Behaviour:
 *   MATCH found    → replaces card <img> with local press image
 *   NO match       → leaves existing Unsplash fallback untouched
 *   Image missing  → silently keeps existing image (onerror handler)
 *
 * Zero dependencies. Works on GitHub Pages static hosting.
 * Fetch is async so never blocks page render.
 */

(function () {
  'use strict';

  // Path to the device database, relative to site root.
  // sync_static_assets copies site/assets/ → docs/assets/ on every build.
  var DB_PATH = 'assets/data/devices.json';

  // ── Utility: normalise a string for comparison ──────────────────────────
  function norm(str) {
    return (str || '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  // ── Build a flat lookup: normalised term → device entry ─────────────────
  // device_name and every alias all resolve to the same entry object.
  function buildLookup(devices) {
    var map = {};
    devices.forEach(function (dev) {
      var terms = [dev.device_name].concat(dev.aliases || []);
      terms.forEach(function (t) {
        map[norm(t)] = dev;
      });
    });
    return map;
  }

  // ── Find best device match inside a title string ─────────────────────────
  // Checks every known term. Prefers the longest matching term to avoid
  // "iPhone 16" matching inside "iPhone 16 Pro Max".
  function findDevice(title, lookup) {
    var lower = norm(title);
    var best = null;
    var bestLen = 0;

    Object.keys(lookup).forEach(function (term) {
      if (lower.indexOf(term) !== -1 && term.length > bestLen) {
        best = lookup[term];
        bestLen = term.length;
      }
    });

    return best; // null if nothing found
  }

  // ── Read the visible card category from the .tag span ───────────────────
  function readCategory(card) {
    var tag = card.querySelector('.tag');
    if (!tag) return 'default';
    var text = norm(tag.textContent);
    // Map site category labels → devices.json category keys
    if (text.indexOf('mobile') !== -1 || text.indexOf('gadget') !== -1) return 'smartphone';
    if (text.indexOf('consumer') !== -1) return 'smartphone';
    if (text.indexOf('enterprise') !== -1) return 'laptop';
    if (text.indexOf('gaming') !== -1) return 'console';
    if (text.indexOf('ev') !== -1 || text.indexOf('auto') !== -1) return 'ev';
    if (text.indexOf('ai') !== -1) return 'ai-software';
    return 'default';
  }

  // ── Swap an image safely, with fallback to default-tech on load error ───
  function swapImage(img, newSrc, altText, defaultFallback) {
    // Verify the new image actually loads before committing the swap
    var probe = new Image();
    probe.onload = function () {
      img.src = newSrc;
      img.alt = altText || img.alt;
    };
    probe.onerror = function () {
      // Press image file missing from repo — fall back to default-tech
      // This is expected during development before images are added.
      if (defaultFallback && newSrc !== defaultFallback) {
        var probe2 = new Image();
        probe2.onload = function () {
          img.src = defaultFallback;
          img.alt = img.alt;
        };
        probe2.src = defaultFallback;
      }
      // If defaultFallback also fails, keep the existing Unsplash image — do nothing.
    };
    probe.src = newSrc;
  }

  // ── Main: fetch DB, then process all cards ───────────────────────────────
  function run() {
    // Collect all cards on this page
    var cards = Array.prototype.slice.call(
      document.querySelectorAll('article.card')
    );
    if (cards.length === 0) return; // nothing to do

    fetch(DB_PATH)
      .then(function (res) {
        if (!res.ok) throw new Error('devices.json not found');
        return res.json();
      })
      .then(function (db) {
        var lookup   = buildLookup(db.devices);
        var fallbacks = db.category_fallbacks || {};
        var defaultImg = fallbacks['default'] || 'assets/press/defaults/default-tech.jpg';

        cards.forEach(function (card) {
          // Read article title from the h3 link
          var titleEl = card.querySelector('h3 a');
          if (!titleEl) return;
          var title = titleEl.textContent || titleEl.innerText || '';

          // Get existing <img> (may not exist if no image was set by build)
          var img = card.querySelector('.card-img-wrap img');

          // Try device match
          var device = findDevice(title, lookup);

          if (device) {
            // We have a specific device match
            if (!img) {
              // Card has no image at all — inject one
              var wrap = document.createElement('div');
              wrap.className = 'card-img-wrap';
              img = document.createElement('img');
              img.width  = 400;
              img.height = 185;
              img.loading = 'lazy';
              wrap.appendChild(img);
              card.insertBefore(wrap, card.firstChild);
            }
            var pressAlt = device.brand + ' ' + device.device_name + ' — editorial press image';
            swapImage(img, device.image_path, pressAlt, defaultImg);

          } else if (!img) {
            // No device match AND no existing image — inject category fallback
            var cat    = readCategory(card);
            var fbSrc  = fallbacks[cat] || defaultImg;
            var wrap2  = document.createElement('div');
            wrap2.className = 'card-img-wrap';
            var img2   = document.createElement('img');
            img2.width  = 400;
            img2.height = 185;
            img2.loading = 'lazy';
            img2.alt    = 'Technology illustration';
            wrap2.appendChild(img2);
            card.insertBefore(wrap2, card.firstChild);
            swapImage(img2, fbSrc, null, defaultImg);
          }
          // else: no match but card already has an Unsplash image — leave it alone
        });
      })
      .catch(function (err) {
        // Network/parse errors: silent fail, site continues working normally
        // Uncomment the line below while developing to debug:
        // console.warn('[device-images] Failed to load devices.json:', err);
      });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

})();
