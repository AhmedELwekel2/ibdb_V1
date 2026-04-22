import requests
from bs4 import BeautifulSoup
import feedparser
import logging

logging.basicConfig(level=logging.INFO)

def test_nist():
    print("Fetching NIST RSS feed...")
    feed_url = "https://www.nist.gov/news-events/news/rss.xml"
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        print("No entries found in NIST RSS feed.")
        return

    print(f"Found {len(feed.entries)} entries.")
    
    # Test first article
    first_entry = feed.entries[0]
    print(f"\nTarget Article: {first_entry.title}")
    url = first_entry.link
    print(f"URL: {url}")
    
    print("Testing extraction...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        content = soup.select_one('.text-with-summary')
        if content:
             text = content.get_text(strip=True)[:500]
             print("\nSuccess! Content Preview:")
             print(text + "...")
             print(f"Total Length: {len(content.get_text(strip=True))}")
        else:
             print("Failed to find .text-with-summary element.")
             
    except Exception as e:
        print(f"Error extracting: {e}")

if __name__ == "__main__":
    test_nist()
