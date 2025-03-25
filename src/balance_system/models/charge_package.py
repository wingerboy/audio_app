from sqlalchemy import Column, Integer, String, Numeric, DateTime, func, Boolean
from ..db import Base

class ChargePackage(Base):
    """充值套餐模型"""
    __tablename__ = "charge_packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="套餐名称")
    price = Column(Numeric(10, 2), nullable=False, comment="套餐价格")
    value = Column(Numeric(10, 2), nullable=False, comment="套餐价值")
    description = Column(String(200), nullable=True, comment="套餐描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序")
    created_at = Column(DateTime, server_default=func.now(), nullable=False, comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "price": float(self.price),
            "value": float(self.value),
            "description": self.description,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 