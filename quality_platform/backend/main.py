from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import sys

# Ensure project root (.. ) is on sys.path so we can import quality_bot module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", "DUMMY_WEB_API_TOKEN")

from quality_bot.telegram_bot_quality_arabic import (  # type: ignore
    enhance_articles_with_content,
    filter_relevant_articles,
    filter_recent_articles,
    categorize_articles_for_blogs,
    generate_quality_blog_with_ai,
    build_fallback_quality_blog_content,
    create_quality_blog_pdf,
    generate_magazine_content_with_ai,
    render_magazine_pdf,
)

# Imports from current module
from database import engine, get_db, Base
from models import Article, Settings as SettingsModel
from schemas import NewsListResponse, SettingResponse, SettingBase
from scheduler import start_scheduler

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Quality News API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Start the background task to fetch news periodically
    start_scheduler()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "db": "connected"}


def _article_to_dict(a: Article) -> dict:
    """Helper to convert DB article to dict for bot functions"""
    return {
        "title": a.title,
        "description": a.description,
        "url": a.url,
        "publishedAt": a.published_at.isoformat() if a.published_at else None,
        "source": {"name": a.source_name},
        "content": a.content
    }


@app.get("/api/news/daily", response_model=NewsListResponse)
def get_daily_news(db: Session = Depends(get_db)):
    """Return merged daily quality news from Local DB."""
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    
    articles = db.query(Article).filter(
        (Article.published_at >= yesterday) | (Article.created_at >= yesterday),
        Article.is_relevant == True
    ).order_by(Article.published_at.desc().nulls_last(), Article.created_at.desc()).all()
    
    result = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "publishedAt": a.published_at,
            "source": {"name": a.source_name},
            "content": a.content,
            "created_at": a.created_at
        } for a in articles
    ]
    return {"date": today.date().isoformat(), "count": len(result), "articles": result}


@app.get("/api/news/weekly", response_model=NewsListResponse)
def get_weekly_news(db: Session = Depends(get_db)):
    """Return weekly quality news (last 7 days) from Local DB."""
    today = datetime.utcnow()
    last_week = today - timedelta(days=7)
    
    articles = db.query(Article).filter(
        (Article.published_at >= last_week) | (Article.created_at >= last_week),
        Article.is_relevant == True
    ).order_by(Article.published_at.desc().nulls_last(), Article.created_at.desc()).all()
    
    result = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "publishedAt": a.published_at,
            "source": {"name": a.source_name},
            "content": a.content,
            "created_at": a.created_at
        } for a in articles
    ]
    return {"date": today.date().isoformat(), "count": len(result), "articles": result}


@app.get("/api/news/monthly", response_model=NewsListResponse)
def get_monthly_news(db: Session = Depends(get_db)):
    """Return monthly quality news (last 30 days) from Local DB."""
    today = datetime.utcnow()
    last_month = today - timedelta(days=30)
    
    articles = db.query(Article).filter(
        (Article.published_at >= last_month) | (Article.created_at >= last_month),
        Article.is_relevant == True
    ).order_by(Article.published_at.desc().nulls_last(), Article.created_at.desc()).all()
    
    result = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "url": a.url,
            "publishedAt": a.published_at,
            "source": {"name": a.source_name},
            "content": a.content,
            "created_at": a.created_at
        } for a in articles
    ]
    return {"date": today.date().isoformat(), "count": len(result), "articles": result}


@app.get("/api/settings", response_model=list[SettingResponse])
def get_settings(db: Session = Depends(get_db)):
    return db.query(SettingsModel).all()

@app.post("/api/settings", response_model=SettingResponse)
def save_setting(setting: SettingBase, db: Session = Depends(get_db)):
    db_setting = db.query(SettingsModel).filter(SettingsModel.key == setting.key).first()
    if db_setting:
        db_setting.value = setting.value
        db_setting.description = setting.description or db_setting.description
    else:
        db_setting = SettingsModel(**setting.dict())
        db.add(db_setting)
    
    db.commit()
    db.refresh(db_setting)
    return db_setting


# ==========================================
# REPORTS ENDPOINTS
# ==========================================

