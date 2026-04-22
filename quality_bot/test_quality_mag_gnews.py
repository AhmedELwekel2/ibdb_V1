import feedparser
import requests

def test_quality_mag_gnews():
    url = "https://news.google.com/rss/search?q=site:qualitymag.com"
    print(f"Testing Google News RSS feed: {url}")
    
    try:
        feed = feedparser.parse(url)
        print(f"Entries found: {len(feed.entries)}")
        
        if feed.entries:
            for entry in feed.entries[:3]:
                print(f"\nTitle: {entry.title}")
                print(f"Link: {entry.link}")
                print(f"Published: {entry.published}")
        else:
            print("No entries found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_quality_mag_gnews()
