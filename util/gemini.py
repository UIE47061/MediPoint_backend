# util/gemini.py
import json
from typing import Dict, Any

import google.generativeai as genai

from util.config import env  # 你之前寫好的 Env 類別


# 初始化 Gemini
if not env.GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in environment")

genai.configure(api_key=env.GEMINI_API_KEY)

# 建議用速度快的模型
MODEL_NAME = "gemini-2.5-flash"


def ai_summary_daily(report: Dict[str, Any]) -> str:
    """
    給 /report/daily 的 JSON，請 Gemini 幫你寫「營運摘要＋建議」。
    回傳一段已排版好的中文文字。
    """
    model = genai.GenerativeModel(MODEL_NAME)

    # 為了避免 prompt 太肥，稍微壓縮只挑重點丟給模型
    slim_report = {
        "meta": report.get("meta", {}),
        "kpi": report.get("kpi", {}),
        "top_products": report.get("top_products", [])[:10],
        "top_categories": report.get("top_categories", [])[:10],
        "low_stock": report.get("low_stock", [])[:20],
        "spike_products": report.get("spike_products", [])[:20],
    }

    prompt = f"""
你是一位連鎖藥局的營運分析師，請閱讀下面的 JSON 報表，寫出「給門市店長看」的一頁式簡短摘要。

請用繁體中文，口吻專業但不要太學術。

輸出格式請大致如下（不用顯示標題編號）：
1. 一句話總結今天表現（例如：整體銷售較過去 7 天略為成長，主力來自＊＊品類）
2. 列出 3 點以內的「短期動作建議」（每點一行，前面加 -）
   - 優先補貨哪些品項或品類（可以參考 low_stock / spike_products）
   - 若有暴增品項，提醒可能與季節、疫情、新聞事件有關
3. 給門市同仁的標準話術建議（1～2 句），例如：
   - 面對缺貨品項可以怎麼推薦替代商品
   - 面對客人詢問熱賣品項時可以怎麼說

不要解釋 JSON 結構，只要直接講結論與建議。

以下是報表 JSON（已簡化）：
{json.dumps(slim_report, ensure_ascii=False)}
"""

    try:
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        return text if text else "（AI 摘要目前無法產生）"
    except Exception as e:
        # 不讓整個 API 爆掉，只回傳錯誤訊息給前端 debug 用
        return f"AI 摘要產生失敗：{e}"