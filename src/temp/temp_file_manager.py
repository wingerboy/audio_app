#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
import shutil
import tempfile
import logging
from typing import List, Optional, Dict, Any


class TempFileManager:
    """临时文件管理器"""

    def __init__(self, base_dir: Optional[str] = None, prefix: str = "temp_"):
        """
        初始化临时文件管理器
        
        Args:
            base_dir: 临时文件基础目录，默认使用系统临时目录
            prefix: 临时文件前缀
        """
        self.logger = logging.getLogger(__name__)
        
        # 如果没有指定基础目录，使用系统临时目录
        self.base_dir = base_dir or tempfile.gettempdir()
        self.prefix = prefix
        
        # 确保基础目录存在
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            
        # 在基础目录下创建唯一的会话目录
        self.session_id = str(uuid.uuid4())
        self.session_dir = os.path.join(self.base_dir, f"{self.prefix}{self.session_id}")
        os.makedirs(self.session_dir, exist_ok=True)
        
        self.logger.debug(f"创建临时会话目录: {self.session_dir}")
        
        # 跟踪创建的所有临时文件
        self.temp_files: List[str] = []
    
    def create_temp_file(self, suffix: str = "", prefix: Optional[str] = None) -> str:
        """
        创建临时文件
        
        Args:
            suffix: 文件后缀
            prefix: 文件前缀，默认使用类初始化时指定的前缀
            
        Returns:
            临时文件的路径
        """
        file_prefix = prefix or self.prefix
        
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=file_prefix, dir=self.session_dir)
        # 关闭文件描述符
        os.close(fd)
        
        # 添加到跟踪列表
        self.temp_files.append(temp_path)
        
        self.logger.debug(f"创建临时文件: {temp_path}")
        return temp_path
    
    def create_named_file(self, name: str, suffix: str = "") -> str:
        """
        创建命名临时文件
        
        Args:
            name: 文件名
            suffix: 文件后缀
            
        Returns:
            命名临时文件的路径
        """
        # 生成文件路径
        safe_name = name.replace(os.path.sep, "_")  # 确保文件名没有路径分隔符
        temp_path = os.path.join(self.session_dir, f"{safe_name}{suffix}")
        
        # 创建空文件
        with open(temp_path, 'w') as f:
            pass
        
        # 添加到跟踪列表
        self.temp_files.append(temp_path)
        
        self.logger.debug(f"创建命名临时文件: {temp_path}")
        return temp_path
    
    def create_temp_dir(self, suffix: str = "", prefix: Optional[str] = None) -> str:
        """
        创建临时目录
        
        Args:
            suffix: 目录后缀
            prefix: 目录前缀，默认使用类初始化时指定的前缀
            
        Returns:
            临时目录的路径
        """
        dir_prefix = prefix or self.prefix
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=dir_prefix, dir=self.session_dir)
        
        # 添加到跟踪列表
        self.temp_files.append(temp_dir)
        
        self.logger.debug(f"创建临时目录: {temp_dir}")
        return temp_dir
    
    def remove_file(self, file_path: str) -> bool:
        """
        删除临时文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            删除是否成功
        """
        if file_path in self.temp_files:
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                    
                self.temp_files.remove(file_path)
                self.logger.debug(f"删除临时文件: {file_path}")
                return True
            except Exception as e:
                self.logger.error(f"删除临时文件失败: {file_path}, 错误: {str(e)}")
                return False
        else:
            self.logger.warning(f"尝试删除非托管的临时文件: {file_path}")
            return False
    
    def cleanup(self) -> None:
        """清理所有临时文件"""
        self.logger.debug(f"清理临时文件会话: {self.session_dir}")
        
        # 清理所有临时文件
        files_to_clean = list(self.temp_files)  # 创建副本以避免在循环中修改
        for file_path in files_to_clean:
            self.remove_file(file_path)
        
        # 最后尝试清理会话目录
        try:
            if os.path.exists(self.session_dir):
                shutil.rmtree(self.session_dir)
                self.logger.debug(f"删除临时会话目录: {self.session_dir}")
        except Exception as e:
            self.logger.error(f"删除临时会话目录失败: {self.session_dir}, 错误: {str(e)}")
    
    def __del__(self):
        """析构函数，确保清理临时文件"""
        try:
            self.cleanup()
        except:
            pass  # 忽略在析构函数中的错误 