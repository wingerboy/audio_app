from decimal import Decimal
import logging
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.exc import SQLAlchemyError

from ..db import db_session
from ..models.pricing_rule import PricingRule
from ..models.charge_package import ChargePackage

logger = logging.getLogger(__name__)

class PricingService:
    """定价服务，负责计算API使用费用"""
    
    # 默认定价规则
    DEFAULT_PRICING_RULES = {
        'tiny': {'base_price': 0.1, 'size_factor': 0.1},
        'base': {'base_price': 0.2, 'size_factor': 0.15},
        'small': {'base_price': 0.3, 'size_factor': 0.2},
        'medium': {'base_price': 0.5, 'size_factor': 0.25},
        'large': {'base_price': 1.0, 'size_factor': 0.3}
    }
    
    @staticmethod
    def estimate_cost(file_size_mb: float, model_size: str) -> Dict[str, Any]:
        """估算处理费用
        
        Args:
            file_size_mb: 文件大小（MB）
            model_size: 模型大小（tiny/base/small/medium/large）
            
        Returns:
            Dict: 包含预估费用和详细信息的字典
        """
        try:
            # 获取定价规则
            rule = PricingService.DEFAULT_PRICING_RULES.get(model_size)
            if not rule:
                raise ValueError(f"不支持的模型大小: {model_size}")
            
            # 计算费用
            base_price = Decimal(str(rule['base_price']))
            size_factor = Decimal(str(rule['size_factor']))
            file_size = Decimal(str(file_size_mb))
            
            # 基础费用 + 文件大小费用
            estimated_cost = base_price + (file_size * size_factor)
            
            return {
                "estimated_cost": float(estimated_cost),
                "details": {
                    "base_price": float(base_price),
                    "size_factor": float(size_factor),
                    "file_size": float(file_size),
                    "model_size": model_size
                }
            }
        except Exception as e:
            logger.error(f"估算费用失败: {str(e)}")
            raise
    
    @staticmethod
    def get_pricing_rules() -> List[Dict[str, Any]]:
        """获取所有定价规则"""
        return [
            {
                "model_size": size,
                "base_price": float(rule["base_price"]),
                "size_factor": float(rule["size_factor"])
            }
            for size, rule in PricingService.DEFAULT_PRICING_RULES.items()
        ]
    
    @staticmethod
    def get_charge_packages() -> List[Dict[str, Any]]:
        """获取充值套餐"""
        return [
            {
                "id": "package_1",
                "name": "基础套餐",
                "points": 1000,
                "price": 10,
                "description": "1000点数 = 10元"
            },
            {
                "id": "package_2",
                "name": "进阶套餐",
                "points": 5000,
                "price": 45,
                "description": "5000点数 = 45元"
            },
            {
                "id": "package_3",
                "name": "专业套餐",
                "points": 10000,
                "price": 80,
                "description": "10000点数 = 80元"
            }
        ]
    
    @staticmethod
    def get_all_model_pricing(file_size_mb: float, api_type: str = 'analysis') -> Dict[str, Dict[str, Any]]:
        """
        获取所有模型的定价预估
        
        Args:
            file_size_mb: 文件大小，单位MB
            api_type: API类型，默认为'analysis'
            
        Returns:
            Dict: 包含所有模型的预估费用的字典
        """
        result = {}
        for model_size in ['tiny', 'base', 'small', 'medium', 'large']:
            try:
                cost_info = PricingService.estimate_cost(file_size_mb, model_size)
                result[model_size] = cost_info
            except ValueError:
                # 如果某个模型没有定价规则，跳过
                continue
        
        return result
    
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