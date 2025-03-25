from decimal import Decimal
import logging
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.exc import SQLAlchemyError

from ..db import db_session
from ..models.pricing_rule import PricingRule
from ..models.charge_package import ChargePackage

logger = logging.getLogger(__name__)

class PricingService:
    @staticmethod
    def get_pricing_rules() -> List[Dict[str, Any]]:
        """获取所有定价规则"""
        db = db_session()
        try:
            rules = db.query(PricingRule).filter(PricingRule.is_active == True).all()
            return [rule.to_dict() for rule in rules]
        except SQLAlchemyError as e:
            logger.error(f"查询定价规则失败: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_charge_packages() -> List[Dict[str, Any]]:
        """获取所有充值套餐"""
        db = db_session()
        try:
            packages = db.query(ChargePackage).filter(
                ChargePackage.is_active == True
            ).order_by(ChargePackage.sort_order.asc()).all()
            return [package.to_dict() for package in packages]
        except SQLAlchemyError as e:
            logger.error(f"查询充值套餐失败: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_price(
        api_type: str, 
        model_size: Optional[str] = None, 
        duration: Optional[float] = None, 
        file_size: Optional[float] = None
    ) -> Dict[str, Any]:
        """计算API使用价格"""
        db = db_session()
        try:
            # 查询定价规则
            query = db.query(PricingRule).filter(
                PricingRule.api_type == api_type,
                PricingRule.is_active == True
            )
            
            if model_size:
                rule = query.filter(PricingRule.model_size == model_size).first()
                if not rule:
                    # 如果没有找到特定模型大小的规则，则使用默认规则
                    rule = query.filter(PricingRule.model_size == None).first()
            else:
                rule = query.filter(PricingRule.model_size == None).first()
            
            if not rule:
                raise ValueError(f"未找到API类型为{api_type}的定价规则")
            
            # 计算价格
            price = float(rule.base_price)
            details = {
                "base_price": price,
                "duration_cost": 0,
                "file_size_cost": 0,
            }
            
            # 按时长计费
            if duration and rule.price_per_minute:
                duration_cost = float(rule.price_per_minute) * (duration / 60)  # 分钟单位
                price += duration_cost
                details["duration_cost"] = duration_cost
                details["duration"] = duration
            
            # 按文件大小计费
            if file_size and rule.price_per_mb:
                file_size_cost = float(rule.price_per_mb) * file_size
                price += file_size_cost
                details["file_size_cost"] = file_size_cost
                details["file_size"] = file_size
            
            return {
                "price": round(price, 4),
                "api_type": api_type,
                "model_size": model_size,
                "rule_id": rule.id,
                "details": details
            }
        except SQLAlchemyError as e:
            logger.error(f"计算价格失败: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def create_pricing_rule(rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建定价规则"""
        required_fields = ["api_type", "base_price"]
        for field in required_fields:
            if field not in rule_data:
                raise ValueError(f"缺少必要字段: {field}")
        
        # 确保价格为Decimal类型
        try:
            base_price = Decimal(str(rule_data["base_price"]))
            price_per_minute = Decimal(str(rule_data.get("price_per_minute", 0))) if rule_data.get("price_per_minute") is not None else None
            price_per_mb = Decimal(str(rule_data.get("price_per_mb", 0))) if rule_data.get("price_per_mb") is not None else None
        except (ValueError, TypeError):
            raise ValueError("价格格式不正确")
        
        db = db_session()
        try:
            rule = PricingRule(
                api_type=rule_data["api_type"],
                model_size=rule_data.get("model_size"),
                base_price=base_price,
                price_per_minute=price_per_minute,
                price_per_mb=price_per_mb,
                description=rule_data.get("description"),
                is_active=rule_data.get("is_active", True)
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return rule.to_dict()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"创建定价规则失败: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def create_charge_package(package_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建充值套餐"""
        required_fields = ["name", "price", "value"]
        for field in required_fields:
            if field not in package_data:
                raise ValueError(f"缺少必要字段: {field}")
        
        # 确保价格为Decimal类型
        try:
            price = Decimal(str(package_data["price"]))
            value = Decimal(str(package_data["value"]))
        except (ValueError, TypeError):
            raise ValueError("价格格式不正确")
        
        db = db_session()
        try:
            package = ChargePackage(
                name=package_data["name"],
                price=price,
                value=value,
                description=package_data.get("description"),
                is_active=package_data.get("is_active", True),
                sort_order=package_data.get("sort_order", 0)
            )
            db.add(package)
            db.commit()
            db.refresh(package)
            return package.to_dict()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"创建充值套餐失败: {e}")
            raise
        finally:
            db.close() 