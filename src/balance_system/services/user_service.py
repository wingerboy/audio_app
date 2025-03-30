from typing import Optional
import logging
from sqlalchemy.exc import SQLAlchemyError

from ..db import db_session
from ..models.user import User

logger = logging.getLogger(__name__)

class UserService:
    """用户服务，提供用户相关操作"""
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            User: 用户对象，不存在则返回None
        """
        try:
            return db_session.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as e:
            logger.error(f"查询用户失败: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户
        
        Args:
            email: 用户邮箱
            
        Returns:
            User: 用户对象，不存在则返回None
        """
        try:
            return db_session.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            logger.error(f"根据邮箱查询用户失败: {e}")
            return None
            
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            User: 用户对象，不存在则返回None
        """
        try:
            return db_session.query(User).filter(User.username == username).first()
        except SQLAlchemyError as e:
            logger.error(f"根据用户名查询用户失败: {e}")
            return None 