import bcrypt
from sqlalchemy import Column, String, Numeric, Boolean, Text, DateTime, Integer, func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, generate_uuid
from decimal import Decimal
from datetime import datetime

# 用户角色常量定义
ROLE_USER = 0       # 普通用户
ROLE_ADMIN = 1      # 管理员
ROLE_AGENT = 2      # 一级代理
ROLE_SENIOR_AGENT = 3  # 高级代理

class User(Base, TimestampMixin):
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # 将is_admin从Boolean改为Integer，并重命名为role
    role = Column(Integer, default=ROLE_USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    balance = Column(Numeric(10, 2), default=0, nullable=False)
    total_charged = Column(Numeric(10, 2), default=0, nullable=False)  
    total_consumed = Column(Numeric(10, 2), default=0.00, nullable=False)
    
    # 关系
    transactions = relationship("TransactionRecord", backref="user")
    api_usages = relationship("ApiUsage", back_populates="user")
    balance_record = relationship("UserBalance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
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
    
    # 增加角色判断的辅助方法
    def is_admin(self):
        """判断用户是否为管理员"""
        return self.role == ROLE_ADMIN
    
    def is_agent(self):
        """判断用户是否为代理"""
        return self.role == ROLE_AGENT
    
    def is_senior_agent(self):
        """判断用户是否为高级代理"""
        return self.role == ROLE_SENIOR_AGENT
    
    def has_admin_access(self):
        """判断用户是否有管理员权限（包括管理员和高级代理）"""
        return self.role in (ROLE_ADMIN, ROLE_SENIOR_AGENT)
    
    def get_role_name(self):
        """获取用户角色名称"""
        role_names = {
            ROLE_USER: "普通用户",
            ROLE_ADMIN: "管理员",
            ROLE_AGENT: "一级代理",
            ROLE_SENIOR_AGENT: "高级代理"
        }
        return role_names.get(self.role, "未知角色")
    
    def to_dict(self):
        """转换为字典表示"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'role': self.role,
            'role_name': self.get_role_name(),
            'is_admin': self.is_admin(),  # 为了向后兼容
            'created_at': self.created_at.timestamp() if self.created_at else None,
            'last_login': self.last_login.timestamp() if self.last_login else None,
            'balance': float(self.balance),
            'total_charged': float(self.total_charged),
            'total_consumed': float(self.total_consumed)
        } 