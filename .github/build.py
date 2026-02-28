name: Build Tech Brief

on:
  push:
    branches: [ main ]
  schedule:
    - cron: "0 */6 * * *"       # every 6 hours
  workflow_dispatch:             # manual trigger from Actions tab

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install feedparser beautifulsoup4 sumy python-slugify jinja2 nltk

      - name: Download NLTK data (required by sumy)
        run: |
          python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

      - name: Build static site
        run: |
          python scripts/build.py
          test -f site/index.html   # fail fast if build didn't produce index

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: site
          publish_branch: gh-pages
          user_name: "github-actions[bot]"
          user_email: "41898282+github-actions[bot]@users.noreply.github.com"
          force_orphan: true        # keeps gh-pages branch clean on every deploy
