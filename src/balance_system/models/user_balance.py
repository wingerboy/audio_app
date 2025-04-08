from sqlalchemy import Column, Integer, String, Numeric, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from ..db import Base

class UserBalance(Base):
    """用户余额模型"""
    __tablename__ = "user_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False, comment="用户ID")
    balance = Column(Numeric(10, 2), default=0, nullable=False, comment="当前余额")
    total_charged = Column(Numeric(10, 2), default=0, nullable=False, comment="总充值金额")
    total_consumed = Column(Numeric(10, 2), default=0, nullable=False, comment="总消费金额")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    
    # 关联到User表
    user = relationship("User", back_populates="balance_record")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "balance": float(self.balance),
            "total_charged": float(self.total_charged),
            "total_consumed": float(self.total_consumed),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 