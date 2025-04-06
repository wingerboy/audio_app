from sqlalchemy import Column, Integer, String, Numeric, DateTime, func, Boolean
from ..db import Base

class PricingRule(Base):
    """定价规则模型"""
    __tablename__ = "pricing_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    api_type = Column(String(50), index=True, nullable=False, comment="API类型")
    model_size = Column(String(50), nullable=True, comment="模型大小")
    base_price = Column(Numeric(10, 4), nullable=False, comment="基础价格")
    price_per_minute = Column(Numeric(10, 4), nullable=True, comment="每分钟价格")
    price_per_mb = Column(Numeric(10, 4), nullable=True, comment="每MB价格")
    description = Column(String(200), nullable=True, comment="描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "api_type": self.api_type,
            "model_size": self.model_size,
            "base_price": float(self.base_price),
            "price_per_minute": float(self.price_per_minute) if self.price_per_minute else None,
            "price_per_mb": float(self.price_per_mb) if self.price_per_mb else None,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 