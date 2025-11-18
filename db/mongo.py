from pymongo import MongoClient
from pymongo.server_api import ServerApi
import sys
import pathlib
import certifi

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from util.config import env

MONGO_URI = env.MongoDB_URL

client = MongoClient(
    MONGO_URI,
    server_api=ServerApi("1"),          # 使用 Server API v1（Atlas 官方建議）
    tls=True,                           # 明確啟用 TLS
    tlsCAFile=certifi.where(),          # 使用 certifi 的根憑證
    tlsAllowInvalidCertificates=True,   # ⚠ Demo 用：放寬憑證驗證
)

db = client["medipoint"]