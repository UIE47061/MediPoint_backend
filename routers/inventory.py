from fastapi import APIRouter
from db.mongo import db

router = APIRouter(prefix="/inventory")

@router.get("/")
def get_inventory():
    data = list(db.inventory.find())
    for d in data:
        d["_id"] = str(d["_id"])
    return data

@router.get("/low")
def low_stock(threshold: int = 10):
    data = list(db.inventory.find({"stock_on_hand": {"$lt": threshold}}))
    for d in data:
        d["_id"] = str(d["_id"])
    return data