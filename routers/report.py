# routers/report.py
from fastapi import APIRouter, Query
from typing import Optional, Any

from datetime import datetime

from db.mongo import db
from routers.analytics import (
    kpi_daily,
    top_products,
    top_categories,
    low_stock,
    spike_products,
)
from util.gemini import ai_summary_daily

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/daily")
def daily_report(
    date: str = Query(..., description="YYYY-MM-DD"),
    store_id: Optional[str] = None,
    with_ai: bool = True,
):
    """
    一頁式商情報表：
    - KPI（總銷售 / 單數 / 件數 / top sku / top category）
    - Top products
    - Top categories
    - Low stock
    - Spike products
    - (選配) AI summary
    """
    # 直接呼叫 analytics 裡的函式
    kpi = kpi_daily(date=date, store_id=store_id)
    tops = top_products(date=date, store_id=store_id, limit=10)
    cats = top_categories(date=date, limit=10)
    low = low_stock(store_id=store_id, threshold=10, limit=50)
    spikes = spike_products(date=date, store_id=store_id, ratio=2.0, limit=20)

    report = {
        "meta": {
            "date": date,
            "store_id": store_id,
            "generated_at": datetime.now().isoformat(),
        },
        "kpi": kpi,
        "top_products": tops,
        "top_categories": cats,
        "low_stock": low,
        "spike_products": spikes,
    }

    if with_ai:
        summary_text = ai_summary_daily(report)
        report["ai_summary"] = summary_text

    return report