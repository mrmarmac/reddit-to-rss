# reddit-rss

Serverless Reddit → RSS pipeline. 
Runs on GitHub Actions, served via GitHub Pages. 
No auth, no dependencies beyond `requests`.

## What it does

- Fetches hot posts from configured subreddits every 3 hours
- Filters by per-subreddit upvote threshold
- Deduplicates across runs (won't resurface posts already seen)
- Embeds full post body for text posts; external URL for link posts
- Writes a valid RSS 2.0 `feed.xml` served at your GitHub Pages URL

---

## One-time setup

### 1. Create repo

Create new **public** GitHub repository (e.g. `reddit-to-rss`).  
Clone it locally and add these files:

```
reddit-rss/
├── fetch_reddit.py
├── seen.json          ← create this manually (see below)
└── .github/
    └── workflows/
        └── reddit_rss.yml
```

Create an empty `seen.json`:
```bash
echo "[]" > seen.json
git add . && git commit -m "init" && git push
```

### 2. Enable GitHub Pages

1. Go to **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / root (`/`)
4. Save

Your feed URL will be:
```
https://<your-username>.github.io/<repo-name>/feed.xml
```

### 3. Add to NetNewsWire

1. Open NetNewsWire → **File → New Feed…**
2. Paste your `feed.xml` URL
3. Done

### 4. Trigger first run

Go to **Actions → Update Reddit RSS Feed → Run workflow** to populate the feed immediately without waiting 3 hours.

---

## Changing subreddits or thresholds

Edit the `SUBREDDITS` dict at the top of `fetch_reddit.py`:

```python
SUBREDDITS = {
    "localllama":  200,
    "auslaw":       20,
    # add or remove entries here
}
```

Push the change. It takes effect on the next run.

---

## Notes

- GitHub Actions free tier: 2,000 min/month. If 3 hourly check, this uses ~1 min per run × 8 runs/day × 30 days ≈ 240 min/month. Well within limits.
- Reddit's public JSON API has no hard rate limit for low-frequency personal use, but the script includes a User-Agent header as required.
- `seen.json` is capped at 200 IDs. Posts older than the cap *could* theoretically reappear, but in practice won't for active subreddits.
- GHA scheduled crons can be delayed by up to ~30 min during high-load periods. This is fine for a personal feed.
