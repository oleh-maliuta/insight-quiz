from datetime import datetime
from typing import Optional, List, Dict, Any


class Attempt:
    def __init__(self, document: dict):
        self.doc = document or {}

    @classmethod
    def from_document(cls, document: dict):
        return cls(document) if document else None

    @property
    def id(self) -> Optional[str]:
        return self.doc.get('_id')

    @property
    def user_id(self) -> Optional[str]:
        return self.doc.get('user_id')

    @property
    def quiz_id(self) -> Optional[str]:
        return self.doc.get('quiz_id')

    @property
    def answers(self) -> Optional[List[Dict[str, Any]]]:
        return self.doc.get('answers')
    
    @property
    def created_at(self) -> Optional[datetime]:
        return self.doc.get('created_at')

    @property
    def updated_at(self) -> Optional[datetime]:
        return self.doc.get('updated_at')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'answers': self.answers,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
