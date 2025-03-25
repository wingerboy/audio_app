#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import uuid
import bcrypt
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理类，提供用户注册、验证、存储等功能"""
    
    def __init__(self, data_dir):
        """
        初始化用户管理器
        
        Args:
            data_dir: 用户数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化用户数据文件
        if not self.users_file.exists():
            self._save_users({})
            logger.info(f"创建新的用户数据文件: {self.users_file}")
    
    def _load_users(self):
        """载入用户数据"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户数据文件失败: {str(e)}")
            return {}
    
    def _save_users(self, users):
        """保存用户数据"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存用户数据文件失败: {str(e)}")
            return False
    
    def create_user(self, username, email, password):
        """
        创建新用户
        
        Args:
            username: 用户名
            email: 电子邮件
            password: 密码
            
        Returns:
            dict: 创建的用户信息（不含密码）或None（如果创建失败）
        """
        users = self._load_users()
        
        # 检查用户名或邮箱是否已存在
        for user_id, user in users.items():
            if user['username'].lower() == username.lower():
                logger.warning(f"用户名已存在: {username}")
                return None, "用户名已存在"
            if user['email'].lower() == email.lower():
                logger.warning(f"邮箱已存在: {email}")
                return None, "邮箱已存在"
        
        # 创建新用户
        user_id = str(uuid.uuid4())
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        new_user = {
            'id': user_id,
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': time.time(),
            'last_login': None
        }
        
        users[user_id] = new_user
        if not self._save_users(users):
            return None, "保存用户数据失败"
        
        # 返回用户信息（不含密码）
        user_info = dict(new_user)
        user_info.pop('password')
        return user_info, None
    
    def authenticate_user(self, email, password):
        """
        验证用户凭据
        
        Args:
            email: 电子邮件
            password: 密码
            
        Returns:
            dict: 用户信息（不含密码）或None（如果认证失败）
        """
        users = self._load_users()
        
        # 查找匹配邮箱的用户
        user = None
        for user_data in users.values():
            if user_data['email'].lower() == email.lower():
                user = user_data
                break
        
        if not user:
            logger.warning(f"用户不存在: {email}")
            return None, "用户名或密码不正确"
        
        # 验证密码
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            logger.warning(f"密码不正确: {email}")
            return None, "用户名或密码不正确"
        
        # 更新最后登录时间
        user['last_login'] = time.time()
        self._save_users(users)
        
        # 返回用户信息（不含密码）
        user_info = dict(user)
        user_info.pop('password')
        return user_info, None
    
    def get_user_by_id(self, user_id):
        """
        通过ID获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户信息（不含密码）或None（如果用户不存在）
        """
        users = self._load_users()
        
        if user_id not in users:
            return None
        
        # 返回用户信息（不含密码）
        user_info = dict(users[user_id])
        user_info.pop('password')
        return user_info
    
    def update_user(self, user_id, update_data):
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            update_data: 要更新的字段
            
        Returns:
            dict: 更新后的用户信息（不含密码）或None（如果更新失败）
        """
        users = self._load_users()
        
        if user_id not in users:
            return None
        
        user = users[user_id]
        
        # 不允许更新的字段
        forbidden_fields = ['id', 'created_at']
        
        # 更新密码需要特殊处理
        if 'password' in update_data:
            update_data['password'] = bcrypt.hashpw(
                update_data['password'].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
        
        # 更新字段
        for key, value in update_data.items():
            if key not in forbidden_fields:
                user[key] = value
        
        # 保存更新
        if not self._save_users(users):
            return None
        
        # 返回更新后的用户信息（不含密码）
        user_info = dict(user)
        user_info.pop('password')
        return user_info 