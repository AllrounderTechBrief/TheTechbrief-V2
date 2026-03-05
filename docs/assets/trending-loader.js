/**
 * trending-loader.js — The Tech Brief
 * ─────────────────────────────────────────────────────────
 * HOW TO UPDATE TRENDING STORIES (the whole workflow):
 *
 *   1. Open Notepad (or Notes / any plain text app)
 *   2. Write each story as 5 plain lines:
 *
 *        Line 1 — Headline
 *        Line 2 — Summary (1-2 sentences)
 *        Line 3 — Badge word  (Breaking / AI Alert / MWC / EVs / Security / Innovation / Gaming)
 *        Line 4 — Source name (e.g. The Verge)
 *        Line 5 — Page link   (e.g. ai-news.html)
 *
 *   3. Leave one blank line between each story. That's it.
 *   4. Go to GitHub → docs/assets/data/trending.txt → pencil ✏️ → paste → Commit
 *   5. Site updates in ~60 seconds.
 *
 * ─────────────────────────────────────────────────────────
 * EXAMPLE — exactly what to type in Notepad:
 *
 *   Apple Unveils iPhone 17 Air
 *   Apple just announced a thinner iPhone Air alongside new iPad models.
 *   Breaking
 *   Apple Newsroom
 *   mobile-gadgets.html
 *
 *   ChatGPT Gets Memory Upgrade
 *   OpenAI gives ChatGPT long-term memory across all conversations.
 *   AI Alert
 *   OpenAI Blog
 *   ai-news.html
 *
 * ─────────────────────────────────────────────────────────
 */

(function () {
  'use strict';

  var DATA_PATH = 'assets/data/trending.txt';

  // Badge word → CSS class (case-insensitive, partial match)
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
    return 'trend-badge--innovation'; // default colour
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

  // ── Parse trending.txt ─────────────────────────────────────────────────
  // 5 non-blank lines = 1 story. Stories separated by blank lines.
  // Format:
  //   Line 1: Headline
  //   Line 2: Summary
  //   Line 3: Badge
  //   Line 4: Source name
  //   Line 5: Link (page.html or https://...)
  function parseTxt(raw) {
    var stories = [];
    // Normalise endings
    var lines = raw.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');

    var block = [];
    for (var i = 0; i <= lines.length; i++) {
      var line = (i < lines.length) ? lines[i].trim() : '';

      if (line === '') {
        // End of a block — collect it if we have content
        if (block.length >= 3) {
          stories.push({
            headline:   block[0] || '',
            summary:    block[1] || '',
            badge:      block[2] || 'Update',
            source:     block[3] || '',
            link:       block[4] || 'index.html'
          });
        }
        block = [];
      } else {
        block.push(line);
        // Once we have 5 lines treat as complete (ignore any extra lines)
        if (block.length === 5) {
          stories.push({
            headline: block[0],
            summary:  block[1],
            badge:    block[2],
            source:   block[3],
            link:     block[4]
          });
          block = [];
        }
      }
    }

    return stories;
  }

  function buildItem(story, index) {
    var num    = String(index + 1).padStart(2, '0');
    var cls    = badgeClass(story.badge);
    var isExt  = (story.link || '').startsWith('http');
    var target = isExt ? ' target="_blank" rel="noopener noreferrer"' : '';

    var li = document.createElement('li');
    li.className = 'trending-item';
    li.innerHTML =
      '<span class="trending-num" aria-hidden="true">' + num + '</span>' +
      '<div class="trending-content">' +
        '<div class="trending-tags">' +
          '<span class="trend-badge ' + cls + '">' + esc(story.badge) + '</span>' +
          (story.source ? '<span class="trend-source">' + esc(story.source) + '</span>' : '') +
        '</div>' +
        '<h3 class="trending-headline">' +
          '<a href="' + esc(story.link || '#') + '"' + target + '>' + esc(story.headline) + '</a>' +
        '</h3>' +
        '<p class="trending-summary">' + esc(story.summary) + '</p>' +
      '</div>';
    return li;
  }

  function run() {
    var section = document.querySelector('.trending-now');
    if (!section) return;

    // Auto-update date to today
    var dateEl = section.querySelector('.trending-date');
    if (dateEl) {
      var now = new Date();
      dateEl.textContent = todayLabel();
      dateEl.setAttribute('datetime', now.toISOString().split('T')[0]);
    }

    var list = section.querySelector('.trending-list');
    if (!list) return;

    fetch(DATA_PATH + '?v=' + Date.now()) // cache bust
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
        // Silent fail — HTML shell stays visible
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

})();
