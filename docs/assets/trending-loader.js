/**
 * trending-loader.js — The Tech Brief
 * ─────────────────────────────────────────────────────────────────
 * HOW TO UPDATE TRENDING STORIES (daily workflow):
 *
 *   1. Open Notepad / Notes / any plain text app
 *   2. Write each story as exactly 5 lines:
 *
 *        Line 1 — Headline
 *        Line 2 — Summary (1-2 sentences)
 *        Line 3 — Badge  (Breaking / Security / AI Alert / MWC / EVs / Innovation / Gaming / Launch / Review)
 *        Line 4 — Source Name | https://real-source-url
 *        Line 5 — Page link  (e.g. ai-news.html)
 *
 *   3. Leave ONE blank line between stories. Nothing else needed.
 *   4. GitHub → docs/assets/data/trending.txt → pencil ✏️ → paste → Commit
 *   5. Site goes live in ~60 seconds.
 *
 * ─────────────────────────────────────────────────────────────────
 * EXAMPLE — copy this format exactly:
 *
 *   Apple Unveils iPhone 17 Air
 *   Apple just announced a thinner iPhone Air alongside new iPad models at today's event.
 *   Breaking
 *   Apple Newsroom | https://www.apple.com/newsroom/
 *   mobile-gadgets.html
 *
 *   ChatGPT Gets Long-Term Memory
 *   OpenAI gives ChatGPT memory that works across all your conversations.
 *   AI Alert
 *   OpenAI Blog | https://openai.com/news/
 *   ai-news.html
 *
 * ─────────────────────────────────────────────────────────────────
 * Source line format:
 *   "Source Name | https://url"  → name becomes a clickable link to the real article
 *   "Source Name"                → plain text (no link) — both formats work fine
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
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Parse source line: "Name | https://url" or just "Name" ───────────────
  function parseSource(raw) {
    var parts = (raw || '').split('|');
    return {
      name: parts[0].trim(),
      url:  parts.length > 1 ? parts[1].trim() : ''
    };
  }

  // ── Parse trending.txt ────────────────────────────────────────────────────
  // 5 non-blank lines = 1 story, blank line separates stories.
  function parseTxt(raw) {
    var stories = [];
    var lines = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    var block = [];

    function flushBlock() {
      if (block.length < 3) { block = []; return; }
      var src = parseSource(block[3] || '');
      stories.push({
        headline:   block[0] || '',
        summary:    block[1] || '',
        badge:      block[2] || 'Update',
        source:     src.name,
        source_url: src.url,
        link:       block[4] || 'index.html'
      });
      block = [];
    }

    for (var i = 0; i <= lines.length; i++) {
      var line = i < lines.length ? lines[i].trim() : '';
      if (line === '') {
        flushBlock();
      } else {
        block.push(line);
        if (block.length === 5) flushBlock();
      }
    }

    return stories;
  }

  // ── Build one <li> item ───────────────────────────────────────────────────
  function buildItem(story, index) {
    var num    = String(index + 1).padStart(2, '0');
    var cls    = badgeClass(story.badge);
    var isExt  = (story.link || '').startsWith('http');
    var target = isExt ? ' target="_blank" rel="noopener noreferrer"' : '';

    // Source: clickable link if URL provided, plain span otherwise
    var sourceHtml = '';
    if (story.source) {
      if (story.source_url) {
        sourceHtml = '<a class="trend-source" href="' + esc(story.source_url) +
          '" target="_blank" rel="noopener noreferrer">' + esc(story.source) + ' ↗</a>';
      } else {
        sourceHtml = '<span class="trend-source">' + esc(story.source) + '</span>';
      }
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
          '<a href="' + esc(story.link || '#') + '"' + target + '>' + esc(story.headline) + '</a>' +
        '</h3>' +
        '<p class="trending-summary">' + esc(story.summary) + '</p>' +
      '</div>';
    return li;
  }

  // ── Main ──────────────────────────────────────────────────────────────────
  function run() {
    var section = document.querySelector('.trending-now');
    if (!section) return;

    var dateEl = section.querySelector('.trending-date');
    if (dateEl) {
      var now = new Date();
      dateEl.textContent = todayLabel();
      dateEl.setAttribute('datetime', now.toISOString().split('T')[0]);
    }

    var list = section.querySelector('.trending-list');
    if (!list) return;

    fetch(DATA_PATH + '?v=' + Date.now())
      .then(function (res) {
        if (!res.ok) throw new Error('trending.txt not found');
        return res.text();
      })
      .then(function (raw) {
        var stories = parseTxt(raw);
        if (!stories.length) return;
        list.innerHTML = '';
        stories.slice(0, 6).forEach(function (s, i) {
          list.appendChild(buildItem(s, i));
        });
      })
      .catch(function () {
        // Silent — existing HTML stays visible if fetch fails
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

})();
