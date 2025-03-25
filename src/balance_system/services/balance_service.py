from decimal import Decimal
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from ..db import db_session
from ..models.user import User
from ..models.transaction_record import TransactionRecord, TransactionType

logger = logging.getLogger(__name__)

class BalanceService:
    @staticmethod
    def record_gift_balance(user_id: str, amount: Decimal) -> Dict[str, Any]:
        """记录赠送余额"""
        try:
            # 创建交易记录
            transaction = TransactionRecord(
                user_id=user_id,
                amount=amount,
                balance=amount,  # 初始余额就是赠送金额
                transaction_type=TransactionType.GIFT,
                description="新用户注册赠送余额"
            )
            
            db_session.add(transaction)
            db_session.commit()
            db_session.refresh(transaction)
            
            return transaction.to_dict()
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"记录赠送余额失败: {e}")
            raise
    
    @staticmethod
    def get_user_balance(user_id: str) -> Dict[str, Any]:
        """获取用户余额信息"""
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            
            return {
                "balance": float(user.balance),
                "total_charged": float(user.total_charged),
                "total_consumed": float(user.total_consumed)
            }
        except SQLAlchemyError as e:
            logger.error(f"查询用户余额失败: {e}")
            raise
    
    @staticmethod
    def charge_user_balance(
        user_id: str, 
        amount: float, 
        description: Optional[str] = None,
        operator: Optional[str] = None
    ) -> Dict[str, Any]:
        """用户充值"""
        if amount <= 0:
            raise ValueError("充值金额必须大于0")
        
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            
            # 更新余额
            decimal_amount = Decimal(str(amount))
            user.balance += decimal_amount
            user.total_charged += decimal_amount
            
            # 创建交易记录
            transaction = TransactionRecord(
                user_id=user_id,
                amount=decimal_amount,
                balance=user.balance,
                transaction_type=TransactionType.CHARGE,
                description=description,
                operator=operator
            )
            
            db_session.add(transaction)
            db_session.commit()
            db_session.refresh(user)
            db_session.refresh(transaction)
            
            return {
                "balance": float(user.balance),
                "total_charged": float(user.total_charged),
                "total_consumed": float(user.total_consumed),
                "transaction": transaction.to_dict()
            }
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"用户充值失败: {e}")
            raise
    
    @staticmethod
    def consume_user_balance(
        user_id: str, 
        amount: float, 
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """用户消费"""
        if amount <= 0:
            raise ValueError("消费金额必须大于0")
        
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            
            decimal_amount = Decimal(str(amount))
            
            # 检查余额是否足够
            if user.balance < decimal_amount:
                raise ValueError("余额不足")
            
            # 更新余额
            user.balance -= decimal_amount
            user.total_consumed += decimal_amount
            
            # 创建交易记录
            transaction = TransactionRecord(
                user_id=user_id,
                amount=-decimal_amount,  # 消费为负数
                balance=user.balance,
                transaction_type=TransactionType.CONSUME,
                description=description
            )
            
            db_session.add(transaction)
            db_session.commit()
            db_session.refresh(user)
            db_session.refresh(transaction)
            
            return {
                "balance": float(user.balance),
                "total_charged": float(user.total_charged),
                "total_consumed": float(user.total_consumed),
                "transaction": transaction.to_dict()
            }
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"用户消费失败: {e}")
            raise
    
    @staticmethod
    def get_user_transactions(user_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取用户交易记录"""
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        
        try:
            # 查询总数
            total = db_session.query(TransactionRecord).filter(
                TransactionRecord.user_id == user_id
            ).count()
            
            # 分页查询
            transactions = db_session.query(TransactionRecord).filter(
                TransactionRecord.user_id == user_id
            ).order_by(
                TransactionRecord.created_at.desc()
            ).offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                "total": total,
                "page": page,
                "per_page": per_page,
                "items": [t.to_dict() for t in transactions]
            }
        except SQLAlchemyError as e:
            logger.error(f"查询用户交易记录失败: {e}")
            raise 