from flask import Blueprint, request, jsonify, current_app
import logging
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.balance_system.services.api_usage_service import ApiUsageService

# 初始化日志
logger = logging.getLogger(__name__)

# 创建蓝图
bp = Blueprint('usage_bp', __name__, url_prefix='/api/usage')

@bp.route('/record', methods=['POST'])
@jwt_required()
def record_api_usage():
    """记录API使用情况"""
    try:
        user_id = get_jwt_identity()
        data = request.json
        
        # 验证必要参数
        required_fields = ['api_type', 'task_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必要参数: {field}'
                }), 400
        
        # 提取参数
        api_type = data.get('api_type')
        task_id = data.get('task_id')
        model_size = data.get('model_size')
        duration = data.get('duration') # 秒
        file_size = data.get('file_size') # MB
        cost = data.get('cost')
        description = data.get('description', '')
        
        # 创建服务实例
        api_usage_service = ApiUsageService()
        
        # 记录API使用
        result = api_usage_service.record_api_usage(
            user_id=user_id,
            api_type=api_type,
            task_id=task_id,
            model_size=model_size,
            duration=duration,
            file_size=file_size,
            cost=cost,
            description=description
        )
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': '记录API使用失败'
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': '记录API使用成功',
            'data': result
        })
    except Exception as e:
        logger.error(f"记录API使用失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'记录API使用失败: {str(e)}'
        }), 500

@bp.route('/history', methods=['GET'])
@jwt_required()
def get_api_usage_history():
    """获取API使用历史记录"""
    try:
        user_id = get_jwt_identity()
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        # 创建服务实例
        api_usage_service = ApiUsageService()
        
        # 获取使用历史
        usage_records, total = api_usage_service.get_user_api_usage(
            user_id=user_id,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'status': 'success',
            'data': {
                'records': usage_records,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })
    except Exception as e:
        logger.error(f"获取API使用历史失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取API使用历史失败: {str(e)}'
        }), 500

@bp.route('/stats', methods=['GET'])
@jwt_required()
def get_api_usage_stats():
    """获取API使用统计信息"""
    try:
        user_id = get_jwt_identity()
        
        # 创建服务实例
        api_usage_service = ApiUsageService()
        
        # 获取统计信息
        stats = api_usage_service.get_usage_statistics(user_id=user_id)
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        logger.error(f"获取API使用统计失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取API使用统计失败: {str(e)}'
        }), 500 