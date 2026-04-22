"""
AI blog generation using Azure Claude API
"""
import logging
import os

logger = logging.getLogger(__name__)

# Try to import Azure AI client, fallback to AWS if not available
try:
    from azure_ai import call_claude_api as azure_call_claude_api
    USE_AZURE = True
    logger.info("✅ Using Azure AI for Claude API")
except ImportError:
    logger.warning("⚠️ Azure AI client not available, checking for AWS fallback...")
    try:
        import boto3
        from botocore.config import Config
        from config import AWS_BEARER_TOKEN_BEDROCK, AWS_REGION, AWS_BEDROCK_INFERENCE_PROFILE
        
        if not AWS_BEARER_TOKEN_BEDROCK:
            logger.warning("⚠️ AWS_BEARER_TOKEN_BEDROCK environment variable is not set!")
            raise ValueError("No AI provider configured!")
        
        bedrock_client = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION
        )
        
        bedrock_config_long = Config(
            read_timeout=600,
            connect_timeout=10,
            retries={'max_attempts': 1}
        )
        bedrock_client_long = boto3.client(
            service_name="bedrock-runtime",
            region_name=AWS_REGION,
            config=bedrock_config_long
        )
        
        USE_AZURE = False
        logger.info(f"✅ Using AWS Bedrock as fallback")
        logger.info(f"   Region: {AWS_REGION}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize any AI provider: {str(e)}")
        raise


def call_claude_api(system_message, user_message, api_key=None, model=None, 
                   max_tokens=16384, temperature=0.7, use_cache=True, 
                   use_long_timeout=False):
    """
    Call Claude API via Azure or AWS Bedrock
    
    Args:
        system_message: System prompt for Claude
        user_message: User message/prompt
        api_key: Not used (kept for compatibility)
        model: Model ID (optional)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        use_cache: Whether to use caching (placeholder for future implementation)
        use_long_timeout: Use long timeout client for magazine generation
    
    Returns:
        str: Claude's response or None if failed
    """
    try:
        # Use Azure if available
        if USE_AZURE:
            return azure_call_claude_api(
                system_message=system_message,
                user_message=user_message,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                use_cache=use_cache
            )
        
        # Fallback to AWS Bedrock
        client = bedrock_client_long if use_long_timeout else bedrock_client
        model_id = model or AWS_BEDROCK_INFERENCE_PROFILE
        
        # Prepare the request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_message,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }
        
        # Make the API call
        response = client.invoke_model(
            modelId=model_id,
            body=request_body
        )
        
        # Parse the response
        response_body = response['body'].read().decode('utf-8')
        import json
        response_data = json.loads(response_body)
        
        # Extract the content
        if 'content' in response_data and len(response_data['content']) > 0:
            return response_data['content'][0]['text']
        else:
            logger.error("No content in Claude response")
            return None
            
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        return None


def parse_keyword_input(raw_text):
    """Parse keyword input in format: Primary | secondary1, secondary2, secondary3"""
    if not raw_text:
        return None
    parts = raw_text.split('|', 1)
    primary = parts[0].strip()
    if not primary:
        return None
    secondary = []
    if len(parts) > 1:
        secondary = [kw.strip() for kw in parts[1].split(',') if kw.strip()]
    return {"primary": primary, "secondary": secondary}


def format_secondary_keywords(secondary_list):
    """Format secondary keywords for display"""
    if not secondary_list:
        return "لم يتم تحديد كلمات ثانوية"
    return ", ".join(secondary_list)


