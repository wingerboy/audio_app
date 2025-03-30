import logging
from flask import Blueprint, request, jsonify, current_app
from src.balance_system.services.pricing_service import PricingService
from api.auth import login_required, admin_required

logger = logging.getLogger(__name__)

bp = Blueprint('pricing_bp', __name__, url_prefix='/api/pricing')

@bp.route('/estimate', methods=['POST'])
@login_required
def estimate_cost():
    """估算处理费用"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "缺少请求数据"}), 400
            
        # 获取参数
        file_size_mb = data.get('file_size_mb')
        model_size = data.get('model_size', 'base')
        task_id = data.get('task_id')  # 添加task_id参数
        audio_duration_minutes = data.get('audio_duration_minutes')
        
        # 验证参数
        if not file_size_mb and not task_id:
            return jsonify({"error": "缺少必要参数file_size_mb或task_id"}), 400
            
        # 如果提供了task_id，从task中获取信息
        if task_id:
            from app import tasks
            if task_id not in tasks:
                return jsonify({"error": "任务不存在"}), 404
                
            task = tasks[task_id]
            file_size_mb = task.get('size_mb')
            audio_duration_minutes = task.get('audio_duration_minutes')
            
        # 估算费用
        cost_info = PricingService.estimate_cost(
            file_size_mb=file_size_mb, 
            model_size=model_size,
            audio_duration_minutes=audio_duration_minutes
        )
        
        # 获取当前用户ID
        user_id = get_jwt_identity()
        
        return jsonify({
            "user_id": user_id,
            "file_size_mb": file_size_mb,
            "model_size": model_size,
            "audio_duration_minutes": cost_info["details"]["audio_duration_minutes"],
            "estimated_cost": cost_info["estimated_cost"],
            "details": cost_info["details"],
            "task_id": task_id  # 返回task_id
        })
        
    except Exception as e:
        logger.exception(f"估算费用失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/models', methods=['GET'])
def get_model_pricing():
    """获取模型定价信息"""
    try:
        # 获取查询参数
        file_size_mb = request.args.get('file_size_mb', type=float)
        audio_duration_minutes = request.args.get('audio_duration_minutes', type=float)
        
        if not file_size_mb:
            return jsonify({"error": "缺少必要参数file_size_mb"}), 400
        
        # 获取所有模型的预估价格
        pricing_data = PricingService.get_all_model_pricing(
            file_size_mb=file_size_mb,
            audio_duration_minutes=audio_duration_minutes
        )
        
        return jsonify(pricing_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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