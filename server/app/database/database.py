import logging
from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError
from app.constants import MONGO_DB_URL, MONGO_DB_NAME

load_dotenv()

client = MongoClient(MONGO_DB_URL)
db = client[MONGO_DB_NAME]


def _ensure_indexes():
    try:
        db.users.create_index('email', unique=True)
    except PyMongoError as error:
        logging.warning('Could not ensure MongoDB indexes: %s', error)


try:
    client.admin.command('ping')
    _ensure_indexes()
    logging.info('Connected to MongoDB and ensured indexes.')
except Exception as error:
    logging.warning('Could not connect to MongoDB during startup: %s', error)


def get_db():
    yield db
