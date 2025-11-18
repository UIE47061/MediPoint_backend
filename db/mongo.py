from pymongo import MongoClient
import sys
import pathlib
import certifi

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from util.config import env

MONGO_URI = env.MongoDB_URL

client = MongoClient(env.MongoDB_URL, tlsCAFile=certifi.where())
db = client["medipoint"]