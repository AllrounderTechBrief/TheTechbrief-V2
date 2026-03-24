# The Tech Brief V3 — Intelligence Platform

A premium technology intelligence platform built with GitHub Pages + Groq API.

## What's New in V3

- **Groq Intelligence Pipeline** — every article processed through an 8-task analysis system: category mapping, tech term extraction, executive summaries, trend analysis (2025–2027), strategic insights, and SEO optimisation
- **V3 Design System** — Playfair Display + IBM Plex Sans, live ticker bar, intel-card components, featured-first article layout
- **Rich Article Pages** — Executive Summary callout, Why It Matters, Key Technologies, Trend Outlook, and Strategic Insights sections
- **Homepage Intelligence** — per-category article slices (AI Deep Dives, Cybersecurity Alerts, etc.)
- **Never-blank guarantee** — 3-tier fallback (Groq → cache → local editorial)

## Setup

### 1. GitHub Secrets
Add `GROQ_API_KEY` to your repo secrets:
- Go to Settings → Secrets and variables → Actions → New repository secret
- Name: `GROQ_API_KEY`
- Value: your Groq API key from [console.groq.com](https://console.groq.com)

### 2. GitHub Pages
- Settings → Pages
- Source: Deploy from branch
- Branch: `main` / Folder: `/docs`

### 3. Trigger First Build
- Actions → 🤖 The Tech Brief V3 — Intelligence Build → Run workflow

### 4. Custom Domain
- Your CNAME is already set to `www.thetechbrief.net`
- Add a CNAME DNS record pointing to `allroundertechbrief.github.io`

## Build Schedule
- **Every 6 hours** — RSS fetch + intelligence rewrites
- **Daily 05:00 UTC** — Generate 9 original deep-dive articles (1 per category)
- **On every push** to main

## Structure
```
├── .github/workflows/build.yml   ← CI/CD pipeline
├── data/
│   ├── feeds.json                ← RSS feed URLs
│   ├── meta.json                 ← page titles & descriptions
│   └── article_cache.json        ← Groq rewrite cache (60-day TTL)
├── scripts/
│   ├── build.py                  ← V3 intelligence build pipeline
│   ├── generate_articles.py      ← daily deep-dive generator
│   └── summarize.py              ← text summariser
├── site/                         ← source templates + static files
│   ├── template_home.html        ← homepage Jinja2 template
│   ├── template_category.html    ← category page template
│   └── assets/styles.css         ← V3 production stylesheet
└── docs/                         ← GitHub Pages output (auto-generated)
```

## Contact Form
Replace `YOUR_FORMSPREE_ID` in `docs/contact.html` with your Formspree form ID.
Sign up free at [formspree.io](https://formspree.io).
