from fastapi import APIRouter
from pydantic import BaseModel
import google.generativeai as genai
from util.config import env

# 從環境變數載入 Gemini API Key
genai.configure(api_key=env.GEMINI_API_KEY)

router = APIRouter(prefix="/insight")

class Req(BaseModel):
    text: str

@router.post("/")
def analyze(req: Req):

    prompt = f"""
    你是一個藥局輿情分析模型。
    文章內容如下：

    {req.text}

    請分析這段內容，並輸出 **純 JSON**：

    {{
      "intent": "想買 / 求知 / 抱怨 / 比價 / 缺貨",
      "sentiment": "positive / negative / neutral",
      "brand": "偵測到的品牌（沒有則空字串）",
      "ingredient": "成分/學名（沒有則空字串）",
      "symptom": "提到的症狀（沒有則空字串）",
      "confidence": 0.0
    }}

    請務必只回傳 JSON，不能有其他文字。
    """

    model = genai.GenerativeModel("gemini-pro")   # text 模型
    response = model.generate_content(prompt)

    return {"result": response.text}