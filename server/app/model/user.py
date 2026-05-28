from datetime import datetime
from typing import Optional, List, Dict, Any
import enum


class RoleEnum(str, enum.Enum):
    STUDENT = 'student'
    TEACHER = 'teacher'
    ADMIN = 'admin'


class User:
    def __init__(self, document: dict):
        self.doc = document or {}

    @classmethod
    def from_document(cls, document: dict):
        return cls(document) if document else None

    @property
    def id(self) -> Optional[str]:
        return self.doc.get('_id')

    @property
    def first_name(self) -> Optional[str]:
        return self.doc.get('first_name')

    @property
    def last_name(self) -> Optional[str]:
        return self.doc.get('last_name')

    @property
    def email(self) -> Optional[str]:
        return self.doc.get('email')

    @property
    def password_hash(self) -> Optional[str]:
        return self.doc.get('password_hash')

    @property
    def role(self) -> Optional[str]:
        return self.doc.get('role')

    @property
    def avatar(self) -> Optional[str]:
        return self.doc.get('avatar')

    @property
    def subscription_status(self) -> Optional[str]:
        return self.doc.get('subscription_status')

    @property
    def phone_number(self) -> Optional[str]:
        return self.doc.get('phone_number')

    @property
    def about(self) -> Optional[str]:
        return self.doc.get('about')

    @property
    def is_email_verified(self) -> Optional[bool]:
        return self.doc.get('is_email_verified')

    @property
    def subscription_until(self) -> Optional[datetime]:
        return self.doc.get('subscription_until')
    
    @property
    def synchronized_at(self) -> Optional[datetime]:
        return self.doc.get('synchronized_at')

    @property
    def created_at(self) -> Optional[datetime]:
        return self.doc.get('created_at')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'avatar': self.avatar,
            'subscription_status': self.subscription_status,
            'phone_number': self.phone_number,
            'about': self.about,
            'is_email_verified': self.is_email_verified,
            'tokens': self.tokens,
            'subscription_until': self.subscription_until,
            'created_at': self.created_at,
        }
