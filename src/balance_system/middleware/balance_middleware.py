import logging
import json
import uuid
from flask import request, jsonify, g
from functools import wraps
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.balance_service import BalanceService
from ..services.pricing_service import PricingService
from ..services.api_usage_service import ApiUsageService

logger = logging.getLogger(__name__)

class BalanceMiddleware:
    """余额系统中间件，用于API请求的余额检查和消费记录"""
    
    @staticmethod
    def check_balance(api_type, model_size=None):
        """检查余额是否足够的装饰器"""
        def decorator(f):
            @wraps(f)
            @jwt_required()
            def decorated_function(*args, **kwargs):
                user_id = get_jwt_identity()
                
                # 获取请求信息
                content_length = request.content_length or 0
                file_size = content_length / 1024 / 1024  # 转换为MB
                
                try:
                    # 计算价格
                    price_info = PricingService.get_price(
                        api_type=api_type,
                        model_size=model_size,
                        file_size=file_size
                    )
                    cost = price_info["price"]
                    
                    # 获取用户余额
                    balance_info = BalanceService.get_user_balance(user_id)
                    balance = balance_info["balance"]
                    
                    # 检查余额是否足够
                    if balance < cost:
                        return jsonify({
                            "status": "error",
                            "message": "余额不足，请充值",
                            "balance": balance,
                            "required": cost
                        }), 402  # Payment Required
                    
                    # 保存预估费用到g对象
                    g.estimated_cost = cost
                    g.api_type = api_type
                    g.model_size = model_size
                    g.file_size = file_size
                    g.task_id = str(uuid.uuid4())
                    
                    # 继续处理请求
                    return f(*args, **kwargs)
                except ValueError as e:
                    logger.error(f"余额检查失败: {e}")
                    return jsonify({
                        "status": "error",
                        "message": str(e)
                    }), 400
                except Exception as e:
                    logger.error(f"余额检查过程中发生错误: {e}")
                    return jsonify({
                        "status": "error",
                        "message": "服务器内部错误，请稍后重试"
                    }), 500
            
            return decorated_function
        
        return decorator
    
    @staticmethod
    def record_usage():
        """记录API使用的装饰器"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 记录开始时间
                import time
                start_time = time.time()
                
                # 调用原始函数
                response = f(*args, **kwargs)
                
                # 计算处理时间
                duration = time.time() - start_time
                
                try:
                    # 确保有用户身份和API类型
                    if hasattr(g, 'task_id') and hasattr(g, 'api_type'):
                        user_id = get_jwt_identity()
                        
                        # 获取处理结果信息
                        if isinstance(response, tuple):
                            response_data = response[0]
                            status_code = response[1]
                        else:
                            response_data = response
                            status_code = 200
                        
                        # 只记录成功的请求
                        if 200 <= status_code < 300:
                            # 将response_data转换为字符串（如果是Response对象）
                            if hasattr(response_data, 'get_data'):
                                json_data = json.loads(response_data.get_data(as_text=True))
                            else:
                                json_data = json.loads(response_data)
                            
                            # 提取处理结果的详细信息
                            details = {
                                "status": json_data.get("status"),
                                "duration": duration,
                                "response_code": status_code
                            }
                            
                            # 记录API使用
                            ApiUsageService.record_api_usage(
                                user_id=user_id,
                                api_type=g.api_type,
                                task_id=g.task_id,
                                model_size=getattr(g, 'model_size', None),
                                input_size=getattr(g, 'file_size', None),
                                duration=duration,
                                details=json.dumps(details)
                            )
                    
                except Exception as e:
                    logger.error(f"记录API使用失败: {e}")
                    # 不影响原始响应
                
                return response
            
            return decorated_function
        
        return decorator 