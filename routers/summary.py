# routers/summary.py
from fastapi import APIRouter
from db.mongo import db

router = APIRouter(prefix="/summary", tags=["summary"])

@router.get("/")
def get_summary(limit: int = 31):
    """
    取得最近 N 筆每日總結資料（預設 31 天）
    """
    data = list(
        db.summary.find().sort("date", -1).limit(limit)
    )
    for d in data:
        d["_id"] = str(d["_id"])
    return data


@router.get("/by-date")
def get_summary_by_date(date: str):
    """
    依日期查詢每日總結資料
    date 格式依你的 CSV 欄位，例如 '2025-10-01'
    """
    data = list(db.summary.find({"date": date}))
    for d in data:
        d["_id"] = str(d["_id"])
    return data