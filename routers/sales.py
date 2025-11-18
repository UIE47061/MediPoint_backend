from fastapi import APIRouter
from db.mongo import db

router = APIRouter(prefix="/sales")

@router.get("/")
def get_sales(limit: int = 200):
    data = list(db.sales.find().limit(limit))
    for d in data:
        d["_id"] = str(d["_id"])
    return data