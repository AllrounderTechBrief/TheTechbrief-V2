/**
 * device-images.js — The Tech Brief
 *
 * Assigns correct featured images to article cards.
 *
 * Priority order per card:
 *   1. Specific device press image  (e.g. samsung-galaxy-s26-ultra.jpg)
 *   2. Device category fallback     (e.g. default-smartphone.jpg) if press file missing
 *   3. Title-keyword category       (title says "phone" → smartphone fallback)
 *   4. Tag-based category           (last resort)
 *   5. Leave existing image alone
 *
 * Fixes:
 *   - "Enterprise Tech" Motorola phone article no longer shows a laptop image
 *   - Samsung article no longer shows an iPhone Unsplash photo when press file missing
 */

(function () {
  'use strict';

  var DB_PATH = 'assets/data/devices.json';

  function norm(str) {
    return (str || '').toLowerCase().replace(/\s+/g, ' ').trim();
  }

  function buildLookup(devices) {
    var map = {};
    devices.forEach(function (dev) {
      var terms = [dev.device_name].concat(dev.aliases || []);
      terms.forEach(function (t) { map[norm(t)] = dev; });
    });
    return map;
  }

  // Returns true if title clearly describes a phone/mobile article
  function titleIsPhone(t) {
    return /phone|smartphone|grapheneos|calyxos|lineageos|android fork|foldable|flip phone|handset/.test(t);
  }

  // Find best matching device — longest term wins to avoid short-name collisions.
  // Rejects laptop/desktop match when title clearly signals a phone.
  function findDevice(title, lookup) {
    var lower = norm(title);
    var best = null, bestLen = 0;
    Object.keys(lookup).forEach(function (term) {
      if (lower.indexOf(term) !== -1 && term.length > bestLen) {
        best = lookup[term]; bestLen = term.length;
      }
    });
    // Guard: don't use a laptop/desktop press image for a phone article
    if (best && (best.category === 'laptop' || best.category === 'desktop') && titleIsPhone(lower)) {
      return null;
    }
    return best;
  }

  // Determine visual category from article title keywords.
  // This is more accurate than using the editorial category tag,
  // because "Enterprise Tech" often contains phone articles.
  function titleCategory(title) {
    var t = norm(title);
    if (/phone|smartphone|grapheneos|calyxos|lineageos|android fork|foldable|flip phone|handset/.test(t)) return 'smartphone';
    if (/\blaptop|notebook|macbook|thinkpad|chromebook|ultrabook|matebook/.test(t)) return 'laptop';
    if (/\btablet|ipad|\bpad\b/.test(t)) return 'tablet';
    if (/earbuds|headphones|airpods|\bbuds\b|tws/.test(t)) return 'audio';
    if (/smartwatch|apple watch|galaxy watch|pixel watch/.test(t)) return 'wearable';
    if (/electric car|electric vehicle|\bev\b|charging station|\btesla\b/.test(t)) return 'ev';
    if (/\bgpu\b|graphics card|geforce|radeon/.test(t)) return 'gpu';
    if (/playstation|\bps5\b|\bxbox\b|nintendo switch/.test(t)) return 'console';
    if (/vr headset|ar glasses|vision pro|meta quest/.test(t)) return 'xr';
    return null;
  }

  // Last-resort: map editorial category tag to visual type
  function tagCategory(card) {
    var tag = card.querySelector('.tag');
    if (!tag) return 'default';
    var text = norm(tag.textContent);
    if (text.indexOf('mobile') !== -1 || text.indexOf('gadget') !== -1) return 'smartphone';
    if (text.indexOf('consumer') !== -1) return 'smartphone';
    if (text.indexOf('gaming') !== -1) return 'console';
    if (text.indexOf('ev') !== -1 || text.indexOf('auto') !== -1) return 'ev';
    if (text.indexOf('ai') !== -1) return 'ai-software';
    // "Enterprise Tech" / "Broadcast Tech" → 'default' (NOT 'laptop')
    return 'default';
  }

  // Try each src in order; first one that loads wins. If all fail, leave existing image.
  function setImageFromList(img, srcList, altText) {
    if (!srcList || srcList.length === 0) return;
    var src = srcList[0];
    var probe = new Image();
    probe.onload = function () {
      img.src = src;
      if (altText) img.alt = altText;
    };
    probe.onerror = function () {
      setImageFromList(img, srcList.slice(1), altText);
    };
    probe.src = src;
  }

  function ensureImg(card) {
    var img = card.querySelector('.card-img-wrap img');
    if (img) return { img: img, injected: false };
    var wrap = document.createElement('div');
    wrap.className = 'card-img-wrap';
    img = document.createElement('img');
    img.width = 400; img.height = 185; img.loading = 'lazy';
    wrap.appendChild(img);
    card.insertBefore(wrap, card.firstChild);
    return { img: img, injected: true };
  }

  function run() {
    var cards = Array.prototype.slice.call(document.querySelectorAll('article.card'));
    if (cards.length === 0) return;

    fetch(DB_PATH)
      .then(function (res) {
        if (!res.ok) throw new Error('devices.json not found');
        return res.json();
      })
      .then(function (db) {
        var lookup    = buildLookup(db.devices);
        var fallbacks = db.category_fallbacks || {};
        var def       = fallbacks['default'] || 'assets/press/defaults/default-tech.jpg';

        cards.forEach(function (card) {
          var titleEl = card.querySelector('h3 a');
          if (!titleEl) return;
          var title = titleEl.textContent || titleEl.innerText || '';

          // ── 1. Try specific device match ──────────────────────────────
          var device = findDevice(title, lookup);
          if (device) {
            var catFb   = fallbacks[device.category] || def;
            var titleCat = titleCategory(title);
            var titleFb  = (titleCat && fallbacks[titleCat]) || def;
            var r = ensureImg(card);
            setImageFromList(r.img,
              [device.image_path, catFb, titleFb, def],
              device.brand + ' ' + device.device_name
            );
            return;
          }

          // ── 2. Title keyword category ──────────────────────────────────
          var tCat = titleCategory(title);
          if (tCat) {
            var fbSrc = fallbacks[tCat] || def;
            var r2 = ensureImg(card);
            // Always apply title-based category, even if card already has
            // a wrong-category Unsplash image (the main fix for Motorola case)
            setImageFromList(r2.img, [fbSrc, def], 'Technology illustration');
            return;
          }

          // ── 3. Tag-based category (only for cards with no image) ───────
          var tagCat = tagCategory(card);
          var r3 = ensureImg(card);
          if (r3.injected) {
            // Only fill empty cards from the tag — don't override existing
            setImageFromList(r3.img, [fallbacks[tagCat] || def, def], 'Technology illustration');
          }
        });
      })
      .catch(function () {
        // Silent — Unsplash pool images stay visible if fetch fails
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

})();
