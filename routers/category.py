from fastapi import APIRouter
from db.mongo import db

router = APIRouter(prefix="/category")

@router.get("/")
def get_category():
    data = list(db.category.find())
    for d in data:
        d["_id"] = str(d["_id"])
    return data