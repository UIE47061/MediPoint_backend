import json
from typing import Dict, Any, List
import google.generativeai as genai
from util.config import env


if not env.GEMINI_API_KEY:
    pass
else:
    genai.configure(api_key=env.GEMINI_API_KEY)

MODEL_NAME = "gemini-2.0-flash" # 或使用最新的模型

def generate_talking_point(topic: str, products: List[str], reason: str) -> str:
    """
    專為 Dashboard 生成「藥師銷售話術」。
    topic: 議題 (ex: 流感高峰)
    products: 相關藥品名稱列表
    reason: 系統判斷的原因 (ex: 庫存告急)
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = f"""
        你是一位資深藥局店長。
        情況：{topic}
        相關商品：{', '.join(products)}
        系統偵測原因：{reason}

        請生成一句「簡短、專業且具備商業說服力」的備貨或銷售建議話術給藥師看。
        限制：30字以內，繁體中文。
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "建議依照過往銷量與目前庫存水位進行彈性調整。"