import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime
from ..db import Base

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

def generate_uuid():
    return str(uuid.uuid4()) 