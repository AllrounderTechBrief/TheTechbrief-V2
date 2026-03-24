# TheTechBrief-V3 — Setup Guide

## What Changed from V2 → V3

### Files Replaced
| File | Change |
|------|--------|
| `site/assets/styles.css` | Full redesign — Playfair Display, IBM Plex Sans, ticker bar, intel-cards |
| `site/template_home.html` | V3 hero, live ticker, per-category sections, skeleton loaders |
| `site/template_category.html` | Category hero, breadcrumb, featured-first layout |
| `scripts/build.py` | V3 Intelligence Pipeline — 8-task Groq analysis system |
| `.github/workflows/build.yml` | Updated job names + V3 comments |
| `site/assets/trending-loader.js` | Improved V3 card renderer with CAT_DATA_MAP |

### Files Unchanged (kept from V2)
- `scripts/generate_articles.py`
- `scripts/summarize.py`
- `data/feeds.json`
- `data/meta.json`
- All `docs/legal/*.html` pages
- `docs/about.html`, `docs/contact.html`, `docs/how-to.html`
- All `docs/articles/*.html` (evergreen articles)

---

## Step 1 — Upload to GitHub

Upload the entire V3 folder to your repo maintaining the structure.

**Critical files that must be uploaded:**
- `scripts/build.py` ✓ (V3 Intelligence Pipeline)
- `site/template_home.html` ✓ (V3 design)
- `site/template_category.html` ✓ (V3 design)
- `site/assets/styles.css` ✓ (V3 stylesheet)
- `site/assets/trending-loader.js` ✓
- `.github/workflows/build.yml` ✓ (V3 workflow)

---

## Step 2 — Add GROQ_API_KEY Secret

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `GROQ_API_KEY`
4. Value: your Groq API key from https://console.groq.com
5. Click **Add secret**

---

## Step 3 — Verify GitHub Pages Settings

1. Settings → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** / Folder: **`/docs`**

---

## Step 4 — Trigger First Build

1. Actions tab → **🤖 The Tech Brief V3 — Intelligence Build**
2. Click **Run workflow** → **Run workflow**
3. Watch the logs — should complete in 90–120 seconds

---

## V3 Intelligence Pipeline Explained

When Groq is enabled, each RSS article is processed through:

1. **Category mapping** — identifies relevant tech categories
2. **Tech term extraction** — names specific technologies, frameworks, protocols
3. **Executive summary** — 3-4 line dense insight (not news recap)
4. **Why it matters** — business impact, industry disruption, security implications
5. **Trend analysis** — 2025–2027 outlook (accelerating/declining/hype vs real)
6. **Strategic insights** — actionable recommendations for organisations
7. **SEO title + meta** — high-CPC keyword optimised
8. **Editorial body** — 140-180 word analytical paragraph

This means every article page on the site reads like expert analyst output, not an automated summary.

---

## Contact Form Activation

In `docs/contact.html`, replace `YOUR_FORMSPREE_ID`:
```
action="https://formspree.io/f/YOUR_FORMSPREE_ID"
```
Sign up at https://formspree.io (free tier available).

---

## AdSense Application Checklist

Before applying:
- [ ] At least 15-20 original articles published
- [ ] About page with editorial team description
- [ ] Privacy Policy present (docs/legal/privacy.html ✓)
- [ ] Terms of Use present (docs/legal/terms.html ✓)
- [ ] Disclaimer present (docs/legal/disclaimer.html ✓)
- [ ] Contact page functional
- [ ] No scraped/copied content (V3 intelligence rewrites handle this)
- [ ] Custom domain active (thetechbrief.net)
- [ ] Site indexed in Google Search Console
