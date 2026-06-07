import re
from typing import Optional
import bcrypt
from fastapi.responses import JSONResponse
import jwt
import logging
from datetime import datetime, timedelta, timezone
from pymongo.database import Database
from pymongo.errors import PyMongoError
from fastapi import HTTPException

from app.user_manager.mail_controller import send_password_change_form, send_verification_link
from app.model.user import RoleEnum, User
from app.utils.db.auth import get_current_user
from app.constants import *

# Налаштування логування
logging.basicConfig(level=logging.DEBUG)


# 🔹 Hash
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# 🔹 Verify
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# 🔹 Generate JWT token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(
        timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # Додаємо час дії токену
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ENCODE_ALGORITHM)

# Create a new user
async def create_user(db: Database, first_name: str, last_name: str, email: str, password: str, role: RoleEnum, locale: str):
    try:
        # email verification
        email_regex = r"(^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$)"
        if not re.match(email_regex, email):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid email format",
                    "data": None
                }
            )
        existing_user = db.users.find_one({'email': email})
        if existing_user:
            return JSONResponse(
                status_code=400,
                content={
                    'detail': 'Email is already taken',
                    'data': None,
                },
            )

        hashed_password = hash_password(password)
        now = datetime.now(timezone.utc)
        user_doc = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password_hash': hashed_password,
            'role': role.value,
            'created_at': now,
            'synchronized_at': now,
            'is_email_verified': False,
        }
        db.users.insert_one(user_doc)
        token = create_access_token({'sub': email}, expires_delta=timedelta(hours=24))
        await send_verification_link(email, token, locale)
        return JSONResponse(
            status_code=201,
            content={
                'detail': 'Register successful. Please verify your email',
                'data': {
                    'access_token': token,
                    'token_type': 'bearer',
                },
            },
        )

    except PyMongoError as e:
        logging.error('MongoDB error in create_user: %s', e)
        return JSONResponse(
            status_code=500,
            content={
                'detail': 'Database error',
                'data': None,
            },
        )


# 🔹 Authenticate user and generate JWT token
def authenticate_user(db: Database, email: str, password: str):
    user_doc = db.users.find_one({'email': email})
    logging.debug(f'Retrieved user document: {user_doc}')

    if not user_doc:
        logging.debug(f'No user found with email: {email}')
        return JSONResponse(
            status_code=404,
            content={
                'detail': 'User not found or incorrect password',
                'data': None,
            },
        )

    user = User.from_document(user_doc)
    if not user or not user.password_hash:
        logging.debug(f'Invalid user record for email: {email}')
        return JSONResponse(
            status_code=404,
            content={
                'detail': 'User not found or incorrect password',
                'data': None,
            },
        )

    if not verify_password(password, user.password_hash):
        logging.debug(f'Authentication failed for user: {email}')
        return JSONResponse(
            status_code=404,
            content={
                'detail': 'User not found or incorrect password',
                'data': None,
            },
        )

    if not user.is_email_verified:
        return JSONResponse(
            status_code=403,
            content={
                'detail': 'Email not verified',
                'data': None,
            },
        )

    access_token = create_access_token(
        data={'sub': str(user.email)},
        expires_delta=timedelta(minutes=30),
    )

    return {
        'detail': 'Authentication successful',
        'data': {
            'access_token': access_token,
            'token_type': 'bearer',
        },
    }


def update_synchronized_at(token: str, db: Database):
    current_user = get_current_user(token, db)
    if isinstance(current_user, JSONResponse):
        return current_user

    now = datetime.now(timezone.utc)
    db.users.update_one({'email': current_user.email}, {'$set': {'synchronized_at': now}})
    current_user.synchronized_at = now
    return JSONResponse(
        status_code=200,
        content={
            "detail": "Synchronized at updated",
            "data": {
                 "synchronized_at": current_user.synchronized_at_iso
            }
        }
    )

def is_user_verified(user_id, db: Database) -> bool:
    try:
        user_doc = db.users.find_one({'id': int(user_id)})
    except (TypeError, ValueError):
        user_doc = None
    return bool(user_doc and user_doc.get('is_email_verified'))

# Functions to update the user's password
def create_password_reset_token(email: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    """
    Creates a password reset token.

    - **Parameters**:
        - `email`: User's email address.
        - `expires_delta`: Expiration time for the token.

    - **Returns**: JWT token for password reset.
    """
    to_encode = {"sub": email, "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ENCODE_ALGORITHM)
async def send_password_reset_email(db: Database, email: str, locale: Optional[str] = 'en'):
    """
    Sends a password reset form to the user's email after verifying the password.
    
    - **Parameters**:
        - `db`: Database connection.
        - `email`: User's email address.
        - `locale`: The language for the reset message ('ua' for Ukrainian, 'en' for English).
    - **Raises**:
        - HTTPException: If the email doesn't exist or the password is incorrect.
    """
    user_doc = db.users.find_one({'email': email})

    if not user_doc:
        raise HTTPException(status_code=404, detail='User not found')


    # Створення токену для скидання пароля
    reset_token = create_password_reset_token(email=email)

    # Формуємо посилання для зміни пароля
    reset_url = f"{SERVER_URL}/change-password-form?token={reset_token}&locale={locale}"

    # Створюємо HTML контент в залежності від мови
    if locale == 'ua':
        html_content = f"""
        <html>
            <body>
                <h3>Зміна пароля</h3>
                <p>Щоб змінити пароль, натисніть на посилання нижче:</p>
                <a href="{reset_url}">Змінити пароль</a>
                <p>Якщо ви не робили запит на зміну пароля, проігноруйте цей лист.</p>
            </body>
        </html>
        """
        subject="Запит на зміну пароля"
    else:
        html_content = f"""
        <html>
            <body>
                <h3>Password Change</h3>
                <p>To change your password, click the link below:</p>
                <a href="{reset_url}">Change Password</a>
                <p>If you did not request a password change, please ignore this email.</p>
            </body>
        </html>
        """
        subject="Password change request"

    # Відправка email користувачу
    try:
        await send_password_change_form(
            email=email,
            subject=subject,
            html_content=html_content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"detail": "Password reset email sent successfully."}

def update_user_password(db: Database, user: User, old_password: str, new_password: str):
    """
    Updates the user's password after verifying the old password.

    :param db: Database connection
    :param user: The current user (User object)
    :param old_password: The user's current password
    :param new_password: The new password for the user
    :raises HTTPException: If the old password is incorrect
    :return: A message confirming the successful password change
    """
    if not verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=400, detail='Incorrect old password')

    new_hashed_password = hash_password(new_password)
    db.users.update_one({'id': user.id}, {'$set': {'password': new_hashed_password}})
    user.password_hash = new_hashed_password

    return {'detail': 'Password successfully updated', 'data': ''}

# Function to update the user's email


async def update_user_email(db: Database, user: User, password: str, new_email: str, locale: str):
    """
    Updates the user's email after verifying the password.
    """
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail='Incorrect password')

    email_regex = r'(^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$)'
    if not re.match(email_regex, new_email):
        raise HTTPException(status_code=400, detail='Invalid email format')

    existing_user = db.users.find_one({'email': new_email})
    if existing_user:
        raise HTTPException(status_code=400, detail='Email is already taken')

    token = create_access_token({'sub': new_email}, expires_delta=timedelta(hours=24))
    update_result = db.users.update_one(
        {'id': user.id},
        {'$set': {'email': new_email, 'is_email_verified': False}},
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail='User not found')

    await send_verification_link(new_email, token, locale)
    return {'detail': 'Email successfully updated. Please verify new email', 'data': ''}
