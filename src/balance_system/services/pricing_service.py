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
    
    # 新的定价规则 - 基于文件大小和音频时长
    DEFAULT_PRICING_RULES = {
        'base_fee': 5,           # 基础费用，固定为10点
        'base_fee_weight': 1,     # 基础费用权重，固定为1
        'duration_fee': 1.5,        # 每分钟时长费用基础数值
        'duration_fee_weight': 1, # 时长费用权重，可根据模型调整
        'file_size_fee': 1,       # 每MB文件大小费用基础数值
        'file_size_fee_weight': 1, # 文件大小费用权重，可根据模型调整
        'discount_rate': 1,   # 折扣率，默认100%
    }
    
    @staticmethod
    def estimate_cost(file_size_mb: float, audio_duration_minutes: Optional[float] = None) -> Dict[str, Any]:
        """估算处理费用
        
        Args:
            file_size_mb: 文件大小（MB）=
            audio_duration_minutes: 音频时长（分钟），如果未提供，将根据文件大小估算
            
        Returns:
            Dict: 包含预估费用和详细信息的字典
        """
        try:
            # 获取定价规则
            rule = PricingService.DEFAULT_PRICING_RULES
            
            # 如果未提供音频时长，根据文件大小进行估算
            # 假设平均每分钟音频约2MB (根据实际情况调整)
            if audio_duration_minutes is None:
                audio_duration_minutes = file_size_mb / 2.0
            
            # 计算费用
            # 1. 基础费用
            base_fee = Decimal(str(rule['base_fee'])) * Decimal(str(rule['base_fee_weight']))
            
            # 2. 音频时长费用
            duration_fee = Decimal(str(rule['duration_fee'])) * Decimal(str(rule['duration_fee_weight'])) * Decimal(str(audio_duration_minutes))
            
            # 3. 文件大小费用
            file_size_fee = Decimal(str(rule['file_size_fee'])) * Decimal(str(rule['file_size_fee_weight'])) * Decimal(str(file_size_mb))
            
            # 总费用
            total_cost = (base_fee + duration_fee + file_size_fee) * Decimal(str(rule['discount_rate']))
            
            return {
                "estimated_cost": float(total_cost),
                "details": {
                    "base_fee": float(base_fee),
                    "duration_fee": float(duration_fee),
                    "file_size_fee": float(file_size_fee),
                    "file_size_mb": float(file_size_mb),
                    "discount_rate": float(rule['discount_rate']),
                    "audio_duration_minutes": float(audio_duration_minutes)
                }
            }
        except Exception as e:
            logger.error(f"估算费用失败: {str(e)}")
            raise
    
    @staticmethod
    def get_pricing_rules() -> List[Dict[str, Any]]:
        """获取所有定价规则"""
        return PricingService.DEFAULT_PRICING_RULES
    
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