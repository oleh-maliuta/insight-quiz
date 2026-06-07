from fastapi import HTTPException
from fastapi.responses import JSONResponse
import jwt
import logging
from pymongo.database import Database
from app.model.user import User
from app.constants import *


def get_current_user(token: str, db: Database):
    logging.debug('Decoding token: %s', token)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ENCODE_ALGORITHM])
        user_email: str = payload.get("sub")
        if not user_email:
            # Логування помилки, якщо email відсутній
            logging.error("Invalid token: User email not found")
            # Повертаємо JSONResponse при помилці
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        # Логування email користувача
        logging.debug("Decoded user email: %s", user_email)
    except jwt.ExpiredSignatureError:
        # Логування, якщо токен прострочений
        logging.error("Token has expired")
        return JSONResponse(status_code=401, content={"detail": "Token has expired"})
    except jwt.PyJWTError as e:
        # Логування помилки декодування
        logging.error("JWT decoding error: %s", str(e))
        return JSONResponse(status_code=401, content={"detail": "Could not validate credentials"})

    user_doc = db.users.find_one({'email': user_email})
    if user_doc is None:
        logging.debug('User with email %s not found in DB', user_email)
        return JSONResponse(status_code=401, content={'detail': 'User not found'})
    logging.debug('User found in DB: %s', user_email)
    return User.from_document(user_doc)


def get_current_user_id(token: str, db: Database):
    logging.debug('Decoding token: %s', token)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ENCODE_ALGORITHM])
        user_email: str = payload.get("sub")
        if not user_email:
            # Логування помилки, якщо ID відсутнє
            logging.error("Invalid token: User ID not found")
            raise HTTPException(status_code=401, detail="Invalid token")
        # Логування ID користувача
        logging.debug("Decoded user email: %s", user_email)
    except jwt.PyJWTError as e:
        logging.debug("JWT error: %s", str(e))  # Логування помилки декодування
        raise HTTPException(
            status_code=401, detail="Could not validate credentials")

    user_doc = db.users.find_one({'email': user_email})
    if user_doc is None:
        logging.debug('User with email %s not found in DB', user_email)
        raise HTTPException(status_code=401, detail='User not found')
    current_user = User.from_document(user_doc)
    logging.debug('User found in DB: %s', current_user.email)
    return current_user.id