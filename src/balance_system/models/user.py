from sqlalchemy import Column, String, Numeric, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, generate_uuid
from decimal import Decimal

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    # 新用户默认余额
    DEFAULT_BALANCE = Decimal('100.00')  # 默认赠送100元
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    balance = Column(Numeric(10, 2), default=DEFAULT_BALANCE, nullable=False)
    total_charged = Column(Numeric(10, 2), default=DEFAULT_BALANCE, nullable=False)  # 包含赠送金额
    total_consumed = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # 关系
    transactions = relationship("TransactionRecord", backref="user")
    api_usages = relationship("ApiUsage", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>" 