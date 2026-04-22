import feedparser
import requests

def test_quality_mag():
    url = "https://www.qualitymag.com/rss/articles"
    print(f"Testing RSS feed: {url}")
    
    # Newer Chrome UA
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        print("Fetching with requests + newer headers...")
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            feed = feedparser.parse(response.content)
            print(f"Entries found: {len(feed.entries)}")
        else:
            print(f"Failed to fetch: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_quality_mag()