def build_keyword_instruction_block(keywords):
    """Build SEO-focused keyword instructions for AI"""
    if keywords and keywords.get("primary"):
        primary = keywords["primary"]
        secondary_text = format_secondary_keywords(keywords.get("secondary", []))
        keyword_header = (
            f'PRIMARY KEYWORD: "{primary}"\n'
            f"SECONDARY KEYWORDS / LSI: {secondary_text}\n"
        )
    else:
        keyword_header = (
            "PRIMARY KEYWORD: Not specified (infer the best fit from the quality and excellence coverage)\n"
            "SECONDARY KEYWORDS / LSI: Use related quality, excellence, and QA terms, synonyms, and supporting subtopics\n"
        )

    return f"""
{keyword_header}
SEO requirements:
- Place the primary keyword in:
  • The SEO Title
  • The H1
  • The first paragraph (within the first 100 words)
  • Naturally 2–3 times every ~300 words throughout the body
- Distribute secondary/LSI keywords across select H2/H3 headings and different paragraphs as thematic synonyms.
- Do NOT repeat the exact same keyword in every heading—use natural variations to avoid keyword stuffing.

Mandatory SEO outputs at the top of the response (before any other sections):
1. SEO Title: < 60 characters, includes the primary keyword and communicates a clear benefit.
2. Meta Description: 120–150 characters summarizing the main value, optionally includes the primary keyword once (only if it reads naturally) plus a light CTA.
3. Recommended Slug: lowercase, hyphen-separated version of the primary keyword (e.g., quality-management-excellence-2025).
4. Headings Structure: Proposed H2/H3 outline derived from the primary + secondary keywords using varied phrasing.

After listing these SEO elements, continue with the requested quality and excellence blog structure while following the keyword guidance above.
""".strip()


def keywords_summary_text(keywords):
    """Generate summary text for keywords"""
    if not keywords or not keywords.get("primary"):
        return "لم يتم إعداد أي كلمات مفتاحية بعد."
    secondary = format_secondary_keywords(keywords.get("secondary", []))
    return f"الكلمة الأساسية: {keywords['primary']}\nالكلمات الثانوية: {secondary}"


def generate_quality_blog_with_ai(articles, blog_theme, time_period="weekly", keywords=None):
    """
    Generate a Quality & Excellence blog post using Claude AI
    
    Args:
        articles: List of articles with content
        blog_theme: Theme for the blog (strategy, excellence, etc.)
        time_period: Time period (daily, weekly, monthly)
        keywords: Optional keyword dict with 'primary' and 'secondary' keys
    
    Returns:
        str: Generated blog content in Arabic Markdown
    """
    try:
        # Prepare article summaries for context
        article_summaries = []
        for i, article in enumerate(articles[:10], 1):  # Limit to top 10 for context
            title = article.get('title', 'Unknown')
            source = article.get('source', {}).get('name', 'Unknown')
            content = article.get('full_content', article.get('description', ''))[:500]
            article_summaries.append(f"{i}. {title} ({source})\n   {content}...\n")
        
        articles_text = "\n\n".join(article_summaries)
        
        # Build keyword instruction block
        keyword_instruction = build_keyword_instruction_block(keywords)
        
        # System prompt
        system_prompt = """You are an expert Quality Management and Excellence content writer specializing in creating high-quality, engaging Arabic blog posts.

Your task is to write a comprehensive, well-structured blog post about Quality Management and Excellence topics based on the provided articles.

REQUIREMENTS:
1. Write entirely in Arabic
2. Use professional, engaging tone
3. Structure with clear headings (H1, H2, H3)
4. Include practical examples and actionable insights
5. Format in Markdown
6. Ensure content is SEO-optimized based on provided keywords
7. Add relevant statistics and data when available
8. Include a compelling introduction and conclusion

The blog should be informative, well-researched, and valuable for quality professionals and organizations seeking excellence."""

        # User prompt
        user_prompt = f"""{keyword_instruction}

Based on the following {len(articles)} articles about Quality Management and Excellence, write a comprehensive blog post.

Time Period: {time_period}
Theme: {blog_theme}

ARTICLES FOR REFERENCE:
{articles_text}

Write a detailed blog post that synthesizes insights from these articles while following the SEO requirements above."""

        # Call Claude API
        logger.info(f"Generating blog with theme: {blog_theme}, time period: {time_period}")
        blog_content = call_claude_api(
            system_message=system_prompt,
            user_message=user_prompt,
            max_tokens=16384,
            temperature=0.7,
            use_long_timeout=True
        )
        
        if blog_content:
            logger.info("✅ Blog generated successfully")
            return blog_content
        else:
            logger.error("❌ Failed to generate blog content")
            return None
            
    except Exception as e:
        logger.error(f"Error generating blog with AI: {str(e)}")
        return None