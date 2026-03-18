# TheTechBrief-V2 — Setup & Fix Guide

## Why You Were Getting 404

Two separate issues were causing the 404:

1. **Missing `data/` folder** — `feeds.json` and `meta.json` were not in the repo.
   The build script crashed silently because it couldn't find these files.

2. **Wrong Pages source** — GitHub Pages was serving `site/index.html` directly
   from the `main` branch placeholder file (which just says "building…").
   Your custom `Build Tech Brief` workflow output was never being served.

---

## How This Repo Now Works

```
main branch
├── .github/workflows/build.yml   ← runs every 6 hrs + on push
├── data/
│   ├── feeds.json                ← RSS feed URLs
│   └── meta.json                 ← page titles & descriptions
├── scripts/
│   ├── build.py                  ← main generator
│   └── summarize.py              ← text summariser
└── site/                         ← GitHub Pages serves this folder
    ├── index.html                ← OVERWRITTEN by build on each run
    ├── ai-news.html              ← OVERWRITTEN by build on each run
    ├── [other category pages]    ← OVERWRITTEN by build on each run
    ├── about.html                ← static — stays as-is
    ├── contact.html              ← static — stays as-is
    ├── assets/                   ← static CSS + SVG
    ├── legal/                    ← static legal pages
    └── articles/                 ← static original articles
```

The build workflow:
1. Checks out `main`
2. Runs `scripts/build.py` which fetches RSS feeds and writes HTML into `site/`
3. Commits and pushes the updated `site/` files back to `main`
4. GitHub Pages' own `pages-build-deployment` picks up the commit and deploys

---

## Step-by-Step Setup (Do This Once)

### Step 1 — Upload all files from this zip to your repo

Upload everything maintaining the folder structure shown above.
In GitHub UI: go to each folder and use "Add file → Upload files".

**Critical folders that must exist:**
- `data/feeds.json` ✓
- `data/meta.json` ✓
- `scripts/build.py` ✓
- `scripts/summarize.py` ✓
- `site/template_home.html` ✓
- `site/template_category.html` ✓

### Step 2 — Verify GitHub Pages settings

1. Go to your repo → **Settings** → **Pages**
2. Under **Source**: select **"Deploy from a branch"**
3. Branch: **`main`**   Folder: **`/ (root)`** → **No — use `/site`**

   ⚠️ GitHub Pages can serve a subfolder:
   - Branch: `main`
   - Folder: `/site`   ← set this

   If `/site` subfolder option is not available in the UI, use the root and
   move all `site/` contents up one level, OR keep using the gh-pages approach
   from the previous build.yml (both work — see note below).

### Step 3 — Trigger the build manually

1. Go to **Actions** tab in your repo
2. Click **"Build Tech Brief"** in the left sidebar
3. Click **"Run workflow"** → **"Run workflow"** (green button)
4. Watch the logs — should complete in ~60–90 seconds

### Step 4 — Verify

After the workflow succeeds, visit:
`https://allroundertechbrief.github.io/TheTechBrief/`

Or for the V2 repo:
`https://allroundertechbrief.github.io/TheTechbrief-V2/`

---

## If Pages Can't Serve `/site` Subfolder

Some GitHub accounts can only serve from root or `docs/` folder.
In that case, use this alternative workflow approach:

Change the last step in `build.yml` from the git commit approach to:

```yaml
      - name: Deploy to gh-pages branch
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: site
          publish_branch: gh-pages
          force_orphan: true
```

Then set Pages source to: Branch `gh-pages` / folder `/ (root)`.

---

## Build Schedule

The workflow runs automatically:
- Every **6 hours** (cron: `0 */6 * * *`)
- On every push to `main`
- Manually via Actions → Run workflow

---

## Contact Form Activation

The contact form at `/contact.html` uses Formspree.
To activate it:
1. Sign up free at https://formspree.io
2. Create a new form — copy your form ID (e.g. `xabc1234`)
3. In `site/contact.html`, replace `YOUR_FORMSPREE_ID` with your ID:
   `action="https://formspree.io/f/xabc1234"`
4. Commit the change — form will now send emails to your address
