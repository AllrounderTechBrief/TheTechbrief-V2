# The Streamic — Automated Article Engine Setup

## One-Time Setup

1. **Add the Groq API secret to GitHub**
   - Go to your repo → Settings → Secrets and Variables → Actions
   - Click **New repository secret**
   - Name: `GROQ_API_KEY`
   - Value: your Groq API key from https://console.groq.com

2. **Enable GitHub Pages**
   - Repo → Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` / `docs` folder

3. **Push this code to your GitHub repo main branch**
   - The first workflow dispatch will trigger a full build

## Manual Trigger

Go to: Actions → 🎙️ Generate + Build The Streamic → Run workflow

## Schedule (UTC)

| Job | Schedule | What it does |
|-----|----------|--------------|
| generate | 05:00 daily | 1 deep-dive article per category (700–900w) |
| generate-trending | 05:30 daily | 6 trending editorial articles (400–500w) |
| build | 00:00/06:00/12:00/18:00 | RSS pull → full docs/ rebuild |

## File Structure

```
/
├── .github/workflows/build.yml     ← Full automation workflow
├── data/
│   ├── feeds.json                  ← RSS sources per category
│   ├── meta.json                   ← Category metadata (SEO, slugs)
│   ├── generated_articles.json     ← Article metadata index
│   └── trending_cache.json         ← Trending generation cache
├── scripts/
│   ├── build.py                    ← Main site builder (RSS → docs/)
│   ├── generate_articles.py        ← Deep-dive article generator
│   └── generate_trending.py        ← Trending articles generator
├── site/
│   ├── template_home.html          ← Featured/home Jinja2 template
│   ├── template_category.html      ← Category page Jinja2 template
│   ├── style.css                   ← Global styles
│   ├── articles/                   ← AI-generated article HTML files
│   └── assets/
│       ├── logo.png
│       ├── fallback.jpg
│       └── data/
│           ├── trending.json       ← Trending widget data
│           └── trending.txt        ← Plain-text trending feed
└── docs/                           ← GitHub Pages output (auto-generated)
```

## NEVER edit docs/ directly — it is overwritten on every build.
## All changes must be made in site/, scripts/, or data/.

## Adding a New RSS Feed

Edit `data/feeds.json` and add the URL to the relevant category array.

## Content Rules (AdSense-safe)

- All generated articles are 100% original prose — never copied from feeds
- RSS feeds are used ONLY for topic context
- No source names, quotes, or paraphrased text from external sites
- Unsplash copyright-safe image pools per category
