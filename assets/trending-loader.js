/**
 * trending-loader.js — The Tech Brief (Redesigned)
 * ──────────────────────────────────────────────────────────────────
 * Reads site/assets/data/trending.json (generated daily by generate_trending.py)
 * Renders full magazine-style trending articles with:
 *  - Hero image (copyright-free Unsplash)
 *  - Category badge + date
 *  - Full intro paragraph
 *  - Expandable full article (4 body paragraphs + conclusion)
 *  - Key insight callout box
 *  - "Read full analysis" internal link
 * ──────────────────────────────────────────────────────────────────
 */

(function () {
  'use strict';

  var JSON_PATH = 'assets/data/trending.json';

  /* ── Inject styles ────────────────────────────────────────────── */
  function injectStyles() {
    if (document.getElementById('ttb-trending-styles')) return;
    var style = document.createElement('style');
    style.id  = 'ttb-trending-styles';
    style.textContent = [
      /* Section wrapper */
      '.trending-now { background:#FFFBF5; border-top:3px solid var(--accent,#2563EB); border-bottom:1px solid #E0D8CF; padding:0; margin:0; }',
      '.trending-inner { max-width:1280px; margin:0 auto; padding:36px 24px 40px; }',

      /* Header row */
      '.trending-meta { display:flex; align-items:center; gap:16px; margin-bottom:28px; flex-wrap:wrap; }',
      '.trending-live { display:flex; align-items:center; gap:6px; }',
      '.live-dot { width:9px; height:9px; background:#22C55E; border-radius:50%; display:inline-block; animation:ttb-pulse 1.8s ease-in-out infinite; }',
      '@keyframes ttb-pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(1.3)} }',
      '.live-label { font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#22C55E; font-family:var(--font-mono,monospace); }',
      '.trending-title { font-family:var(--font-serif,"DM Serif Display",Georgia,serif); font-size:24px; font-weight:400; color:var(--ink,#0D0D12); margin:0; }',
      '.trending-date { font-size:12px; color:var(--ink-3,#7A7A8C); margin-left:auto; font-family:var(--font-mono,monospace); }',

      /* Story grid — 3 columns on desktop, 1 on mobile */
      '.trending-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:24px; list-style:none; margin:0; padding:0; }',
      '@media(max-width:900px){.trending-grid{grid-template-columns:repeat(2,1fr);}}',
      '@media(max-width:560px){.trending-grid{grid-template-columns:1fr;}}',

      /* Individual story card */
      '.tcard { background:#fff; border-radius:12px; border:1px solid #E0D8CF; overflow:hidden; display:flex; flex-direction:column; box-shadow:0 2px 8px rgba(0,0,0,.06); transition:transform .2s,box-shadow .2s; }',
      '.tcard:hover { transform:translateY(-3px); box-shadow:0 6px 24px rgba(0,0,0,.1); }',

      /* Story image */
      '.tcard-img { width:100%; height:190px; object-fit:cover; display:block; background:#EEE; }',

      /* Card body */
      '.tcard-body { padding:18px 20px 14px; flex:1; display:flex; flex-direction:column; gap:10px; }',

      /* Badge + number row */
      '.tcard-meta { display:flex; align-items:center; gap:10px; }',
      '.tcard-num { font-size:12px; font-weight:700; color:var(--ink-3,#7A7A8C); font-family:var(--font-mono,monospace); flex-shrink:0; }',
      '.tcard-badge { display:inline-block; color:#fff; font-size:10px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; padding:3px 9px; border-radius:999px; }',
      '.tcard-cat { font-size:11px; color:var(--ink-3,#7A7A8C); margin-left:auto; }',

      /* Headline */
      '.tcard-headline { font-family:var(--font-serif,"DM Serif Display",Georgia,serif); font-size:17px; line-height:1.3; color:var(--ink,#0D0D12); margin:0; }',
      '.tcard-headline a { color:inherit; text-decoration:none; }',
      '.tcard-headline a:hover { color:var(--accent,#2563EB); }',

      /* Intro (always visible) */
      '.tcard-intro { font-size:13.5px; line-height:1.65; color:var(--ink-2,#3D3D4E); margin:0; }',

      /* Key insight box */
      '.tcard-insight { background:#EEF4FF; border-left:3px solid var(--accent,#2563EB); padding:10px 14px; border-radius:0 6px 6px 0; font-size:12.5px; font-style:italic; color:var(--ink,#0D0D12); line-height:1.55; }',
      '.tcard-insight strong { display:block; font-size:10px; text-transform:uppercase; letter-spacing:.8px; color:var(--accent,#2563EB); font-style:normal; margin-bottom:4px; }',

      /* Expandable full article */
      '.tcard-full { display:none; flex-direction:column; gap:12px; margin-top:4px; border-top:1px solid #E5E5EE; padding-top:14px; }',
      '.tcard-full.open { display:flex; }',
      '.tcard-full p { font-size:13.5px; line-height:1.72; color:var(--ink,#0D0D12); margin:0; }',
      '.tcard-conclusion { font-style:italic; color:var(--ink-2,#3D3D4E) !important; }',

      /* Footer */
      '.tcard-footer { padding:12px 20px; border-top:1px solid #E0D8CF; background:#FAFAF7; display:flex; align-items:center; justify-content:space-between; gap:8px; flex-wrap:wrap; }',
      '.tcard-expand { background:none; border:none; cursor:pointer; font-size:12.5px; font-weight:700; color:var(--accent,#2563EB); font-family:var(--font-body,inherit); padding:0; display:flex; align-items:center; gap:4px; }',
      '.tcard-expand:hover { color:var(--accent-h,#1D4ED8); }',
      '.tcard-expand-icon { display:inline-block; transition:transform .2s; font-style:normal; }',
      '.tcard-expand.expanded .tcard-expand-icon { transform:rotate(180deg); }',
      '.tcard-read { font-size:12px; font-weight:600; color:var(--accent,#2563EB); text-decoration:none; }',
      '.tcard-read:hover { color:var(--accent-h,#1D4ED8); }',
      '.tcard-date { font-size:11px; color:var(--ink-3,#7A7A8C); font-family:var(--font-mono,monospace); }',

      /* Browse footer link */
      '.trending-footer { margin-top:28px; text-align:right; }',
      '.trending-cta { font-size:13px; font-weight:700; color:var(--accent,#2563EB); text-decoration:none; letter-spacing:.3px; }',
      '.trending-cta:hover { color:var(--accent-h,#1D4ED8); }',

      /* Skeleton loader */
      '.tcard-skeleton { background:#fff; border-radius:12px; border:1px solid #E0D8CF; overflow:hidden; }',
      '.skeleton-img { width:100%; height:190px; background:linear-gradient(90deg,#EEE 25%,#F5F5F5 50%,#EEE 75%); background-size:200% 100%; animation:ttb-shimmer 1.5s infinite; }',
      '.skeleton-body { padding:18px 20px; display:flex; flex-direction:column; gap:10px; }',
      '.skeleton-line { height:14px; border-radius:4px; background:linear-gradient(90deg,#EEE 25%,#F5F5F5 50%,#EEE 75%); background-size:200% 100%; animation:ttb-shimmer 1.5s infinite; }',
      '@keyframes ttb-shimmer { to{background-position:-200% 0} }',
    ].join('\n');
    document.head.appendChild(style);
  }

  /* ── Helpers ──────────────────────────────────────────────────── */
  function esc(s) {
    return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function fmtDate(iso) {
    try {
      var d = new Date(iso);
      var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      return months[d.getUTCMonth()] + ' ' + d.getUTCDate() + ', ' + d.getUTCFullYear();
    } catch(e) { return iso || ''; }
  }

  function todayLabel() {
    var d = new Date();
    var days   = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    var months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    return days[d.getDay()] + ', ' + d.getDate() + ' ' + months[d.getMonth()] + ' ' + d.getFullYear();
  }

  /* ── Build a single story card ────────────────────────────────── */
  function buildCard(story, index) {
    var li = document.createElement('li');
    li.className = 'tcard';

    var num        = String(index + 1).padStart(2, '0');
    var badgeColor = story.badge_color || '#2563EB';
    var catUrl     = story.cat_url || 'index.html';
    var date       = fmtDate(story.date || '');

    // Build paragraphs HTML
    var parasHTML = '';
    if (Array.isArray(story.paragraphs)) {
      story.paragraphs.forEach(function(p, i) {
        parasHTML += '<p' + (i === story.paragraphs.length - 1 ? '' : '') + '>' + esc(p) + '</p>';
      });
    }

    li.innerHTML =
      /* Image */
      (story.image ? '<img class="tcard-img" src="' + esc(story.image) + '" alt="' + esc(story.headline) + '" loading="lazy" width="400" height="190">' : '') +

      /* Body */
      '<div class="tcard-body">' +
        '<div class="tcard-meta">' +
          '<span class="tcard-num">' + num + '</span>' +
          '<span class="tcard-badge" style="background:' + badgeColor + '">' + esc(story.badge || 'Tech') + '</span>' +
          '<span class="tcard-cat">' + esc(story.category || '') + '</span>' +
        '</div>' +
        '<h3 class="tcard-headline"><a href="' + esc(catUrl) + '">' + esc(story.headline) + '</a></h3>' +
        '<p class="tcard-intro">' + esc(story.intro || '') + '</p>' +
        (story.key_insight ?
          '<div class="tcard-insight"><strong>Key Insight</strong>' + esc(story.key_insight) + '</div>' : '') +
        /* Full article (expandable) */
        '<div class="tcard-full" id="tcard-full-' + index + '">' +
          parasHTML +
          (story.conclusion ? '<p class="tcard-conclusion">' + esc(story.conclusion) + '</p>' : '') +
        '</div>' +
      '</div>' +

      /* Footer */
      '<div class="tcard-footer">' +
        '<button class="tcard-expand" data-target="tcard-full-' + index + '" aria-expanded="false">' +
          'Read full analysis <i class="tcard-expand-icon" aria-hidden="true">▾</i>' +
        '</button>' +
        '<span class="tcard-date">' + date + '</span>' +
      '</div>';

    /* Expand/collapse toggle */
    var btn = li.querySelector('.tcard-expand');
    if (btn) {
      btn.addEventListener('click', function() {
        var targetId = this.getAttribute('data-target');
        var fullDiv  = document.getElementById(targetId);
        if (!fullDiv) return;
        var isOpen = fullDiv.classList.toggle('open');
        this.classList.toggle('expanded', isOpen);
        this.setAttribute('aria-expanded', isOpen);
        this.innerHTML = (isOpen ? 'Collapse article ' : 'Read full analysis ') +
          '<i class="tcard-expand-icon" aria-hidden="true">' + (isOpen ? '▴' : '▾') + '</i>';
      });
    }

    return li;
  }

  /* ── Skeleton loaders ─────────────────────────────────────────── */
  function buildSkeletons(list, n) {
    for (var i = 0; i < n; i++) {
      var li = document.createElement('li');
      li.className = 'tcard-skeleton';
      li.innerHTML =
        '<div class="skeleton-img"></div>' +
        '<div class="skeleton-body">' +
          '<div class="skeleton-line" style="width:30%"></div>' +
          '<div class="skeleton-line" style="width:80%"></div>' +
          '<div class="skeleton-line" style="width:65%"></div>' +
          '<div class="skeleton-line" style="width:90%"></div>' +
          '<div class="skeleton-line" style="width:55%"></div>' +
        '</div>';
      list.appendChild(li);
    }
  }

  /* ── Rebuild section HTML for JSON-driven design ──────────────── */
  function rebuildSection(section, stories) {
    section.innerHTML =
      '<div class="trending-inner">' +
        '<div class="trending-meta">' +
          '<div class="trending-live">' +
            '<span class="live-dot" aria-hidden="true"></span>' +
            '<span class="live-label">Live</span>' +
          '</div>' +
          '<h2 class="trending-title">Tech Trending Now</h2>' +
          '<time class="trending-date" datetime="' + new Date().toISOString().split('T')[0] + '">' + todayLabel() + '</time>' +
        '</div>' +
        '<ol class="trending-grid" aria-label="Trending stories" id="ttb-trending-list"></ol>' +
        '<div class="trending-footer">' +
          '<a href="ai-news.html" class="trending-cta">Browse all tech news →</a>' +
        '</div>' +
      '</div>';

    var list = section.querySelector('#ttb-trending-list');
    if (!list) return;

    buildSkeletons(list, 3);

    setTimeout(function() {
      list.innerHTML = '';
      stories.slice(0, 6).forEach(function(story, i) {
        list.appendChild(buildCard(story, i));
      });
    }, 400);
  }

  /* ── Main ─────────────────────────────────────────────────────── */
  function run() {
    var section = document.querySelector('.trending-now');
    if (!section) return;

    injectStyles();

    // Show skeleton immediately
    var inner = section.querySelector('.trending-inner');
    var list  = section.querySelector('.trending-list');
    if (list) buildSkeletons(list, 3);

    // Try JSON first (Groq-generated articles)
    fetch(JSON_PATH + '?v=' + Date.now())
      .then(function(res) {
        if (!res.ok) throw new Error('trending.json not found');
        return res.json();
      })
      .then(function(data) {
        if (data && Array.isArray(data.stories) && data.stories.length > 0) {
          rebuildSection(section, data.stories);
        } else {
          throw new Error('empty stories array');
        }
      })
      .catch(function() {
        // Fallback: try trending.txt
        fetch('assets/data/trending.txt?v=' + Date.now())
          .then(function(r) { return r.text(); })
          .then(function(raw) {
            // simple txt parser — keep old behaviour for fallback
            if (list) {
              list.innerHTML = '';
              var lines = raw.replace(/\r\n/g,'\n').split('\n');
              var block = [], stories = [];
              lines.forEach(function(line) {
                var l = line.trim();
                if (l === '') {
                  if (block.length >= 3) stories.push({headline:block[0],intro:block[1],badge:block[2],category:block[3]||'',cat_url:block[4]||'index.html',badge_color:'#2563EB',date:''});
                  block = [];
                } else { block.push(l); }
              });
              stories.slice(0,6).forEach(function(s,i){ list.appendChild(buildCard(s,i)); });
            }
          })
          .catch(function() { /* silent fail */ });
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

})();
