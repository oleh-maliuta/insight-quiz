from datetime import datetime
from typing import Optional, List, Dict, Any


class Question:
    def __init__(self, document: dict):
        self.doc = document or {}

    @classmethod
    def from_document(cls, document: dict):
        return cls(document) if document else None

    @property
    def id(self) -> Optional[str]:
        return self.doc.get('_id')

    @property
    def quiz_id(self) -> Optional[str]:
        return self.doc.get('quiz_id')

    @property
    def type(self) -> Optional[str]:
        return self.doc.get('type')

    @property
    def title(self) -> Optional[str]:
        return self.doc.get('title')

    @property
    def content(self) -> Optional[str]:
        return self.doc.get('content')

    @property
    def attachments(self) -> Optional[List[str]]:
        return self.doc.get('attachments')

    @property
    def answer(self) -> Optional[Dict[str, Any]]:
        return self.doc.get('answer')

    @property
    def created_at(self) -> Optional[datetime]:
        return self.doc.get('created_at')

    @property
    def updated_at(self) -> Optional[datetime]:
        return self.doc.get('updated_at')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'attachments': self.attachments,
            'answer': self.answer,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
