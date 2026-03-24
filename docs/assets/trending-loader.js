/**
 * trending-loader.js — The Tech Brief V3
 * Loads trending.json, renders intel-cards into #trending-grid.
 * Falls back to trending.txt if JSON unavailable.
 */

(function () {
  'use strict';

  var CAT_COLORS = {
    'ai-news':               '#7C3AED',
    'cybersecurity-updates': '#DC2626',
    'mobile-gadgets':        '#0891B2',
    'evs-automotive':        '#059669',
    'startups-business':     '#D97706',
    'enterprise-tech':       '#1A56DB',
    'gaming':                '#7C3AED',
    'consumer-tech':         '#0891B2',
    'broadcast-tech':        '#BE185D',
  };

  var CAT_DATA_MAP = {
    'ai-news':               'ai',
    'cybersecurity-updates': 'cyber',
    'mobile-gadgets':        'mobile',
    'evs-automotive':        'evs',
    'startups-business':     'startup',
    'enterprise-tech':       'enterprise',
    'gaming':                'gaming',
    'consumer-tech':         'consumer',
    'broadcast-tech':        'broadcast',
  };

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function buildCard(story) {
    var catSlug   = story.cat_slug || 'ai-news';
    var catColor  = CAT_COLORS[catSlug] || '#1A56DB';
    var dataAttr  = CAT_DATA_MAP[catSlug] || 'ai';
    var catUrl    = story.cat_url || 'index.html';
    var badge     = escapeHtml(story.badge || 'Tech');
    var headline  = escapeHtml(story.headline || '');
    var summary   = escapeHtml(story.summary || story.intro || '');
    var date      = escapeHtml(story.date || '');

    return '<article class="intel-card" data-cat="' + dataAttr + '" style="border-left-color:' + catColor + ';">' +
      '<span class="intel-badge" style="background:' + catColor + '1a;color:' + catColor + ';">' + badge + '</span>' +
      '<h3><a href="' + escapeHtml(catUrl) + '">' + headline + '</a></h3>' +
      '<p>' + summary.substring(0, 150) + (summary.length > 150 ? '…' : '') + '</p>' +
      '<div class="intel-footer">' +
        '<time>' + date + '</time>' +
        '<a href="' + escapeHtml(catUrl) + '" class="intel-read">Read brief</a>' +
      '</div>' +
    '</article>';
  }

  function renderStories(stories) {
    var grid = document.getElementById('trending-grid');
    var placeholder = document.getElementById('trending-placeholder');
    if (!grid) return;

    if (!stories || stories.length === 0) {
      if (placeholder) placeholder.style.display = 'none';
      return;
    }

    var html = '';
    for (var i = 0; i < Math.min(stories.length, 6); i++) {
      html += buildCard(stories[i]);
    }

    grid.innerHTML = html;
    grid.style.display = 'grid';
    grid.classList.add('loaded');
    if (placeholder) placeholder.style.display = 'none';
  }

  function loadFromTxt(url) {
    fetch(url, { cache: 'no-store' })
      .then(function (r) { return r.text(); })
      .then(function (text) {
        var lines = text.trim().split('\n');
        var stories = [];
        var CAT_SLUGS = Object.keys(CAT_COLORS);
        for (var i = 0; i + 4 < lines.length; i += 6) {
          var catUrl = lines[i + 4] ? lines[i + 4].trim() : 'index.html';
          var catSlug = catUrl.replace('.html', '');
          stories.push({
            headline:  lines[i]     ? lines[i].trim() : '',
            summary:   lines[i + 1] ? lines[i + 1].trim() : '',
            badge:     lines[i + 2] ? lines[i + 2].trim() : 'Tech',
            cat_slug:  catSlug,
            cat_url:   catUrl,
            date:      '',
          });
        }
        renderStories(stories);
      })
      .catch(function () {
        var placeholder = document.getElementById('trending-placeholder');
        if (placeholder) placeholder.style.display = 'none';
      });
  }

  function init() {
    var BASE = (function () {
      var s = document.querySelector('link[rel="stylesheet"]');
      if (s) {
        var href = s.getAttribute('href') || '';
        if (href.indexOf('../') === 0) return '../';
      }
      return '';
    })();

    var jsonUrl = BASE + 'assets/data/trending.json';
    var txtUrl  = BASE + 'assets/data/trending.txt';

    fetch(jsonUrl, { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('JSON not found');
        return r.json();
      })
      .then(function (data) {
        var stories = data.stories || data;
        if (Array.isArray(stories) && stories.length > 0) {
          renderStories(stories);
        } else {
          loadFromTxt(txtUrl);
        }
      })
      .catch(function () {
        loadFromTxt(txtUrl);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
