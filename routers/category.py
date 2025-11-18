# routers/category.py
from fastapi import APIRouter
from typing import Optional
from db.mongo import db

router = APIRouter(prefix="/category", tags=["category"])

@router.get("/")
def get_category(category: Optional[str] = None, limit: int = 200):
    """
    取得品類趨勢資料：
    - 若有傳 category，就只回傳該品類
    - 否則回傳全部（限制筆數）
    """
    query = {}
    if category:
        query["category"] = category

    data = list(
        db.category.find(query).sort("date", -1).limit(limit)
    )
    for d in data:
        d["_id"] = str(d["_id"])
    return data


@router.get("/by-date")
def get_category_by_date(date: str):
    """
    依日期查詢該日各品類資料
    """
    data = list(db.category.find({"date": date}))
    for d in data:
        d["_id"] = str(d["_id"])
    return data