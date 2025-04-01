import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError

from ..db import db_session
from ..models.api_usage import ApiUsage
from .balance_service import BalanceService
from .pricing_service import PricingService

logger = logging.getLogger(__name__)

class ApiUsageService:
    @staticmethod
    def record_api_usage(
        user_id: str,
        api_type: str,
        task_id: str,
        model_size: Optional[str] = None,
        input_size: Optional[float] = None,
        duration: Optional[float] = None,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """记录API使用并扣除余额"""
        # 计算价格
        try:
            price_info = PricingService.get_price(
                api_type=api_type,
                model_size=model_size,
                duration=duration,
                file_size=input_size
            )
            cost = price_info["price"]
        except ValueError as e:
            logger.error(f"计算价格失败: {e}")
            raise
        
        # 扣除余额
        try:
            consume_result = BalanceService.consume_user_balance(
                user_id=user_id,
                amount=cost,
                description=f"use {api_type} service" + (f" ({model_size})" if model_size else "")
            )
        except ValueError as e:
            logger.error(f"扣除余额失败: {e}")
            raise
        
        # 记录API使用
        db = db_session()
        try:
            api_usage = ApiUsage(
                user_id=user_id,
                api_type=api_type,
                model_size=model_size,
                cost=Decimal(str(cost)),
                input_size=input_size,
                duration=duration,
                task_id=task_id,
                details=details
            )
            db.add(api_usage)
            db.commit()
            db.refresh(api_usage)
            
            return {
                "usage": api_usage.to_dict(),
                "balance": consume_result["balance"],
                "transaction": consume_result["transaction"]
            }
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"记录API使用失败: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_user_api_usage(
        user_id: str, 
        page: int = 1, 
        per_page: int = 20, 
        api_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取用户API使用记录"""
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        
        db = db_session()
        try:
            # 构建查询
            query = db.query(ApiUsage).filter(ApiUsage.user_id == user_id)
            
            if api_type:
                query = query.filter(ApiUsage.api_type == api_type)
            
            # 查询总数
            total = query.count()
            
            # 分页查询
            usages = query.order_by(
                ApiUsage.created_at.desc()
            ).offset((page - 1) * per_page).limit(per_page).all()
            
            return {
                "total": total,
                "page": page,
                "per_page": per_page,
                "items": [u.to_dict() for u in usages]
            }
        except SQLAlchemyError as e:
            logger.error(f"查询API使用记录失败: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_api_usage_stats(user_id: str) -> Dict[str, Any]:
        """获取用户API使用统计"""
        db = db_session()
        try:
            # 总消费金额
            total_cost = db.query(ApiUsage).filter(
                ApiUsage.user_id == user_id
            ).with_entities(
                ApiUsage.api_type,
                ApiUsage.model_size,
                db.func.sum(ApiUsage.cost).label("total_cost"),
                db.func.count(ApiUsage.id).label("count")
            ).group_by(
                ApiUsage.api_type,
                ApiUsage.model_size
            ).all()
            
            # 按API类型汇总
            api_type_stats = {}
            for stat in total_cost:
                api_type = stat.api_type
                if api_type not in api_type_stats:
                    api_type_stats[api_type] = {
                        "total_cost": 0,
                        "count": 0,
                        "models": {}
                    }
                
                # 总计
                api_type_stats[api_type]["total_cost"] += float(stat.total_cost)
                api_type_stats[api_type]["count"] += stat.count
                
                # 按模型汇总
                model_size = stat.model_size or "default"
                if model_size not in api_type_stats[api_type]["models"]:
                    api_type_stats[api_type]["models"][model_size] = {
                        "total_cost": 0,
                        "count": 0
                    }
                
                api_type_stats[api_type]["models"][model_size]["total_cost"] += float(stat.total_cost)
                api_type_stats[api_type]["models"][model_size]["count"] += stat.count
            
            return {
                "total_cost": sum(stats["total_cost"] for stats in api_type_stats.values()),
                "total_count": sum(stats["count"] for stats in api_type_stats.values()),
                "api_types": api_type_stats
            }
        except SQLAlchemyError as e:
            logger.error(f"查询API使用统计失败: {e}")
            raise
        finally:
            db.close() 