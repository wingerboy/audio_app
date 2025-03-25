#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, 
    get_jwt_identity, 
    verify_jwt_in_request,
    JWTManager
)

logger = logging.getLogger(__name__)

def setup_jwt(app):
    """
    配置JWT认证
    
    Args:
        app: Flask应用实例
    """
    # 设置JWT密钥
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)  # 令牌过期时间
    
    # 初始化JWT管理器
    jwt = JWTManager(app)
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'status': 'error',
            'message': '令牌已过期，请重新登录',
            'code': 'token_expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'status': 'error',
            'message': '无效的身份令牌',
            'code': 'invalid_token'
        }), 401
    
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        return jsonify({
            'status': 'error',
            'message': '请先登录',
            'code': 'login_required'
        }), 401
    
    return jwt

def login_required(func):
    """
    需要登录装饰器
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"认证失败: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '请先登录',
                'code': 'login_required'
            }), 401
    return decorated_function

def admin_required(func):
    """
    需要管理员权限装饰器
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # 检查用户是否为管理员
            from models import UserManager
            user_manager = current_app.config['USER_MANAGER']
            user = user_manager.get_user_by_id(user_id)
            
            if not user or not user.get('is_admin', False):
                logger.warning(f"用户 {user_id} 尝试访问管理员资源但无权限")
                return jsonify({
                    'status': 'error',
                    'message': '需要管理员权限',
                    'code': 'admin_required'
                }), 403
                
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"认证失败: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': '请先登录',
                'code': 'login_required'
            }), 401
    return decorated_function

def generate_token(user_id):
    """
    生成JWT访问令牌
    
    Args:
        user_id: 用户ID
    
    Returns:
        str: JWT访问令牌
    """
    return create_access_token(identity=user_id)

def get_current_user():
    """
    获取当前登录用户信息
    
    Returns:
        dict: 用户信息或None
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        # 获取用户信息
        from models import UserManager
        user_manager = current_app.config['USER_MANAGER']
        return user_manager.get_user_by_id(user_id)
    except Exception:
        return None 