@app.post("/api/reports/weekly-blog")
def generate_weekly_blog_report(db: Session = Depends(get_db)):
    try:
        today = datetime.utcnow()
        last_week = today - timedelta(days=7)
        db_articles = db.query(Article).filter(
            (Article.published_at >= last_week) | (Article.created_at >= last_week),
            Article.is_relevant == True
        ).all()
        
        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية للأسبوع الماضي لتوليد تقرير.")

        # Re-apply strict filter just in case
        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=7)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة للأسبوع الماضي بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=50, weekly_mode=True)

        categorized = categorize_articles_for_blogs(enhanced)
        management_articles = categorized.get("management", []) or []
        improvement_articles = categorized.get("improvement", []) or []

        if not management_articles and not improvement_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية لتوليد مدونات أسبوعية.")

        management_blog = ""
        improvement_blog = ""
        
        # Determine if we should use custom keywords from settings
        blog_keywords_setting = db.query(SettingsModel).filter(SettingsModel.key == "blog_keywords").first()
        custom_keywords = blog_keywords_setting.value if blog_keywords_setting else None
        
        # We handle this correctly if generate_quality_blog_with_ai supports passing them globally, 
        # but for now we'll stick to the existing signature
        if management_articles:
            management_blog = generate_quality_blog_with_ai(management_articles, "management", "weekly")
            if not management_blog or "AWS Bedrock Error" in management_blog or "حدث خطأ" in management_blog or len(management_blog.strip()) < 200:
                management_blog = build_fallback_quality_blog_content(management_articles, "أنظمة إدارة الجودة والمعايير")

        if improvement_articles:
            improvement_blog = generate_quality_blog_with_ai(improvement_articles, "improvement", "weekly")
            if not improvement_blog or "AWS Bedrock Error" in improvement_blog or "حدث خطأ" in improvement_blog or len(improvement_blog.strip()) < 200:
                improvement_blog = build_fallback_quality_blog_content(improvement_articles, "التحسين المستمر وأطر التميز")

        combined_blog = "\n\n---\n\n".join([b for b in [management_blog, improvement_blog] if b])
        if not combined_blog or len(combined_blog.strip()) < 100:
            combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص أسبوعي")

        title = "التقرير الأسبوعي للجودة والتميز"
        pdf_path = create_quality_blog_pdf(combined_blog, title, is_temp_file=False)
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للتقرير الأسبوعي.")

        filename = f"Quality_Weekly_Report_{today.strftime('%Y%m%d')}.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد التقرير الأسبوعي: {e}"})


@app.post("/api/reports/monthly-blog")
def generate_monthly_blog_report(db: Session = Depends(get_db)):
    try:
        today = datetime.utcnow()
        last_month = today - timedelta(days=30)
        db_articles = db.query(Article).filter(
            (Article.published_at >= last_month) | (Article.created_at >= last_month),
            Article.is_relevant == True
        ).all()
        
        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية للشهر الماضي لتوليد تقرير.")

        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=30)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=80, monthly_mode=True)

        categorized = categorize_articles_for_blogs(enhanced)
        management_articles = categorized.get("management", []) or []
        improvement_articles = categorized.get("improvement", []) or []

        if not management_articles and not improvement_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية لتوليد مدونات شهرية.")

        management_blog = ""
        improvement_blog = ""
        if management_articles:
            management_blog = generate_quality_blog_with_ai(management_articles, "management", "monthly")
            if not management_blog or "AWS Bedrock Error" in management_blog or "حدث خطأ" in management_blog or len(management_blog.strip()) < 200:
                management_blog = build_fallback_quality_blog_content(management_articles, "أنظمة إدارة الجودة والمعايير")

        if improvement_articles:
            improvement_blog = generate_quality_blog_with_ai(improvement_articles, "improvement", "monthly")
            if not improvement_blog or "AWS Bedrock Error" in improvement_blog or "حدث خطأ" in improvement_blog or len(improvement_blog.strip()) < 200:
                improvement_blog = build_fallback_quality_blog_content(improvement_articles, "التحسين المستمر وأطر التميز")

        combined_blog = "\n\n---\n\n".join([b for b in [management_blog, improvement_blog] if b])
        if not combined_blog or len(combined_blog.strip()) < 100:
            combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص شهري")

        title = "التقرير الشهري للجودة والتميز"
        pdf_path = create_quality_blog_pdf(combined_blog, title, is_temp_file=False)
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للتقرير الشهري.")

        filename = f"Quality_Monthly_Report_{today.strftime('%Y%m%d')}.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد التقرير الشهري: {e}"})


