from decimal import Decimal
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta

from ..db import db_session
from ..models.user import User
from ..models.transaction_record import TransactionRecord, TransactionType
from ..models.user_balance import UserBalance

logger = logging.getLogger(__name__)

class BalanceService:
    @staticmethod
    def record_register_balance(user_id: str, points: int = 50) -> Dict[str, Any]:
        """记录注册赠送点数
        
        Args:
            user_id: 用户ID
            points: 赠送点数数量，默认500点
            
        Returns:
            Dict: 交易记录字典
        """
        try:
            # 获取用户
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("用户不存在")
            
            # 设置点数过期时间（30天后）
            expires_at = datetime.utcnow() + timedelta(days=30)
            decimal_points = Decimal(str(points))
            
            # 更新用户余额
            user.balance += decimal_points
            user.total_charged += decimal_points
            
            # 确保用户有对应的UserBalance记录
            balance_record = db_session.query(UserBalance).filter(UserBalance.user_id == user_id).first()
            if not balance_record:
                balance_record = UserBalance(
                    user_id=user_id,
                    balance=decimal_points,
                    total_charged=decimal_points,
                    total_consumed=Decimal('0')
                )
                db_session.add(balance_record)
            else:
                balance_record.balance += decimal_points
                balance_record.total_charged += decimal_points
            
            # 创建交易记录
            transaction = TransactionRecord(
                user_id=user_id,
                amount=decimal_points,
                balance=user.balance,  # 使用更新后的余额
                transaction_type=TransactionType.REGISTER,
                description="New user registration bonus points",
                expires_at=expires_at
            )
            
            db_session.add(transaction)
            db_session.commit()
            db_session.refresh(transaction)
            db_session.refresh(user)  # 刷新用户对象
            if balance_record in db_session:
                db_session.refresh(balance_record)  # 刷新余额记录
            
            return transaction.to_dict()
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"记录注册赠送点数失败: {e}")
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
    def get_user_transactions(user_id: str, page: int = 1, per_page: int = 20) -> Tuple[List[Dict[str, Any]], int]:
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
            
            return [t.to_dict() for t in transactions], total
        except SQLAlchemyError as e:
            logger.error(f"查询用户交易记录失败: {e}")
            raise
    
    @staticmethod
    def check_expired_balance(user_id: str) -> None:
        """检查并处理过期点数"""
        try:
            # 查找已过期但未标记为过期的点数记录
            now = datetime.utcnow()
            expired_transactions = db_session.query(TransactionRecord).filter(
                TransactionRecord.user_id == user_id,
                TransactionRecord.expires_at < now,
                TransactionRecord.transaction_type.in_([TransactionType.REGISTER, TransactionType.GIFT])
            ).all()
            
            if not expired_transactions:
                return
            
            # 更新用户点数
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return
            
            # 计算要扣除的点数
            total_expired = sum(float(t.amount) for t in expired_transactions if float(t.amount) > 0)
            
            if total_expired > 0:
                # 确保不会出现负数点数
                current_balance = float(user.balance)
                deduct_points = min(current_balance, total_expired)
                
                if deduct_points > 0:
                    # 更新用户余额
                    user.balance -= Decimal(str(deduct_points))
                    
                    # 创建过期记录
                    transaction = TransactionRecord(
                        user_id=user_id,
                        amount=-Decimal(str(deduct_points)),
                        balance=user.balance,
                        transaction_type=TransactionType.CONSUME,
                        description=f"Points expired {len(expired_transactions)} records）"
                    )
                    
                    db_session.add(transaction)
                    db_session.commit()
                    
                    logger.info(f"用户 {user_id} 的 {deduct_points} 点数已过期")
        
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"处理过期点数失败: {e}")
            raise 