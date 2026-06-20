import feedparser
import json

feeds = {
    'arxiv_ai': 'https://rss.arxiv.org/rss/cs.AI',
    'mit_ai': 'https://news.mit.edu/rss/topic/artificial-intelligence2'
}

for key, url in feeds.items():
    print(f"Fetching {key} from {url}...")
    d = feedparser.parse(url)
    print(f"Status: {d.get('status')}")
    print(f"Feed Title: {d.feed.get('title')}")
    print(f"Entries count: {len(d.entries)}")
    if d.entries:
        entry = d.entries[0]
        print(f"First Entry Title: {entry.get('title')}")
        print(f"First Entry Link: {entry.get('link')}")
        print(f"First Entry Published: {entry.get('published') or entry.get('updated')}")
        print(f"First Entry Summary Key: {'summary' in entry}, {'description' in entry}")
        print(f"First Entry Keys: {list(entry.keys())}")
    print("-" * 40)
