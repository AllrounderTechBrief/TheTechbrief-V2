/* THE STREAMIC – Main JavaScript (pubDate sorting + lazy loading) */
(() => {
  // -------------------------------------------
  // CONFIG
  // -------------------------------------------
  const NEWS_FILE = 'data/news.json?v=' + Date.now(); // cache-bust JSON
  const ITEMS_PER_BATCH = 12;

  const CATEGORY_FALLBACKS = {
    'featured': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80&fm=webp',
    'newsroom': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80&fm=webp',
    'playout': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80&fm=webp',
    'infrastructure': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80&fm=webp',
    'graphics': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80&fm=webp',
    'cloud': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80&fm=webp',
    'cloud-production': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80&fm=webp',
    'streaming': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=800&q=80&fm=webp',
    // 🔁 renamed key from 'audio-ai' to 'ai-post-production'
    'ai-post-production': 'https://images.unsplash.com/photo-1589903308904-1010c2294adc?w=800&q=80&fm=webp',
  };

  // -------------------------------------------
  // STATE
  // -------------------------------------------
  let imageObserver = null;
  let allItems = [];
  let displayedCount = 0;

  // -------------------------------------------
  // UTILS
  // -------------------------------------------
  function getFallbackImage(category) {
    const cat = (category || '').toLowerCase().trim();
    if (cat === 'cloud') return CATEGORY_FALLBACKS['cloud-production'];
    if (cat === 'newsroom') return CATEGORY_FALLBACKS['featured'];
    return CATEGORY_FALLBACKS[cat] || CATEGORY_FALLBACKS['featured'];
  }

  function isValidImageUrl(url) {
    if (!url || typeof url !== 'string') return false;
    const u = url.trim().toLowerCase();
    if (!u.startsWith('http')) return false; // must be http/https
    // Reject obvious tracking pixels
    const reject = ['1x1', 'spacer', 'blank', 'pixel', 'avatar', 'gravatar', 'tracker'];
    if (reject.some(p => u.includes(p))) return false;
    return true; // Allow URLs without extensions - CDN URLs are OK
  }

  function setupImageObserver() {
    if (!('IntersectionObserver' in window)) return null;
    return new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          const src = img.dataset.src;
          if (src) {
            img.src = src;
            img.classList.remove('lazy');
            obs.unobserve(img);
          }
        }
      });
    }, { rootMargin: '50px', threshold: 0.01 });
  }

  function createLazyImage(imageUrl, alt, category) {
    const img = document.createElement('img');
    img.alt = alt || 'Article image';
    const chosen = isValidImageUrl(imageUrl) ? imageUrl : getFallbackImage(category);

    if (imageObserver) {
      img.dataset.src = chosen;
      img.src =
        'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; // 1x1
      img.classList.add('lazy');
      imageObserver.observe(img);
    } else {
      img.src = chosen;
      img.loading = 'lazy';
    }

    img.addEventListener('error', () => {
      const fb = getFallbackImage(category);
      if (img.src !== fb) img.src = fb;
    });

    return img;
  }

  // Render a nicer category label (e.g., ai-post-production → AI & POST-PRODUCTION)
  function humanizeCategory(raw) {
    const cat = (raw || '').toLowerCase();
    const map = {
      'ai-post-production': 'AI & POST-PRODUCTION',
      'cloud-production': 'CLOUD PRODUCTION',
    };
    if (map[cat]) return map[cat];
    return cat.toUpperCase().replace(/-/g, ' ');
  }

  // -------------------------------------------
  // RENDER
  // -------------------------------------------
  function renderLargeCard(item) {
    const article = document.createElement('a');
    article.className = 'bento-card-large';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';

    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = createLazyImage(item.image, item.title, item.category);
    figure.appendChild(img);
    article.appendChild(figure);

    const body = document.createElement('div');
    body.className = 'card-body';

    const title = document.createElement('h3');
    title.textContent = item.title || 'Untitled';
    body.appendChild(title);

    // Brief / summary — rendered when feed provides one (additive field)
    if (item.summary && item.summary.trim()) {
      const brief = document.createElement('p');
      brief.className = 'card-summary';
      brief.textContent = item.summary.trim();
      body.appendChild(brief);
    }

    const meta = document.createElement('div');
    meta.className = 'card-meta';

    const source = document.createElement('span');
    source.className = 'source';
    source.textContent = item.source || '';
    meta.appendChild(source);

    if (item.category) {
      const tag = document.createElement('span');
      tag.className = 'category-tag';
      tag.textContent = humanizeCategory(item.category);
      meta.appendChild(tag);
    }

    body.appendChild(meta);
    article.appendChild(body);
    return article;
  }

  function renderListCard(item) {
    const article = document.createElement('a');
    article.className = 'list-card-horizontal';
    article.href = item.link || '#';
    article.target = '_blank';
    article.rel = 'noopener noreferrer';

    const figure = document.createElement('figure');
    figure.className = 'card-image';
    const img = createLazyImage(item.image, item.title, item.category);
    figure.appendChild(img);
    article.appendChild(figure);

    const body = document.createElement('div');
    body.className = 'card-body';

    const title = document.createElement('h3');
    title.textContent = item.title || 'Untitled';
    body.appendChild(title);

    const meta = document.createElement('div');
    meta.className = 'card-meta';

    const source = document.createElement('span');
    source.textContent = item.source || '';
    meta.appendChild(source);

    if (item.category) {
      const tag = document.createElement('span');
      tag.textContent = ` • ${humanizeCategory(item.category)}`;
      meta.appendChild(tag);
    }

    body.appendChild(meta);
    article.appendChild(body);
    return article;
  }

  // -------------------------------------------
  // SORT / DIVERSITY
  // -------------------------------------------
  function capPerSource(items, perSource = 6) {
    const counts = new Map();
    const out = [];
    for (const it of items) {
      const src = (it.source || '').trim().toLowerCase();
      const c = counts.get(src) || 0;
      if (c < perSource) {
        out.push(it);
        counts.set(src, c + 1);
      }
    }
    return out;
  }

  // Legacy kept for reference (no longer used for category pages)
  function smartSort(items) {
    items.sort((a, b) => {
      const dateA = a.pubDate ? new Date(a.pubDate) : new Date(a.timestamp * 1000);
      const dateB = b.pubDate ? new Date(b.pubDate) : new Date(b.timestamp * 1000);
      return dateB - dateA;
    });
    const withImages = items.filter(it => isValidImageUrl(it.image));
    const withoutImages = items.filter(it => !isValidImageUrl(it.image));
    const uniqueSources = new Set(items.map(it => (it.source || '').trim().toLowerCase())).size;
    const dynamicCap = Math.max(6, Math.ceil(items.length / Math.max(uniqueSources, 1)));
    const diversified = capPerSource(withImages, dynamicCap);
    return [...diversified, ...withoutImages];
  }

  /**
   * interleaveBySource — round-robin across sources so no single publisher
   * dominates the top of a category page (e.g. Vizrt in Graphics).
   * Each source bucket is sorted newest-first internally.
   */
  function interleaveBySource(items) {
    // Group into source buckets, preserving insertion order
    const buckets = new Map();
    items.forEach(item => {
      const src = (item.source || 'unknown').trim();
      if (!buckets.has(src)) buckets.set(src, []);
      buckets.get(src).push(item);
    });

    // Sort each bucket newest-first
    buckets.forEach(bucket => {
      bucket.sort((a, b) => {
        const da = a.pubDate ? new Date(a.pubDate) : new Date(a.timestamp * 1000);
        const db = b.pubDate ? new Date(b.pubDate) : new Date(b.timestamp * 1000);
        return db - da;
      });
    });

    // Round-robin: take one from each source in turn
    const sources = [...buckets.keys()];
    const result = [];
    const maxLen = Math.max(...sources.map(s => buckets.get(s).length));
    for (let i = 0; i < maxLen; i++) {
      for (const src of sources) {
        const bucket = buckets.get(src);
        if (i < bucket.length) result.push(bucket[i]);
      }
    }
    return result;
  }

  // -------------------------------------------
  // DATA LOADING (from local JSON)
  // -------------------------------------------
  async function loadLocalJson() {
    const res = await fetch(NEWS_FILE, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    
    // Handle both old (array) and new (object) formats
    if (Array.isArray(data)) {
      // Legacy format: just an array of items
      return { items: data, featured_priority: [] };
    } else if (data && typeof data === 'object') {
      // New format: { featured_priority: [...], items: [...] }
      return {
        items: data.items || [],
        featured_priority: data.featured_priority || []
      };
    }
    
    throw new Error('Invalid JSON shape');
  }

  // Sources that are general consumer/tech press — never shown on specialist pages.
  // Client-side safety net so stale news.json data cannot pollute category pages.
  const BLOCKED_SOURCES_BY_CATEGORY = {
    'streaming':          ['techcrunch', 'engadget', 'wired'],
    'infrastructure':     ['techcrunch', 'engadget', 'wired'],
    'cloud':              ['techcrunch', 'engadget', 'wired'],
    'ai-post-production': ['techcrunch', 'engadget', 'wired'],
    'playout':            ['techcrunch', 'engadget', 'wired'],
    'graphics':           ['techcrunch', 'engadget', 'wired'],
    'newsroom':           ['techcrunch', 'engadget', 'wired'],
  };

  function filterByCategory(items, category) {
    const cat = (category || '').trim().toLowerCase();

    // FEATURED or empty => show everything (homepage / featured landing)
    if (!cat || cat === 'featured') return items;

    // Block general-tech sources from every specialist category
    const blocked = BLOCKED_SOURCES_BY_CATEGORY[cat] || [];
    const notBlocked = it => !blocked.includes((it.source || '').trim().toLowerCase());

    // ai-post-production
    if (cat === 'ai-post-production') {
      return items.filter(it =>
        (it.category || '').toLowerCase() === 'ai-post-production' && notBlocked(it)
      );
    }

    // cloud-production / cloud alias
    if (cat === 'cloud-production' || cat === 'cloud') {
      return items.filter(it => {
        const c = (it.category || '').toLowerCase();
        return (c === 'cloud' || c === 'cloud-production') && notBlocked(it);
      });
    }

    // infrastructure
    if (cat === 'infrastructure') {
      return items.filter(it => {
        const c = (it.category || '').toLowerCase();
        return (c === 'infrastructure' || c === 'security') && notBlocked(it);
      });
    }

    return items.filter(it =>
      (it.category || '').toLowerCase() === cat && notBlocked(it)
    );
  }

  // -------------------------------------------
  // INCREMENTAL RENDERING
  // -------------------------------------------
  function renderNextBatch() {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    if (!largeGrid || !listGrid) return;

    const nextItems = allItems.slice(displayedCount, displayedCount + ITEMS_PER_BATCH);
    if (nextItems.length === 0) {
      hideLoadMoreButton();
      return;
    }

    const schedule = window.requestIdleCallback || ((cb) => setTimeout(cb, 50));
    schedule(() => {
      const largeFrag = document.createDocumentFragment();
      const listFrag = document.createDocumentFragment();

      nextItems.forEach((item, idx) => {
        const absoluteIndex = displayedCount + idx;
        if (absoluteIndex < 12) {
          largeFrag.appendChild(renderLargeCard(item));
        } else {
          listFrag.appendChild(renderListCard(item));
        }
      });

      largeGrid.appendChild(largeFrag);
      listGrid.appendChild(listFrag);
      displayedCount += nextItems.length;

      const btn = document.getElementById('loadMoreBtn');
      if (btn && displayedCount >= allItems.length) {
        btn.parentElement.style.display = 'none';
      }
    });
  }

  function createLoadMoreButton() {
    if (document.getElementById('loadMoreBtn')) return;
    const mainContent = document.querySelector('.category-content') || document.querySelector('main');
    if (!mainContent) return;

    const wrap = document.createElement('div');
    wrap.className = 'view-more-wrap';
    wrap.style.marginTop = '48px';

    const btn = document.createElement('button');
    btn.id = 'loadMoreBtn';
    btn.className = 'btn-view-more';
    btn.textContent = 'Load More';
    btn.addEventListener('click', () => renderNextBatch());

    wrap.appendChild(btn);
    mainContent.appendChild(wrap);
  }

  function hideLoadMoreButton() {
    const btn = document.getElementById('loadMoreBtn');
    if (btn && btn.parentElement) btn.parentElement.style.display = 'none';
  }

  // -------------------------------------------
  // PAGE LOADER
  // -------------------------------------------
  function loadCategoryPage(category) {
    const largeGrid = document.getElementById('bentoGridLarge');
    const listGrid = document.getElementById('listGrid');
    if (!largeGrid || !listGrid) return;

    largeGrid.innerHTML = '<p class="empty-state">Loading articles...</p>';
    listGrid.innerHTML = '';
    allItems = [];
    displayedCount = 0;

    loadLocalJson()
      .then(data => {
        const { items, featured_priority } = data;
        const cat = (category || '').trim().toLowerCase();
        
        let filtered;
        
        // FEATURED PAGE: Show priority items first, then rest
        if (!cat || cat === 'featured') {
          // Get IDs of priority items to avoid duplicates
          const priorityIds = new Set(featured_priority.map(item => item.guid || item.link));
          
          // Filter out priority items from main items list
          const remainingItems = items.filter(item => 
            !priorityIds.has(item.guid || item.link)
          );
          
          // Combine: featured_priority first, then remaining items
          // Guard: strip any items whose link isn't a real http(s) URL
          const safeFilter = arr => arr.filter(it => {
            const l = (it.link || '').trim();
            return l.startsWith('http://') || l.startsWith('https://');
          });
          filtered = [...safeFilter(featured_priority), ...safeFilter(remainingItems)];
        } else {
          // OTHER CATEGORY PAGES: Normal filtering
          const catItems = filterByCategory(items, category);
          // Guard: strip any items whose link isn't a real http(s) URL
          filtered = catItems.filter(it => {
            const l = (it.link || '').trim();
            return l.startsWith('http://') || l.startsWith('https://');
          });
        }
        
        if (filtered.length === 0) {
          largeGrid.innerHTML = '<p class="empty-state">No articles yet. Check back soon!</p>';
          return;
        }
        
        // For non-featured pages, interleave by source so no single publisher dominates
        // For featured, we already have the order we want (priority + sorted rest)
        allItems = (cat === 'featured' || !cat) ? filtered : interleaveBySource(filtered);
        
        largeGrid.innerHTML = '';
        renderNextBatch();
        if (allItems.length > ITEMS_PER_BATCH) createLoadMoreButton();
      })
      .catch(err => {
        console.error('Load error:', err);
        largeGrid.innerHTML = '<p class="empty-state">Failed to load articles. Please try again later.</p>';
      });
  }

  // -------------------------------------------
  // MOBILE NAV
  // -------------------------------------------
  function initMobileNav() {
    const toggle = document.querySelector('.nav-toggle');
    const links = document.querySelector('.nav-links');
    if (!toggle || !links) return;

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      links.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (links.classList.contains('active') &&
          !toggle.contains(e.target) &&
          !links.contains(e.target)) {
        links.classList.remove('active');
      }
    });

    links.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => links.classList.remove('active'));
    });
  }

  // -------------------------------------------
  // INIT
  // -------------------------------------------
  function init() {
    console.log('The Streamic – main.js loaded');
    imageObserver = setupImageObserver();
    initMobileNav();

    const category = (document.body.dataset.category || '').trim().toLowerCase();
    if (category) loadCategoryPage(category);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose helpers for debugging
  window.loadCategory = loadCategoryPage;
})();
