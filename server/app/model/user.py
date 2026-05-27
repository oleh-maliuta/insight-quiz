from datetime import datetime
from typing import Optional
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
    def email(self) -> Optional[str]:
        return self.doc.get('email')

    @property
    def password(self) -> Optional[str]:
        return self.doc.get('password')

    @password.setter
    def password(self, value: str):
        self.doc['password'] = value

    @property
    def role(self) -> Optional[str]:
        return self.doc.get('role')

    @property
    def created_at(self) -> Optional[datetime]:
        return self.doc.get('created_at')

    @property
    def synchronized_at(self) -> Optional[datetime]:
        return self.doc.get('synchronized_at')

    @synchronized_at.setter
    def synchronized_at(self, value: datetime):
        self.doc['synchronized_at'] = value

    @property
    def is_email_verified(self) -> bool:
        return bool(self.doc.get('is_email_verified'))

    @is_email_verified.setter
    def is_email_verified(self, value: bool):
        self.doc['is_email_verified'] = bool(value)

    @property
    def synchronized_at_iso(self) -> Optional[str]:
        return self.synchronized_at.isoformat() if self.synchronized_at else None

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
        }
    


