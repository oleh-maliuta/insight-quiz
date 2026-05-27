from datetime import datetime
from typing import Optional


class Quiz:
    def __init__(self, document: dict):
        self.doc = document or {}

    @classmethod
    def from_document(cls, document: dict):
        return cls(document) if document else None

    @property
    def id(self) -> Optional[str]:
        return self.doc.get('_id')

    @property
    def owner_id(self) -> Optional[str]:
        return self.doc.get('owner_id')

    @property
    def name(self) -> Optional[str]:
        return self.doc.get('name')

    @property
    def created_at(self) -> Optional[datetime]:
        return self.doc.get('created_at')

    @property
    def updated_at(self) -> Optional[datetime]:
        return self.doc.get('updated_at')

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'name': self.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    