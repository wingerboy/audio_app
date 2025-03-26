import bcrypt
from sqlalchemy import Column, String, Numeric, Boolean, Text, DateTime, Integer, func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, generate_uuid
from decimal import Decimal
from datetime import datetime

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    # 新用户默认余额 (点数)
    DEFAULT_BALANCE = Decimal('500.00')  # 默认赠送500点数
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    balance = Column(Numeric(10, 2), default=DEFAULT_BALANCE, nullable=False)
    total_charged = Column(Numeric(10, 2), default=DEFAULT_BALANCE, nullable=False)  # 包含赠送金额
    total_consumed = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # 关系
    transactions = relationship("TransactionRecord", backref="user")
    api_usages = relationship("ApiUsage", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_password(self, password):
        """设置密码"""
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password):
        """验证密码"""
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )
    
    def to_dict(self):
        """转换为字典表示"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.timestamp() if self.created_at else None,
            'last_login': self.last_login.timestamp() if self.last_login else None,
            'balance': float(self.balance),
            'total_charged': float(self.total_charged),
            'total_consumed': float(self.total_consumed)
        } 