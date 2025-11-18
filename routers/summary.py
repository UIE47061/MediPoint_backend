from fastapi import APIRouter
from db.mongo import db

router = APIRouter(prefix="/summary")

@router.get("/")
def get_summary():
    data = list(db.summary.find())
    for d in data:
        d["_id"] = str(d["_id"])
    return data