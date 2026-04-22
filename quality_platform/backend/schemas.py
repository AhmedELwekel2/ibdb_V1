from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class SourceSchema(BaseModel):
    name: Optional[str] = None

class ArticleBase(BaseModel):
    title: str
    description: Optional[str] = None
    url: str
    publishedAt: Optional[datetime] = None
    source_name: Optional[str] = None
    content: Optional[str] = None

class ArticleResponse(ArticleBase):
    id: int
    created_at: datetime
    source: Optional[SourceSchema] = None

    class Config:
        from_attributes = True

class NewsListResponse(BaseModel):
    date: str
    count: int
    articles: List[ArticleResponse]

class SettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SettingResponse(SettingBase):
    id: int

    class Config:
        from_attributes = True
