#!/usr/bin/env python3
"""
Reddit → RSS feed generator.
Fetches hot posts from configured subreddits, filters by upvote threshold,
deduplicates across runs, and writes a valid RSS 2.0 feed.xml.
"""

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import formatdate
import requests

# ── Configuration ────────────────────────────────────────────────────────────

SUBREDDITS = {
    "slatestarcodex": 25,
    "newAIparadigms":  20,
    "narcolepsy":      20,
    "localllama":     200,
    "claudeAI":       200,
    "bestof":         200,
    "auslaw":          20,
    "agentsofai":      50,
    "AI_agents":       50,
}

POSTS_PER_SUB   = 50        # how many posts to fetch per subreddit (max 100)
SEEN_CAP        = 200       # max IDs to retain in seen.json
FEED_TITLE      = "Reddit Curated Feed"
FEED_DESCRIPTION = "High-signal posts from selected subreddits."
FEED_LINK       = "https://reddit.com"
OUTPUT_FEED     = "feed.xml"
SEEN_FILE       = "seen.json"

HEADERS = {"User-Agent": "reddit-rss-filter/1.0 (personal feed generator)"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen() -> list:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return []


def save_seen(seen: list) -> None:
    # Keep only the most recent SEEN_CAP IDs
    trimmed = seen[-SEEN_CAP:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f)


def fetch_posts(subreddit: str, limit: int) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        children = r.json()["data"]["children"]
        return [c["data"] for c in children]
    except Exception as e:
        print(f"  [WARN] Failed to fetch r/{subreddit}: {e}")
        return []


def build_description(post: dict) -> str:
    """Return clean description: selftext for text posts, else a label."""
    selftext = (post.get("selftext") or "").strip()
    url      = post.get("url", "")
    sub      = post.get("subreddit_name_prefixed", "")
    score    = post.get("score", 0)
    comments = post.get("num_comments", 0)
    thread   = f"https://www.reddit.com{post.get('permalink', '')}"

    meta = f"↑{score}  💬{comments}  {sub}"

    if selftext and selftext != "[removed]" and selftext != "[deleted]":
        # Self post with body text
        body = selftext[:2000] + ("…" if len(selftext) > 2000 else "")
        return f"{meta}\n\n{body}\n\n{thread}"
    elif post.get("is_self"):
        # Self post with no body (e.g. link-only self post)
        return f"{meta}\n\n{thread}"
    else:
        # Link post — surface the external URL prominently
        return f"{meta}\n\n{url}\n\n{thread}"


def rfc2822(timestamp: float) -> str:
    return formatdate(timestamp, usegmt=True)


def build_feed(items: list) -> str:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text       = FEED_TITLE
    ET.SubElement(channel, "link").text        = FEED_LINK
    ET.SubElement(channel, "description").text = FEED_DESCRIPTION
    ET.SubElement(channel, "language").text    = "en"
    ET.SubElement(channel, "lastBuildDate").text = formatdate(usegmt=True)

    for post in items:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text       = post["title"]
        ET.SubElement(item, "link").text        = (
            f"https://www.reddit.com{post['permalink']}"
        )
        ET.SubElement(item, "guid", isPermaLink="false").text = post["id"]
        ET.SubElement(item, "pubDate").text     = rfc2822(post["created_utc"])
        ET.SubElement(item, "description").text = build_description(post)
        ET.SubElement(item, "category").text    = post.get("subreddit", "")

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    return ET.tostring(rss, encoding="unicode", xml_declaration=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seen     = load_seen()
    seen_set = set(seen)
    new_posts = []
    new_ids   = []

    for subreddit, threshold in SUBREDDITS.items():
        print(f"Fetching r/{subreddit} (threshold ↑{threshold})…")
        posts = fetch_posts(subreddit, POSTS_PER_SUB)
        accepted = 0
        for post in posts:
            pid = post["id"]
            if pid in seen_set:
                continue
            if post.get("score", 0) < threshold:
                continue
            if post.get("stickied"):
                continue
            new_posts.append(post)
            new_ids.append(pid)
            seen_set.add(pid)
            accepted += 1
        print(f"  → {accepted} new posts above threshold")

    # Sort newest first
    new_posts.sort(key=lambda p: p["created_utc"], reverse=True)

    print(f"\nTotal new posts: {len(new_posts)}")
    feed_xml = build_feed(new_posts)

    with open(OUTPUT_FEED, "w", encoding="utf-8") as f:
        f.write(feed_xml)
    print(f"Written: {OUTPUT_FEED}")

    save_seen(seen + new_ids)
    print(f"Updated: {SEEN_FILE} ({min(len(seen) + len(new_ids), SEEN_CAP)} IDs retained)")


if __name__ == "__main__":
    main()
