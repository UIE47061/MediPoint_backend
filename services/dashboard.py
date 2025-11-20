from db.mongo import db
from util.gemini import generate_talking_point
from datetime import datetime

# 固定查詢日期 (Demo 用，為了配合 CSV 的資料時間點)
TARGET_DATE = "2025-10-30"
STORE_ID = "S001"

def get_weekly_dashboard_data():
    """
    處理 Dashboard 所有的資料獲取與計算邏輯
    """
    
    # ==========================================
    # 1. 計算 KPI (從 daily_category_summary 撈取)
    # ==========================================
    pipeline_kpi = [
        {"$match": {"date": TARGET_DATE, "store_id": STORE_ID}},
        {"$group": {
            "_id": None,
            "total_revenue": {"$sum": "$revenue"},
            "total_gp": {"$sum": "$gross_profit"}
        }}
    ]
    
    kpi_result = list(db.daily_category_summary.aggregate(pipeline_kpi))
    
    if kpi_result:
        revenue = kpi_result[0]['total_revenue']
        gp = kpi_result[0]['total_gp']
        # 防止除以零
        margin = round((gp / revenue) * 100, 1) if revenue > 0 else 0
    else:
        # Fallback (若資料庫尚未寫入該日期數據，提供預設值以免畫面壞掉)
        revenue = 42296
        gp = 4148
        margin = 9.8

    kpi_data = {
        "coverage_label": "熱門商品覆蓋率",
        "coverage_value": "85%",
        "coverage_trend": "較上週 +5%",
        "coverage_progress": 85,
        "gross_profit": f"{int(gp):,}",
        "margin_rate": f"{margin}%",
        "margin_status": "low" if margin < 15 else "high", # 邏輯判斷：低於 15% 視為低毛利
        "top_category": "保健藥品"
    }

    # ==========================================
    # 2. 取得法規警示 (從 alerts collection 撈取真實資料)
    # ==========================================
    # 抓最新的 5 筆，按爬取時間倒序
    alert_cursor = db.alerts.find().sort("crawled_at", -1).limit(5)
    alerts = []
    
    for a in alert_cursor:
        alerts.append({
            "agency": a.get("agency", "CDC"),
            "type": a.get("type", "公告"),
            "title": a.get("title", "無標題"),
            "risk_level": a.get("risk_level", "Medium")
        })
        
    # 如果 DB 裡面是空的 (還沒跑過爬蟲)，就放一個預設的給 Demo 用
    if not alerts:
        alerts = [
            {"agency": "CDC", "type": "系統提示", "title": "尚無最新疫情警示資料，請至後端執行爬蟲更新。", "risk_level": "Low"},
            {"agency": "TFDA", "type": "範例", "title": "特定批號胃藥因包裝瑕疵啟動二級回收 (範例)", "risk_level": "Medium"}
        ]

    # ==========================================
    # 3. 產生智慧備貨建議 (Inventory + Gemini AI)
    # ==========================================
    # 邏輯：找出庫存 < 30 的商品做補貨建議
    low_stock_cursor = db.inventory.find({
        "date": TARGET_DATE, 
        "store_id": STORE_ID,
        "closing_on_hand": {"$lt": 30}
    }).limit(2)

    # 邏輯：找出庫存 > 100 的商品做促銷建議
    high_stock_cursor = db.inventory.find({
        "date": TARGET_DATE, 
        "store_id": STORE_ID,
        "closing_on_hand": {"$gt": 100}
    }).limit(1)
    
    suggestions = []

    # 3.1 補貨建議 (Restock)
    restock_items = []
    for item in low_stock_cursor:
        # 簡單的名稱映射，讓 Demo 更好看 (因為 CSV 只給了 SKU ID)
        sku_name = f"熱銷藥品 ({item['sku_id'][-3:]})"
        if "保健" in item['sku_id']: sku_name = f"綜合感冒藥 ({item['sku_id'][-3:]})"
        if "婦嬰" in item['sku_id']: sku_name = f"兒童退燒水 ({item['sku_id'][-3:]})"

        restock_items.append({
            "sku_id": item["sku_id"],
            "name": sku_name,
            "stock": item["closing_on_hand"],
            "margin": 34.1, # 這裡可再優化：去 sales collection 算真實毛利
            "sales_7d": 14,
            "status": "Critical"
        })
    
    if restock_items:
        # 呼叫 Gemini 生成話術
        ai_talk = generate_talking_point("流感高峰", [x['name'] for x in restock_items], "庫存告急")
        
        suggestions.append({
            "topic": "流感與呼吸道感染高峰",
            "action": "Restock",
            "related_category": "感冒/退燒",
            "reason": "輿情熱度上升 150%，且店內庫存低於安全水位。",
            "items": restock_items,
            "talking_points": ai_talk
        })

    # 3.2 促銷建議 (Promotion)
    promo_items = []
    for item in high_stock_cursor:
         promo_items.append({
            "sku_id": item["sku_id"],
            "name": f"維他命/噴劑 ({item['sku_id'][-3:]})",
            "stock": item["closing_on_hand"],
            "margin": 36.0,
            "sales_7d": 5,
            "status": "Safe"
        })

    if promo_items:
        suggestions.append({
            "topic": "換季過敏潮",
            "action": "Promotion",
            "related_category": "鼻噴劑/維他命",
            "reason": "網路討論增加，但店內庫存過高，建議做促銷去化。",
            "items": promo_items,
            "talking_points": "雖然現在有人問，但庫存偏高。建議搭配維他命 C 做「換季防護組」促銷。"
        })

    # ==========================================
    # 4. 輿情 (從 DB 撈取真實爬蟲資料)
    # ==========================================
    latest_articles = list(db.raw_articles.find().sort("crawled_at", -1).limit(5))
    insights = []
    
    if latest_articles:
        for art in latest_articles:
            # 簡單的規則判斷 tag，未來可用 AI 分析內容
            tags = ["熱議"]
            title = art.get("title", "")
            
            if "感冒" in title or "流感" in title: tags.append("流感")
            if "缺" in title: tags.append("缺貨")
            if "藥" in title: tags.append("用藥諮詢")
            if "寶寶" in title or "小孩" in title: tags.append("兒童")
            
            insights.append({
                "source": art.get("source", "Internet"),
                "board": art.get("board", "General"),
                "title": title,
                "content": art.get("content", "")[:60] + "...", # 只取摘要
                "intent": "Ask" if "?" in title else "Complain",
                "tags": tags
            })
    else:
        # 若沒資料顯示預設
        insights = [
            {"source": "PTT", "board": "BabyMother", "title": "(範例) 小孩半夜發燒買不到藥怎麼辦？", "content": "跑了兩家藥局都說退燒藥缺貨...", "intent": "Out_of_Stock", "tags": ["缺貨", "兒童"]},
            {"source": "Dcard", "board": "Health", "title": "(範例) 最近流感是不是很強？", "content": "吞口水像刀割一樣...", "intent": "Ask", "tags": ["流感", "推薦"]}
        ]

    return {
        "report_date": TARGET_DATE,
        "kpiData": kpi_data,
        "alerts": alerts,
        "suggestions": suggestions,
        "insights": insights
    }