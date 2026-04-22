import logging
import sys
import os
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure we can import the bot module
sys.path.append(os.getcwd())

try:
    from telegram_bot_quality_arabic import fetch_eos_news, extract_article_content
except ImportError as e:
    print(f"Error importing bot module: {e}")
    sys.exit(1)

def test_eos():
    print("Fetching EOS news...")
    try:
        articles = fetch_eos_news()
        print(f"Found {len(articles)} articles.")
        
        if articles:
            print("\n--- Listing Check ---")
            for i, article in enumerate(articles[:3]):
                print(f"[{i+1}] {article['title']}")
                print(f"    URL: {article['url']}")
                print(f"    Date: {article['publishedAt']}")
            
            # Test full content extraction for the first article
            print("\n--- Full Content Extraction Test ---")
            first_url = articles[0]['url']
            print(f"Extracting content from: {first_url}")
            
            content = extract_article_content(first_url)
            if content:
                print("Success!")
                print(f"Title: {content.get('title')}")
                text = content.get('text', '')
                print(f"Content Length: {len(text)}")
                print(f"Snippet: {text[:200]}...")
            else:
                print("Failed to extract content.")
        else:
            print("No articles found.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_eos()
