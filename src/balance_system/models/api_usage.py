from sqlalchemy import Column, Integer, String, Numeric, DateTime, func, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..db import Base

class ApiUsage(Base):
    """API使用记录模型"""
    __tablename__ = "api_usages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="用户ID")
    transaction_id = Column(Integer, ForeignKey('transaction_records.id', ondelete='SET NULL'), nullable=True, comment="交易ID")
    api_type = Column(String(50), index=True, nullable=False, comment="API类型")
    model_size = Column(String(50), nullable=True, comment="模型大小")
    cost = Column(Numeric(10, 4), nullable=False, comment="消费金额")
    input_size = Column(Float, nullable=True, comment="输入大小(MB)")
    duration = Column(Float, nullable=True, comment="处理时长(秒)")
    task_id = Column(String(100), unique=True, nullable=True, comment="任务ID")
    details = Column(String(500), nullable=True, comment="详细信息")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    
    # 关系
    user = relationship("User", back_populates="api_usages")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "transaction_id": self.transaction_id,
            "api_type": self.api_type,
            "model_size": self.model_size,
            "cost": float(self.cost),
            "input_size": self.input_size,
            "duration": self.duration,
            "task_id": self.task_id,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        } 