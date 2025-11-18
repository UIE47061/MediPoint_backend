# routers/analytics.py
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from db.mongo import db

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ======== 這邊的欄位名稱請你依照實際 Mongo 欄位調整 ========
DATE_FIELD = "date"          # 銷售日期欄位，例如 "2025-10-01"
STORE_FIELD = "store_id"
SKU_FIELD = "sku_id"
QTY_FIELD = "qty"            # 銷售數量
AMOUNT_FIELD = "amount"      # 銷售金額
CATEGORY_FIELD = "category"  # 商品分類
NAME_FIELD = "name"          # 商品名稱，如果有

# inventory 欄位
STOCK_FIELD = "stock_on_hand"
SALES_7D_FIELD = "sales_7d"
# ============================================================


def _date_str_to_range(date_str: str):
    """把 YYYY-MM-DD 字串轉成當天的 datetime range（含頭含尾）"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    start = datetime(d.year, d.month, d.day, 0, 0, 0)
    end = start + timedelta(days=1)
    return start, end


@router.get("/kpi/daily")
def kpi_daily(date: str = Query(..., description="YYYY-MM-DD"),
              store_id: Optional[str] = None):
    """
    某天的 KPI：
    - total_sales_amount
    - total_orders
    - total_items
    - top_category
    - top_sku
    """

    # 這裡假設 sales[DATE_FIELD] 是 datetime，如果是純字串就改用 "$match": {DATE_FIELD: date}
    start, end = _date_str_to_range(date)
    match_stage: Dict[str, Any] = {
        DATE_FIELD: {"$gte": start, "$lt": end}
    }
    if store_id:
        match_stage[STORE_FIELD] = store_id

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": None,
                "total_sales_amount": {"$sum": f"${AMOUNT_FIELD}"},
                "total_orders": {"$addToSet": "$order_id"},  # 如果有 order_id
                "total_items": {"$sum": f"${QTY_FIELD}"}
            }
        }
    ]

    agg = list(db.sales.aggregate(pipeline))
    if agg:
        doc = agg[0]
        total_orders = len(doc.get("total_orders", []))
        kpi = {
            "date": date,
            "store_id": store_id,
            "total_sales_amount": doc.get("total_sales_amount", 0),
            "total_orders": total_orders,
            "total_items": doc.get("total_items", 0),
        }
    else:
        kpi = {
            "date": date,
            "store_id": store_id,
            "total_sales_amount": 0,
            "total_orders": 0,
            "total_items": 0,
        }

    # top category
    pipeline_cat = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": f"${CATEGORY_FIELD}",
                "amount": {"$sum": f"${AMOUNT_FIELD}"}
            }
        },
        {"$sort": {"amount": -1}},
        {"$limit": 1},
    ]
    cat = list(db.sales.aggregate(pipeline_cat))
    kpi["top_category"] = cat[0]["_id"] if cat else None

    # top sku
    pipeline_sku = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": {
                    "sku_id": f"${SKU_FIELD}",
                    "name": f"${NAME_FIELD}",
                },
                "amount": {"$sum": f"${AMOUNT_FIELD}"},
                "qty": {"$sum": f"${QTY_FIELD}"},
            }
        },
        {"$sort": {"amount": -1}},
        {"$limit": 1},
    ]
    sku = list(db.sales.aggregate(pipeline_sku))
    if sku:
        top = sku[0]
        kpi["top_sku"] = {
            "sku_id": top["_id"].get("sku_id"),
            "name": top["_id"].get("name"),
            "amount": top["amount"],
            "qty": top["qty"],
        }
    else:
        kpi["top_sku"] = None

    return kpi


@router.get("/top-products")
def top_products(
    date: str = Query(..., description="YYYY-MM-DD"),
    store_id: Optional[str] = None,
    limit: int = 10,
):
    """某天暢銷商品排行"""
    start, end = _date_str_to_range(date)
    match_stage: Dict[str, Any] = {
        DATE_FIELD: {"$gte": start, "$lt": end}
    }
    if store_id:
        match_stage[STORE_FIELD] = store_id

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": {
                    "sku_id": f"${SKU_FIELD}",
                    "name": f"${NAME_FIELD}",
                    "category": f"${CATEGORY_FIELD}",
                },
                "amount": {"$sum": f"${AMOUNT_FIELD}"},
                "qty": {"$sum": f"${QTY_FIELD}"},
            }
        },
        {"$sort": {"amount": -1}},
        {"$limit": limit},
    ]

    results = []
    for i, doc in enumerate(db.sales.aggregate(pipeline), start=1):
        _id = doc["_id"]
        results.append({
            "rank": i,
            "sku_id": _id.get("sku_id"),
            "name": _id.get("name"),
            "category": _id.get("category"),
            "amount": doc.get("amount", 0),
            "qty": doc.get("qty", 0),
        })
    return results


@router.get("/top-categories")
def top_categories(
    date: str = Query(..., description="YYYY-MM-DD"),
    limit: int = 10,
):
    """某天各品類銷售排行"""
    start, end = _date_str_to_range(date)
    match_stage = {
        DATE_FIELD: {"$gte": start, "$lt": end}
    }

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": f"${CATEGORY_FIELD}",
                "amount": {"$sum": f"${AMOUNT_FIELD}"},
                "qty": {"$sum": f"${QTY_FIELD}"},
            }
        },
        {"$sort": {"amount": -1}},
        {"$limit": limit},
    ]
    results = []
    for i, doc in enumerate(db.sales.aggregate(pipeline), start=1):
        results.append({
            "rank": i,
            "category": doc["_id"],
            "amount": doc.get("amount", 0),
            "qty": doc.get("qty", 0),
        })
    return results


@router.get("/low-stock")
def low_stock(
    store_id: Optional[str] = None,
    threshold: int = 10,
    limit: int = 50,
):
    """
    快缺貨清單：
    - stock_on_hand < threshold
    - 估算 days_left = stock_on_hand / (sales_7d / 7)
    """
    query: Dict[str, Any] = {STOCK_FIELD: {"$lt": threshold}}
    if store_id:
        query[STORE_FIELD] = store_id

    cursor = db.inventory.find(query).limit(limit)

    results = []
    for doc in cursor:
        stock = doc.get(STOCK_FIELD, 0) or 0
        sales_7d = doc.get(SALES_7D_FIELD, 0) or 0
        daily = sales_7d / 7 if sales_7d else None
        if daily and daily > 0:
            days_left = round(stock / daily, 1)
        else:
            days_left = None

        results.append({
            "store_id": doc.get(STORE_FIELD),
            "sku_id": doc.get(SKU_FIELD),
            "name": doc.get(NAME_FIELD),
            "category": doc.get(CATEGORY_FIELD),
            "stock_on_hand": stock,
            "sales_7d": sales_7d,
            "days_left": days_left,
        })

    return results


@router.get("/spike-products")
def spike_products(
    date: str = Query(..., description="YYYY-MM-DD"),
    store_id: Optional[str] = None,
    ratio: float = 2.0,
    limit: int = 20,
):
    """
    找出今天比前 7 天平均暴增的品項：
    today_qty >= ratio * avg_7d_qty
    """
    target_day = datetime.strptime(date, "%Y-%m-%d")
    start_today, end_today = _date_str_to_range(date)

    # 前 7 天範圍
    start_7d = start_today - timedelta(days=7)

    base_match: Dict[str, Any] = {}
    if store_id:
        base_match[STORE_FIELD] = store_id

    # 前 7 天 aggregate
    match_7d = base_match.copy()
    match_7d[DATE_FIELD] = {"$gte": start_7d, "$lt": start_today}
    pipeline_7d = [
        {"$match": match_7d},
        {
            "$group": {
                "_id": {
                    "sku_id": f"${SKU_FIELD}",
                    "name": f"${NAME_FIELD}",
                    "category": f"${CATEGORY_FIELD}",
                },
                "qty_7d": {"$sum": f"${QTY_FIELD}"},
            }
        },
    ]
    avg_map: Dict[str, Dict[str, Any]] = {}
    for doc in db.sales.aggregate(pipeline_7d):
        _id = doc["_id"]
        sku = _id.get("sku_id")
        qty_7d = doc.get("qty_7d", 0)
        avg_map[sku] = {
            "name": _id.get("name"),
            "category": _id.get("category"),
            "avg_daily": qty_7d / 7 if qty_7d else 0,
        }

    # 今天的量
    match_today = base_match.copy()
    match_today[DATE_FIELD] = {"$gte": start_today, "$lt": end_today}
    pipeline_today = [
        {"$match": match_today},
        {
            "$group": {
                "_id": {
                    "sku_id": f"${SKU_FIELD}",
                    "name": f"${NAME_FIELD}",
                    "category": f"${CATEGORY_FIELD}",
                },
                "qty_today": {"$sum": f"${QTY_FIELD}"},
            }
        },
    ]
    spikes = []
    for doc in db.sales.aggregate(pipeline_today):
        _id = doc["_id"]
        sku = _id.get("sku_id")
        today_qty = doc.get("qty_today", 0)
        base = avg_map.get(sku)
        if not base:
            continue
        avg_daily = base["avg_daily"]
        if avg_daily > 0 and today_qty >= ratio * avg_daily:
            spikes.append({
                "sku_id": sku,
                "name": _id.get("name"),
                "category": _id.get("category"),
                "qty_today": today_qty,
                "avg_7d_daily": round(avg_daily, 2),
                "ratio": round(today_qty / avg_daily, 2),
            })

    # 排序後取前 limit
    spikes.sort(key=lambda x: x["ratio"], reverse=True)
    return spikes[:limit]