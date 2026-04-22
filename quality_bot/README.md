# Quality & Excellence Telegram Bot - Refactored Structure

A modular Telegram bot for Quality Management and Excellence news, with AI-powered blog generation in Arabic.

## 📁 Project Structure

```
quality_bot/
├── config.py              # Configuration and constants
├── usage_manager.py        # User usage tracking
├── data_fetcher.py        # Data fetching from various sources
├── content_extractor.py    # Content extraction from URLs
├── article_processor.py   # Article filtering and categorization
├── ai_generator.py        # AI blog generation (Claude via AWS Bedrock)
├── pdf_generator.py       # PDF generation with Arabic support
├── telegram_handlers.py   # Telegram bot command/message handlers
├── main.py               # Main entry point
├── Amiri-Regular.ttf     # Arabic font for PDF generation
├── requirements.txt      # Python dependencies
└── user_usage.json       # Usage tracking data (auto-generated)
```

## 🚀 Features

### News Sources
- **NewsAPI** - Quality and excellence news
- **GNews** - Alternative news source
- **RSS Feeds**:
  - Harvard Business Review (HBR)
  - Forbes Leadership
  - ATD (Association for Talent Development)
  - Training Industry
  - Josh Bersin
- **Custom Scrapers**:
  - EOS Egypt (Egyptian Organization for Standardization)
  - EGAC (Egyptian Accreditation Council)

### Bot Commands
- `/start` - Start the bot and see welcome message
- `/help` - Display help and usage information
- `/daily` - Get daily quality news
- `/weekly` - Get weekly summary (categorized)
- `/monthly` - Get monthly comprehensive report
- `/magazine` - Generate PDF magazine with AI content
- `/usage` - Check your current usage limits
- `/keywords` - Set SEO keywords for AI generation
- `/reset` - Reset all user usage (admin only)

### AI Features
- **Blog Generation** - Uses Claude AI (AWS Bedrock) to generate Arabic blog posts
- **SEO Optimization** - Keyword-based content generation with LSI keywords
- **PDF Creation** - Beautiful PDF magazines with Arabic font support
- **Content Enhancement** - Extracts full article content using multiple methods

## 📦 Installation

### Prerequisites
- Python 3.8+
- Telegram Bot Token from @BotFather
- NewsAPI Key
- GNews API Key
- AWS Bedrock credentials (AWS_BEARER_TOKEN_BEDROCK)

### Setup

1. **Clone or navigate to the directory:**
```bash
cd quality_bot
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**

Create a `.env` file in the `quality_bot` directory:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
NEWSAPI_KEY=your_newsapi_key
GNEWS_API_KEY=your_gnews_api_key
AWS_BEARER_TOKEN_BEDROCK=your_aws_bearer_token
AWS_REGION=us-east-1
AWS_BEDROCK_INFERENCE_PROFILE=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

4. **Ensure Arabic font is present:**
Make sure `Amiri-Regular.ttf` is in the `quality_bot` directory.

## 🏃 Running the Bot

### Start the bot:
```bash
python main.py
```

The bot will start polling and respond to commands on Telegram.

## 🔧 Configuration

### Usage Limits
Edit `USAGE_LIMITS` in `config.py`:
```python
USAGE_LIMITS = {
    'daily_news': 30,
    'weekly': 4,
    'monthly': 2,
    'magazine': 2
}
```

### Admin Users
Add your Telegram user ID to `ADMIN_USER_IDS` in `config.py`:
```python
ADMIN_USER_IDS = [1029062753]  # Add your user IDs
```

### RSS Feeds
Modify `RSS_FEEDS` in `config.py` to add or remove sources:
```python
RSS_FEEDS = [
    {"name": "Source Name", "url": "https://example.com/feed/"}
]
```

## 📖 Module Documentation

### config.py
- Stores all configuration constants
- API keys and tokens
- RSS feed URLs
- Usage limits and admin IDs

### usage_manager.py
- Tracks user usage per feature
- Enforces usage limits
- Provides usage statistics
- Admin reset functionality

### data_fetcher.py
- Fetches articles from NewsAPI, GNews, RSS feeds
- Custom scrapers for EOS and EGAC
- Quality filtering for all sources
- Date normalization

### content_extractor.py
- Extracts full article content from URLs
- Multiple extraction methods:
  - newspaper3k (primary)
  - BeautifulSoup (fallback)
  - Custom handlers for specific sites (NIST, EOS, EGAC)
- Retry logic with exponential backoff

### article_processor.py
- Filters articles by keywords
- Filters articles by date range
- Categorizes articles into quality topics:
  - Quality Management Systems
  - ISO Standards & Certification
  - Excellence Frameworks & Awards
  - Process Improvement & Lean
  - Quality Assurance & Control

### ai_generator.py
- AWS Bedrock Claude API integration
- Keyword parsing and formatting
- SEO instruction building
- Blog content generation in Arabic
- Long timeout support for magazine generation

### pdf_generator.py
- PDF generation with ReportLab
- Arabic text reshaping and bidirectional support
- Custom Amiri font registration
- Markdown to PDF conversion
- Beautiful styling and formatting

### telegram_handlers.py
- All Telegram command handlers
- Message handlers for keyword input
- Callback query handlers for inline keyboards
- Usage limit checking
- Response formatting

### main.py
- Bot initialization
- Handler registration
- Polling setup

## 🔑 Keyword Format

When using `/keywords`, use this format:
```
Primary Keyword | secondary keyword 1, secondary keyword 2, secondary keyword 3
```

Example:
```
Quality Management Excellence 2025 | continuous improvement, ISO certification, six sigma
```

## 🛠️ Development

### Adding New Commands
1. Create handler function in `telegram_handlers.py`
2. Add to `get_handlers()` function
3. Update help messages

### Adding New Data Sources
1. Add fetch function to `data_fetcher.py`
2. Import and use in command handlers
3. Add to appropriate aggregations

### Modifying Categorization
Edit categories and keywords in `article_processor.py`:
```python
categories = {
    'Category Name': [],
    # Add more categories
}

keywords = ['keyword1', 'keyword2']
```

## 📝 Notes

- The bot follows the same architectural pattern as the original monolithic file
- Each module has a single responsibility
- Logging is configured throughout for debugging
- Arabic text handling requires proper reshaping and bidi support
- PDF generation uses the Amiri font for beautiful Arabic typography

## 🐛 Troubleshooting

### Bot not responding
- Check TELEGRAM_TOKEN is correct
- Ensure dependencies are installed
- Check logs for errors

### PDF generation fails
- Verify Amiri-Regular.ttf is present
- Check font registration logs
- Ensure arabic_reshaper and bidi are installed

### AWS Bedrock errors
- Verify AWS_BEARER_TOKEN_BEDROCK is set
- Check AWS credentials and region
- Ensure inference profile ID is correct

### No articles found
- Check API keys are valid
- Verify RSS feeds are accessible
- Check filter keywords in `article_processor.py`

## 📄 License

This project is proprietary and confidential.

## 🤝 Support

For issues or questions, contact the development team.