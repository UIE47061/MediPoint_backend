from fastapi import APIRouter
from services.dashboard import get_weekly_dashboard_data

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/weekly-report")
def get_weekly_report():
    """
    取得本週戰情摘要 (包含 KPI, 建議, 輿情)
    """
    # 直接呼叫 Service 層的函式
    return get_weekly_dashboard_data()