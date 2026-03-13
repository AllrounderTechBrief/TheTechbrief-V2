/**
 * trending-loader.js — The Tech Brief
 * ─────────────────────────────────────────────────────────────────
 * HOW TO UPDATE TRENDING STORIES (your daily 60-second workflow):
 *
 *   1. Open Notepad / Notes / any plain text app
 *   2. Write each story as exactly 5 lines:
 *
 *        Line 1 — Headline
 *        Line 2 — Summary (1–2 sentences, plain English)
 *        Line 3 — Badge word  (Breaking / Security / AI Alert / MWC / EVs / Innovation / Gaming / Launch / Review)
 *        Line 4 — Source Name | https://source-homepage-url
 *        Line 5 — https://actual-article-url  ← readers click headline to go HERE
 *
 *   3. Leave ONE blank line between stories.
 *   4. GitHub → docs/assets/data/trending.txt → pencil ✏️ → paste → Commit changes
 *   5. Site updates in ~60 seconds. Done.
 *
 * ─────────────────────────────────────────────────────────────────
 * EXAMPLE — copy this format exactly:
 *
 *   Apple Unveils iPhone 17 Air
 *   Apple has announced a thinner iPhone Air alongside refreshed iPad models at today's event.
 *   Breaking
 *   Apple Newsroom | https://www.apple.com/newsroom/
 *   https://www.apple.com/newsroom/2026/03/apple-announces-iphone-17-air/
 *
 *   ChatGPT Gets Long-Term Memory
 *   OpenAI gives ChatGPT persistent memory that works across all your conversations from today.
 *   AI Alert
 *   OpenAI Blog | https://openai.com/news/
 *   https://openai.com/news/chatgpt-memory-update/
 *
 * ─────────────────────────────────────────────────────────────────
 */

(function () {
  'use strict';

  var DATA_PATH = 'assets/data/trending.txt';

  var BADGE_MAP = [
    ['breaking',    'trend-badge--breaking'],
    ['exclusive',   'trend-badge--breaking'],
    ['mwc',         'trend-badge--mwc'],
    ['ces',         'trend-badge--mwc'],
    ['launch',      'trend-badge--innovation'],
    ['review',      'trend-badge--innovation'],
    ['innovation',  'trend-badge--innovation'],
    ['ai alert',    'trend-badge--ai'],
    ['ai',          'trend-badge--ai'],
    ['update',      'trend-badge--ai'],
    ['evs',         'trend-badge--ev'],
    ['ev',          'trend-badge--ev'],
    ['automotive',  'trend-badge--ev'],
    ['security',    'trend-badge--enterprise'],
    ['enterprise',  'trend-badge--enterprise'],
    ['gaming',      'trend-badge--gaming'],
    ['rumour',      'trend-badge--rumour'],
    ['rumor',       'trend-badge--rumour']
  ];

  function badgeClass(word) {
    var w = (word || '').toLowerCase().trim();
    for (var i = 0; i < BADGE_MAP.length; i++) {
      if (w.indexOf(BADGE_MAP[i][0]) !== -1) return BADGE_MAP[i][1];
    }
    return 'trend-badge--innovation';
  }

  function todayLabel() {
    var d = new Date();
    var days   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var months = ['January','February','March','April','May',
                  'June','July','August','September','October','November','December'];
    return days[d.getDay()] + ', ' + d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  function esc(s) {
    return (s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // Line 4 format: "Source Name | https://url"  OR just  "Source Name"
  function parseSource(raw) {
    var parts = (raw || '').split('|');
    return {
      name: parts[0].trim(),
      url:  parts.length > 1 ? parts[1].trim() : ''
    };
  }

  // ── Parse trending.txt ────────────────────────────────────────────────────
  // 5 non-blank lines = 1 story. Blank line separates stories.
  function parseTxt(raw) {
    var stories = [];
    var lines   = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    var block   = [];

    function flush() {
      if (block.length < 2) { block = []; return; }
      var src = parseSource(block[3] || '');
      stories.push({
        headline:   block[0] || '',
        summary:    block[1] || '',
        badge:      block[2] || 'Update',
        source:     src.name,
        source_url: src.url,
        link:       (block[4] || '').trim() || 'index.html'
      });
      block = [];
    }

    for (var i = 0; i <= lines.length; i++) {
      var line = i < lines.length ? lines[i].trim() : '';
      if (line === '') {
        flush();
      } else {
        block.push(line);
        if (block.length === 5) flush();
      }
    }

    return stories;
  }

  // ── Build one <li> ────────────────────────────────────────────────────────
  function buildItem(story, idx) {
    var num    = String(idx + 1).padStart(2, '0');
    var cls    = badgeClass(story.badge);
    var isExt  = (story.link || '').startsWith('http');
    var target = isExt ? ' target="_blank" rel="noopener noreferrer"' : '';

    // Source: clickable ↗ link when URL provided
    var sourceHtml = '';
    if (story.source) {
      sourceHtml = story.source_url
        ? '<a class="trend-source" href="' + esc(story.source_url) + '" target="_blank" rel="noopener noreferrer">' + esc(story.source) + ' ↗</a>'
        : '<span class="trend-source">' + esc(story.source) + '</span>';
    }

    var li = document.createElement('li');
    li.className = 'trending-item';
    li.innerHTML =
      '<span class="trending-num" aria-hidden="true">' + num + '</span>' +
      '<div class="trending-content">' +
        '<div class="trending-tags">' +
          '<span class="trend-badge ' + cls + '">' + esc(story.badge) + '</span>' +
          sourceHtml +
        '</div>' +
        '<h3 class="trending-headline">' +
          '<a href="' + esc(story.link) + '"' + target + '>' + esc(story.headline) + '</a>' +
        '</h3>' +
        '<p class="trending-summary">' + esc(story.summary) + '</p>' +
      '</div>';
    return li;
  }

  // ── Main ──────────────────────────────────────────────────────────────────
  function run() {
    var section = document.querySelector('.trending-now');
    if (!section) return;

    // Set today's date
    var dateEl = section.querySelector('.trending-date');
    if (dateEl) {
      var now = new Date();
      dateEl.textContent = todayLabel();
      dateEl.setAttribute('datetime', now.toISOString().split('T')[0]);
    }

    var list = section.querySelector('.trending-list');
    if (!list) return;

    // Resolve path relative to page location (handles sub-folders)
    var base = window.location.pathname.replace(/\/[^/]*$/, '/');
    var url  = base + DATA_PATH + '?v=' + Date.now();

    fetch(url)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status + ' fetching ' + url);
        return res.text();
      })
      .then(function (raw) {
        var stories = parseTxt(raw);
        if (!stories.length) {
          console.warn('[trending-loader] trending.txt parsed 0 stories — check format');
          return;
        }
        list.innerHTML = '';
        stories.slice(0, 6).forEach(function (s, i) {
          list.appendChild(buildItem(s, i));
        });
      })
      .catch(function (err) {
        // Log so you can debug in browser DevTools → Console tab
        console.warn('[trending-loader] Could not load trending.txt:', err.message);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

})();
