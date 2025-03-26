import logging
from flask import Blueprint, request, jsonify, current_app
from src.balance_system.services.pricing_service import PricingService
from api.auth import login_required, admin_required

logger = logging.getLogger(__name__)

bp = Blueprint('pricing_bp', __name__, url_prefix='/api/pricing')

@bp.route('/estimate', methods=['POST'])
@login_required
def estimate_cost():
    """
    预估处理费用
    
    请求参数:
        file_size_mb: 文件大小，单位MB
        model_size: 模型大小，如'tiny', 'base', 'small', 'medium', 'large'
        api_type: API类型，默认为'analysis'
    
    返回:
        预估费用和详细信息
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求数据格式错误"}), 400
        
        file_size_mb = data.get('file_size_mb')
        model_size = data.get('model_size')
        api_type = data.get('api_type', 'analysis')
        
        # 验证参数
        if file_size_mb is None:
            return jsonify({"success": False, "message": "缺少参数: file_size_mb"}), 400
        if model_size is None:
            return jsonify({"success": False, "message": "缺少参数: model_size"}), 400
        
        try:
            file_size_mb = float(file_size_mb)
        except ValueError:
            return jsonify({"success": False, "message": "file_size_mb必须为数字"}), 400
        
        # 预估费用
        result = PricingService.estimate_cost(file_size_mb, model_size, api_type)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        logger.error(f"预估费用失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": "服务器错误"}), 500

@bp.route('/models', methods=['GET'])
def get_all_models_pricing():
    """
    获取所有模型的定价预估
    
    查询参数:
        file_size_mb: 文件大小，单位MB
        api_type: API类型，默认为'analysis'
    
    返回:
        所有模型的预估费用
    """
    try:
        file_size_mb = request.args.get('file_size_mb')
        api_type = request.args.get('api_type', 'analysis')
        
        if file_size_mb is None:
            return jsonify({"success": False, "message": "缺少参数: file_size_mb"}), 400
        
        try:
            file_size_mb = float(file_size_mb)
        except ValueError:
            return jsonify({"success": False, "message": "file_size_mb必须为数字"}), 400
        
        # 获取所有模型的定价预估
        result = PricingService.get_all_model_pricing(file_size_mb, api_type)
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"获取模型定价失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": "服务器错误"}), 500

@bp.route('/rules', methods=['GET'])
def get_pricing_rules():
    """获取所有定价规则"""
    try:
        rules = PricingService.get_pricing_rules()
        
        return jsonify({
            "success": True,
            "data": rules
        })
    except Exception as e:
        logger.error(f"获取定价规则失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": "服务器错误"}), 500 