@app.post("/api/reports/magazine")
def generate_magazine_report(db: Session = Depends(get_db)):
    """Generate a monthly magazine PDF using AI content + WeasyPrint templates."""
    try:
        today = datetime.utcnow()
        last_month = today - timedelta(days=30)
        db_articles = db.query(Article).filter(
            (Article.published_at >= last_month) | (Article.created_at >= last_month),
            Article.is_relevant == True
        ).all()

        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية للشهر الماضي لتوليد المجلة.")

        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=30)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة للشهر الماضي بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=40, monthly_mode=True)

        # Generate magazine content using AI
        magazine_data = generate_magazine_content_with_ai(enhanced)
        if not magazine_data:
            raise HTTPException(status_code=500, detail="فشل توليد محتوى المجلة بواسطة الذكاء الاصطناعي.")

        # Add date
        magazine_data['date'] = today.strftime("%B %Y")

        # Render PDF
        filename = f"Quality_Magazine_{today.strftime('%Y%m')}.pdf"
        pdf_path = render_magazine_pdf(magazine_data, filename)
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للمجلة.")

        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد المجلة: {e}"})


@app.post("/api/reports/daily-blog")
def generate_daily_blog_report(db: Session = Depends(get_db)):
    try:
        today = datetime.utcnow()
        yesterday = today - timedelta(days=1)
        db_articles = db.query(Article).filter(
            (Article.published_at >= yesterday) | (Article.created_at >= yesterday),
            Article.is_relevant == True
        ).all()
        
        all_articles = [_article_to_dict(a) for a in db_articles]
        if not all_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية اليوم لتوليد تقرير.")

        filtered = filter_relevant_articles(all_articles)
        recent = filter_recent_articles(filtered, days=1)
        if not recent:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات ملائمة لليوم بعد الفلترة.")

        enhanced = enhance_articles_with_content(recent, max_articles=20)

        categorized = categorize_articles_for_blogs(enhanced)
        management_articles = categorized.get("management", []) or []
        improvement_articles = categorized.get("improvement", []) or []

        if not management_articles and not improvement_articles:
            raise HTTPException(status_code=500, detail="لم يتم العثور على مقالات كافية لتوليد مدونة يومية.")

        management_blog = ""
        improvement_blog = ""
        if management_articles:
            management_blog = generate_quality_blog_with_ai(management_articles, "management", "weekly") # daily uses weekly logic in bot
            if not management_blog or "AWS Bedrock Error" in management_blog or "حدث خطأ" in management_blog or len(management_blog.strip()) < 200:
                management_blog = build_fallback_quality_blog_content(management_articles, "أنظمة إدارة الجودة والمعايير")

        if improvement_articles:
            improvement_blog = generate_quality_blog_with_ai(improvement_articles, "improvement", "weekly")
            if not improvement_blog or "AWS Bedrock Error" in improvement_blog or "حدث خطأ" in improvement_blog or len(improvement_blog.strip()) < 200:
                improvement_blog = build_fallback_quality_blog_content(improvement_articles, "التحسين المستمر وأطر التميز")

        combined_blog = "\n\n---\n\n".join([b for b in [management_blog, improvement_blog] if b])
        if not combined_blog or len(combined_blog.strip()) < 100:
            combined_blog = build_fallback_quality_blog_content(enhanced, "ملخص يومي")

        title = "التقرير اليومي للجودة والتميز"
        pdf_path = create_quality_blog_pdf(combined_blog, title, is_temp_file=False)
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=500, detail="تعذر إنشاء ملف PDF للتقرير اليومي.")

        filename = f"Quality_Daily_Report_{today.strftime('%Y%m%d')}.pdf"
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"خطأ غير متوقع أثناء توليد التقرير اليومي: {e}"})
