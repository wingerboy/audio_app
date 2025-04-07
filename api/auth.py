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
from src.balance_system.models.user import User
from src.balance_system.db import get_db_session

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
            with get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if not user or not user.is_admin():
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
        dict: 包含用户信息的字典，如果未登录则返回None
    """
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        # 获取用户信息
        with get_db_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None
                
            # 返回用户信息字典而不是ORM对象
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_admin': user.is_admin(),
                'role': user.role,
                'role_name': user.get_role_name(),
                'balance': float(user.balance) if user.balance else 0.0,
                'total_charged': float(user.total_charged) if user.total_charged else 0.0,
                'total_consumed': float(user.total_consumed) if user.total_consumed else 0.0,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
    except Exception as e:
        logger.warning(f"获取当前用户失败: {str(e)}")
        return None

def agent_required(func):
    """
    需要代理权限装饰器（允许代理或管理员访问）
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # 检查用户是否为代理或管理员
            with get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if not user or (not user.is_agent() and not user.is_admin() and not user.is_senior_agent()):
                    logger.warning(f"用户 {user_id} 尝试访问代理资源但无权限")
                    return jsonify({
                        'status': 'error',
                        'message': '需要代理权限',
                        'code': 'agent_required'
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

def admin_or_agent_required(func):
    """
    需要管理员或任何级别代理权限的装饰器
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # 检查用户是否为管理员或代理
            with get_db_session() as session:
                user = session.query(User).filter_by(id=user_id).first()
                
                if not user or user.role == 0:  # 普通用户无权限
                    logger.warning(f"用户 {user_id} 尝试访问管理或代理资源但无权限")
                    return jsonify({
                        'status': 'error',
                        'message': '需要管理员或代理权限',
                        'code': 'admin_or_agent_required'
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