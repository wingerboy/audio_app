from flask import Blueprint, request, jsonify, current_app
import logging
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from src.balance_system.services.balance_service import BalanceService
from src.balance_system.services.pricing_service import PricingService
from functools import wraps

# 初始化日志
logger = logging.getLogger(__name__)

# 创建蓝图
bp = Blueprint('balance_bp', __name__, url_prefix='/api/balance')

def admin_required(f):
    """需要管理员权限的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        claims = get_jwt()
        if not claims.get('is_admin'):
            return jsonify({'message': '需要管理员权限'}), 403
        return f(*args, **kwargs)
    return decorated

@bp.route('/info', methods=['GET'])
@jwt_required()
def get_balance_info():
    """获取当前用户的余额信息"""
    try:
        user_id = get_jwt_identity()
        balance_service = BalanceService()
        
        # 获取用户余额信息
        balance_info = balance_service.get_user_balance(user_id)
        
        return jsonify({
            'status': 'success',
            'data': balance_info
        })
    except Exception as e:
        logger.error(f"获取余额信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取余额信息失败: {str(e)}'
        }), 500

@bp.route('/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    """获取用户交易记录"""
    try:
        user_id = get_jwt_identity()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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
@jwt_required()
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