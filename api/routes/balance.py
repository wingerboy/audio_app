from flask import Blueprint, request, jsonify, current_app
import logging
from flask_jwt_extended import get_jwt, get_jwt_identity
from src.balance_system.services.balance_service import BalanceService
from src.balance_system.services.pricing_service import PricingService
from functools import wraps
from api.auth import admin_required, login_required, get_current_user, admin_or_agent_required
from src.balance_system.services.user_service import UserService
import os
import uuid
import subprocess
from src.balance_system.models.user import User
from src.balance_system.db import db_session
from src.utils.logging_config import LoggingConfig
from datetime import datetime

# 设置日志
logger = LoggingConfig.setup_logging(log_level=logging.INFO)

# 创建蓝图
bp = Blueprint('balance_bp', __name__, url_prefix='/api/balance')

# 将原路由转换为工具函数
def check_analyze_balance_for_task(task_id, user_id, model_size='base'):
    """检查当前余额是否足够进行音频分析（工具函数）
    
    Args:
        task_id: 任务ID
        user_id: 用户ID
        model_size: 模型大小，默认为'base'
        
    Returns:
        tuple: (is_sufficient, current_balance, estimated_cost, details)
    """
    try:
        # 在函数内部导入task_manager以避免循环导入
        from api.app import task_manager
        
        # 获取任务信息
        task_info = task_manager.get_task(task_id)
        if not task_info:
            raise ValueError(f'找不到任务: {task_id}')
        
        # 获取参数
        file_size_mb = task_info.get('size_mb')
        audio_duration_minutes = task_info.get('audio_duration_minutes')
        
        # 获取用户余额
        user_service = UserService()
        user = user_service.get_user_by_id(user_id)
        
        if not user:
            raise ValueError("用户不存在")
            
        current_balance = user.balance
        
        # 使用传入的model_size或任务中的model_size，或默认为base
        model_size = model_size or task_info.get('model_size', 'base')
        
        # 估算费用
        cost_info = PricingService.estimate_cost(
            file_size_mb=file_size_mb, 
            audio_duration_minutes=audio_duration_minutes
        )
        
        estimated_cost = cost_info["estimated_cost"]
        is_sufficient = current_balance >= estimated_cost
        
        return (is_sufficient, float(current_balance), float(estimated_cost), cost_info["details"])
        
    except Exception as e:
        logger.exception(f"检查余额失败: {str(e)}")
        raise

@bp.route('/info', methods=['GET'])
@login_required
def get_balance_info():
    """获取当前用户的账户信息，包括余额和交易记录"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'status': 'error', 'message': '用户未认证'}), 401
            
        user_id = user['id']
        balance_service = BalanceService()
        
        # 检查点数是否过期
        balance_service.check_expired_balance(user_id)
        
        # 获取用户余额信息
        balance_info = balance_service.get_user_balance(user_id)
        
        # 获取用户交易记录
        transactions, total = balance_service.get_user_transactions(user_id, page=1, per_page=100)
        
        # 格式化返回数据，符合前端的 BalanceInfo 接口要求
        return jsonify({
            'balance': balance_info['balance'],
            'transactions': [{
                'id': str(trans['id']),
                'amount': trans['amount'],
                'type': trans['transaction_type'],
                'created_at': int(datetime.fromisoformat(trans['created_at']).timestamp()),
                'description': trans['description'] or ''
            } for trans in transactions]
        })
    except Exception as e:
        logger.error(f"获取账户信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取账户信息失败: {str(e)}'
        }), 500

@bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    """获取用户交易记录"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'status': 'error', 'message': '用户未认证'}), 401
            
        user_id = user['id']
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        balance_service = BalanceService()
        
        # 获取用户交易记录
        transactions, total = balance_service.get_user_transactions(
            user_id, 
            page=page, 
            per_page=per_page
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'transactions': transactions,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })
    except Exception as e:
        logger.error(f"获取交易记录失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取交易记录失败: {str(e)}'
        }), 500

@bp.route('/packages', methods=['GET'])
@login_required
def get_charge_packages():
    """获取可用的充值套餐"""
    try:
        pricing_service = PricingService()
        
        # 获取充值套餐
        packages = pricing_service.get_charge_packages()
        
        return jsonify({
            'status': 'success',
            'data': {
                'packages': packages
            }
        })
    except Exception as e:
        logger.error(f"获取充值套餐失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取充值套餐失败: {str(e)}'
        }), 500

@bp.route('/pricing', methods=['GET'])
@login_required
def get_pricing_rules():
    """获取计费规则"""
    try:
        pricing_service = PricingService()
        
        # 获取计费规则
        rules = pricing_service.get_pricing_rules()
        
        return jsonify({
            'status': 'success',
            'data': {
                'rules': rules
            }
        })
    except Exception as e:
        logger.error(f"获取计费规则失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取计费规则失败: {str(e)}'
        }), 500

@bp.route('/calculate_price', methods=['POST'])
@login_required
def calculate_price():
    """计算API使用费用"""
    try:
        data = request.json
        
        # 验证必要参数
        required_fields = ['api_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要参数: {field}'
                }), 400
        
        # 提取参数
        api_type = data.get('api_type')
        model_size = data.get('model_size')
        duration = data.get('duration')  # 秒
        file_size = data.get('file_size')  # MB
        
        pricing_service = PricingService()
        
        # 计算价格
        price = pricing_service.calculate_price(
            api_type=api_type,
            model_size=model_size,
            duration=duration,
            file_size=file_size
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'price': price
            }
        })
    except Exception as e:
        logger.error(f"计算价格失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'计算价格失败: {str(e)}'
        }), 500

@bp.route('/admin/charge', methods=['POST'])
@admin_or_agent_required
def admin_charge():
    """管理员充值（现在也允许代理）"""
    try:
        data = request.json
        
        # 验证必要参数
        required_fields = ['email', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要参数: {field}'
                }), 400
        
        # 提取参数
        email = data.get('email')
        amount = float(data.get('amount'))
        description = data.get('description', 'Administrator recharge')
        
        # 验证金额
        if amount <= 0:
            return jsonify({
                'status': 'error',
                'message': '充值金额必须大于0'
            }), 400
        
        # 根据邮箱查找用户
        user_service = UserService()
        user = user_service.get_user_by_email(email)
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'未找到邮箱为 {email} 的用户'
            }), 404
        
        user_id = user.id
        balance_service = BalanceService()
        
        # 执行充值
        result = balance_service.charge_user_balance(
            user_id=user_id,
            amount=amount,
            description=description
        )
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': '充值失败'
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': '充值成功',
            'data': result
        })
    except Exception as e:
        logger.error(f"管理员充值失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'充值失败: {str(e)}'
        }), 500

# 保留原路由但调用工具函数
@bp.route('/check_analyze', methods=['POST'])
@login_required
def check_analyze_balance():
    """检查当前余额是否足够进行音频分析（API接口）"""
    try:
        data = request.json
        
        # 验证必要参数
        if 'task_id' not in data:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数: task_id'
            }), 400
        
        task_id = data['task_id']
        user_id = get_jwt_identity()
        model_size = data.get('model_size', 'base')
        
        try:
            is_sufficient, current_balance, estimated_cost, details = check_analyze_balance_for_task(
                task_id, user_id, model_size
            )
            
            return jsonify({
                "is_sufficient": is_sufficient,
                "current_balance": current_balance,
                "estimated_cost": estimated_cost,
                "details": details,
                "task_id": task_id
            })
            
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 404
        
    except Exception as e:
        logger.exception(f"检查余额失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/api/balance/check', methods=['POST'])
@login_required
def check_balance():
    """检查用户余额"""
    try:
        # 获取当前用户
        user = get_current_user()
        if not user:
            return jsonify({"error": "未找到用户信息"}), 404
            
        user_id = user['id']
        
        # 获取任务ID或文件大小
        data = request.get_json()
        task_id = data.get('task_id')
        file_size_mb = data.get('file_size_mb')
        audio_duration_minutes = data.get('audio_duration_minutes')
        
        # 如果提供了task_id，从任务中获取信息
        if task_id:
            # 在函数内部导入task_manager以避免循环导入
            from api.app import task_manager
            
            task = task_manager.get_task(task_id)
            if not task:
                return jsonify({"error": "任务不存在"}), 404
                
            file_size_mb = task.get('size_mb')
            audio_duration_minutes = task.get('audio_duration_minutes')
        
        # 如果仍然没有文件大小信息，返回错误
        if not file_size_mb:
            return jsonify({"error": "缺少文件大小信息"}), 400
            
        # 获取用户信息
        db_user = db_session.query(User).filter(User.id == user_id).first()
        if not db_user:
            return jsonify({"error": "未找到用户信息"}), 404
            
        # 检查余额
        balance_check = BalanceService.check_balance(
            user_id=user_id,
            file_size_mb=file_size_mb,
            audio_duration_minutes=audio_duration_minutes
        )
        
        return jsonify({
            "status": "success",
            "data": {
                "balance": float(db_user.balance),
                "required_balance": float(balance_check["required_balance"]),
                "is_sufficient": balance_check["is_sufficient"],
                "file_size_mb": file_size_mb,
                "audio_duration_minutes": audio_duration_minutes,
                "task_id": task_id if task_id else None
            }
        })
        
    except Exception as e:
        logger.exception(f"检查余额时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/api/balance/charge', methods=['POST'])
@login_required
def charge_balance():
    """充值余额"""
    try:
        # 获取当前用户
        user = get_current_user()
        if not user:
            return jsonify({"error": "未找到用户信息"}), 404
            
        user_id = user['id']
        
        # 获取充值金额
        data = request.get_json()
        amount = data.get('amount')
        
        if not amount or amount <= 0:
            return jsonify({"error": "无效的充值金额"}), 400
            
        # 执行充值
        result = BalanceService.charge_balance(user_id, amount)
        
        return jsonify({
            "status": "success",
            "data": {
                "balance": float(result["balance"]),
                "charged_amount": float(amount)
            }
        })
        
    except Exception as e:
        logger.exception(f"充值余额时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/api/balance/history', methods=['GET'])
@login_required
def get_balance_history():
    """获取余额变动历史"""
    try:
        # 获取当前用户
        user = get_current_user()
        if not user:
            return jsonify({"error": "未找到用户信息"}), 404
            
        user_id = user['id']
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 获取历史记录
        history = BalanceService.get_balance_history(
            user_id=user_id,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            "status": "success",
            "data": {
                "total": history["total"],
                "page": page,
                "per_page": per_page,
                "items": [
                    {
                        "id": record.id,
                        "amount": float(record.amount),
                        "type": record.type,
                        "description": record.description,
                        "created_at": record.created_at.isoformat()
                    }
                    for record in history["items"]
                ]
            }
        })
        
    except Exception as e:
        logger.exception(f"获取余额历史时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

