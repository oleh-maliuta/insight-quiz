from pymongo import MongoClient
from app.constants import MONGO_DB_URL, MONGO_DB_NAME

client = MongoClient(MONGO_DB_URL)
db = client[MONGO_DB_NAME]