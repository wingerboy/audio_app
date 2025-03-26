from flask import Blueprint, request, jsonify, current_app
import logging
from flask_jwt_extended import get_jwt
from src.balance_system.services.balance_service import BalanceService
from src.balance_system.services.pricing_service import PricingService
from functools import wraps
from api.auth import admin_required, login_required, get_current_user

# 初始化日志
logger = logging.getLogger(__name__)

# 创建蓝图
bp = Blueprint('balance_bp', __name__, url_prefix='/api/balance')

@bp.route('/info', methods=['GET'])
@login_required
def get_balance_info():
    """获取当前用户的点数信息"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'status': 'error', 'message': '用户未认证'}), 401
            
        user_id = user['id']
        balance_service = BalanceService()
        
        # 检查点数是否过期
        balance_service.check_expired_balance(user_id)
        
        # 获取用户余额信息 (点数)
        balance_info = balance_service.get_user_balance(user_id)
        
        return jsonify({
            'status': 'success',
            'data': {
                'balance': balance_info['balance'],  # 点数余额
                'total_charged': balance_info['total_charged'],  # 总充值点数
                'total_consumed': balance_info['total_consumed'],  # 总消费点数
                'points_to_money': '100点=1元'  # 点数兑换比例
            }
        })
    except Exception as e:
        logger.error(f"获取点数信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取点数信息失败: {str(e)}'
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
@login_required
@admin_required
def admin_charge_balance():
    """管理员对用户账户充值"""
    try:
        data = request.json
        
        # 验证必要参数
        required_fields = ['user_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要参数: {field}'
                }), 400
        
        # 提取参数
        user_id = data.get('user_id')
        amount = float(data.get('amount'))
        description = data.get('description', '管理员充值')
        
        # 验证金额
        if amount <= 0:
            return jsonify({
                'status': 'error',
                'message': '充值金额必须大于0'
            }), 400
        
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

@bp.route('/check_analyze', methods=['POST'])
@login_required
def check_analyze_balance():
    """
    检查用户余额是否足够进行音频分析
    
    请求参数:
        file_size_mb: 文件大小，单位MB
        model_size: 模型大小，如'tiny', 'base', 'small', 'medium', 'large'
    
    返回:
        余额是否足够，预估费用
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据格式错误"}), 400
        
        file_size_mb = data.get('file_size_mb')
        model_size = data.get('model_size')
        
        # 验证参数
        if file_size_mb is None:
            return jsonify({"success": False, "message": "缺少参数: file_size_mb"}), 400
        if model_size is None:
            return jsonify({"success": False, "message": "缺少参数: model_size"}), 400
        
        try:
            file_size_mb = float(file_size_mb)
        except ValueError:
            return jsonify({"success": False, "message": "file_size_mb必须为数字"}), 400
        
        # 使用改进的get_current_user获取用户信息
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "用户未认证"}), 401
        
        # 直接从用户信息字典获取ID
        user_id = user['id']
        
        # 预估费用
        pricing_service = PricingService()
        cost_estimate = pricing_service.estimate_cost(file_size_mb, model_size)
        estimated_cost = cost_estimate["estimated_cost"]
        
        # 获取用户余额
        balance_service = BalanceService()
        user_balance = balance_service.get_user_balance(user_id)
        current_balance = user_balance["balance"]
        
        # 检查余额是否足够
        is_sufficient = current_balance >= estimated_cost
        
        return jsonify({
            "success": True,
            "data": {
                "is_sufficient": is_sufficient,
                "current_balance": current_balance,
                "estimated_cost": estimated_cost,
                "cost_details": cost_estimate["details"]
            }
        })
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"检查余额失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": "服务器错误"}), 500 