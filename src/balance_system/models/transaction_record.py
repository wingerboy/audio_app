from sqlalchemy import Column, Integer, String, Numeric, DateTime, func, Enum, ForeignKey
import enum
from sqlalchemy.orm import relationship
from ..db import Base

class TransactionType(enum.Enum):
    """交易类型"""
    CHARGE = "charge"  # 充值
    CONSUME = "consume"  # 消费
    GIFT = "gift"      # 赠送
    REGISTER = "register"  # 注册赠送
    AGENT_CHARGE = "agent_charge"  # 代理划扣给用户
    AGENT_CONSUME = "agent_consume"  # 代理划扣消费

class TransactionRecord(Base):
    """交易记录模型"""
    __tablename__ = "transaction_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="用户ID")
    amount = Column(Numeric(10, 2), nullable=False, comment="交易金额")
    balance = Column(Numeric(10, 2), nullable=False, comment="交易后余额")
    transaction_type = Column(Enum(TransactionType), nullable=False, comment="交易类型")
    description = Column(String(200), nullable=True, comment="交易描述")
    operator = Column(String(50), nullable=True, comment="操作人")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    
    # 关系
    api_usages = relationship("ApiUsage", backref="transaction_record")
    user_task = relationship("UserTask", backref="transaction_record")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount),
            "balance": float(self.balance),
            "transaction_type": self.transaction_type.value,
            "description": self.description,
            "operator": self.operator,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }