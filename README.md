# reddit-rss

Personal Reddit → RSS pipeline. Runs locally on your Mac via launchd, pushes `feed.xml` to GitHub Pages, read in NetNewsWire. No API auth required.

## What it does

- Fetches hot posts from configured subreddits every 3 hours
- Filters by per-subreddit upvote threshold
- Deduplicates across runs (won't resurface posts you've already seen, capped at 200 IDs)
- Embeds full post body for text posts; external URL for link posts
- Writes a valid RSS 2.0 `feed.xml` pushed to GitHub Pages
- Runs silently in the background — no terminal interaction needed

---

## Architecture

```
launchd (Mac scheduler, every 3 hrs)
  → run.sh
    → venv/bin/python fetch_reddit.py
      → Reddit public JSON API (no auth)
      → writes feed.xml + seen.json
    → git commit + push
GitHub Pages serves feed.xml at stable URL
NetNewsWire polls that URL
```

**Why local and not GitHub Actions?** Reddit blocks GitHub Actions IP ranges with 403 errors. Running locally avoids this entirely.

---

## Repo structure

```
reddit-to-rss/
├── fetch_reddit.py              ← main script
├── run.sh                       ← called by launchd
├── seen.json                    ← dedup state (auto-managed)
├── feed.xml                     ← generated feed (auto-managed)
├── requirements.txt             ← pinned dependencies
├── .gitignore
├── com.martin.reddit-rss.plist  ← launchd config (not committed)
└── venv/                        ← local Python env (not committed)
```

---

## One-time setup

### 1. Clone the repo

```bash
git clone https://github.com/mrmarmac/reddit-to-rss
cd reddit-to-rss
```

### 2. Create the Python environment

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

No need to activate the venv — `run.sh` calls the venv's Python directly by full path.

### 3. Install the launchd scheduler

```bash
bash install.sh
```

This copies `com.martin.reddit-rss.plist` to `~/Library/LaunchAgents/` and loads it. The script runs immediately and every 3 hours after that, on every login. It runs silently in the background — no terminal window appears.

### 4. Enable GitHub Pages

1. Go to the repo on GitHub → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / root (`/`)
4. Save

Your feed URL:
```
https://mrmarmac.github.io/reddit-to-rss/feed.xml
```

### 5. Add to NetNewsWire

1. Open NetNewsWire → **File → New Feed…**
2. Paste the feed URL above
3. Press **Command + R** to force an initial refresh if posts don't appear immediately

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

Then commit and push:

```bash
git add fetch_reddit.py
git commit -m "update subreddits"
git push
```

Takes effect on the next run.

---

## Monitoring

Check the log after any run:
```bash
tail /Users/martin/claude/reddit-to-rss/reddit-rss.log
```

Watch live:
```bash
tail -f /Users/martin/claude/reddit-to-rss/reddit-rss.log
```

---

## Making changes to any file

After editing and saving:
```bash
cd /Users/martin/claude/reddit-to-rss
git add <filename>
git commit -m "describe what you changed"
git push
```

---

## Security notes

- No API keys or secrets anywhere in the repo or code
- Reddit public JSON API requires no auth for public subreddits
- `seen.json` and `feed.xml` are public (GitHub Pages is public on free tier) — they reveal which subreddits you follow and your thresholds
- `venv/` and `.DS_Store` are gitignored and never committed
- `requests` version is pinned in `requirements.txt` to reduce supply chain risk

---

## Troubleshooting

**Feed is empty / no posts fetched**
Check the log for `[WARN] Failed to fetch` lines. If you see 403 errors, Reddit may be temporarily blocking your IP — rare for home connections but possible. Wait and retry.

**NetNewsWire not updating**
Verify the feed is live at the URL in your browser first. Then force refresh in NetNewsWire with **Command + R**.

**Push rejected (fetch first)**
```bash
git fetch origin
git reset --hard origin/main
bash run.sh
```