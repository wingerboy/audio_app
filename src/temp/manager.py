#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
import logging
from pathlib import Path
from src.utils.logging_config import LoggingConfig

class TempFileManager:
    """
    临时文件管理器，负责创建和清理临时文件
    使用上下文管理器模式，确保资源正确释放
    """
    
    def __init__(self, prefix="audio_", parent_dir=None, cleanup_on_exit=True):
        """
        初始化临时文件管理器
        
        Args:
            prefix: 临时文件/目录前缀
            parent_dir: 父目录，如果为None则使用系统临时目录
            cleanup_on_exit: 退出时是否自动清理
        """
        self.logger = LoggingConfig.get_logger(__name__)
        self.prefix = prefix
        self.cleanup_on_exit = cleanup_on_exit
        self.files = []
        self.dirs = []
        
        # 创建父临时目录
        if parent_dir:
            self.parent_dir = parent_dir
            os.makedirs(self.parent_dir, exist_ok=True)
        else:
            self.parent_dir = tempfile.gettempdir()
        
        # 创建一个基础临时目录，所有临时文件将在此目录下
        self.base_dir = os.path.join(
            self.parent_dir, 
            f"{self.prefix}{next(tempfile._get_candidate_names())}"
        )
        os.makedirs(self.base_dir, exist_ok=True)
        self.dirs.append(self.base_dir)
        
        self.logger.debug(f"临时文件管理器初始化，基础目录: {self.base_dir}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，自动清理资源"""
        if self.cleanup_on_exit:
            self.cleanup()
    
    def create_file(self, suffix=".tmp", content=None, dir=None):
        """
        创建临时文件
        
        Args:
            suffix: 文件后缀
            content: 文件内容，如果不为None则写入文件
            dir: 创建目录，默认为基础临时目录
            
        Returns:
            str: 临时文件路径
        """
        target_dir = dir if dir else self.base_dir
        
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix=self.prefix,
            dir=target_dir
        )
        os.close(fd)
        
        # 如果有内容，写入文件
        if content is not None:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 记录文件用于清理
        self.files.append(temp_path)
        self.logger.debug(f"创建临时文件: {temp_path}")
        
        return temp_path
    
    def create_named_file(self, name, suffix=".tmp", content=None, dir=None):
        """
        创建命名临时文件
        
        Args:
            name: 文件名（不含后缀）
            suffix: 文件后缀
            content: 文件内容，如果不为None则写入文件
            dir: 创建目录，默认为基础临时目录
            
        Returns:
            str: 临时文件路径
        """
        target_dir = dir if dir else self.base_dir
        temp_path = os.path.join(target_dir, f"{name}{suffix}")
        
        # 如果有内容，写入文件
        if content is not None:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # 创建空文件
            open(temp_path, 'a').close()
        
        # 记录文件用于清理
        self.files.append(temp_path)
        self.logger.debug(f"创建命名临时文件: {temp_path}")
        
        return temp_path
    
    def create_dir(self, suffix=""):
        """
        创建临时目录
        
        Args:
            suffix: 目录后缀
            
        Returns:
            str: 临时目录路径
        """
        dir_name = f"{self.prefix}{next(tempfile._get_candidate_names())}{suffix}"
        temp_dir = os.path.join(self.base_dir, dir_name)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 记录目录用于清理
        self.dirs.append(temp_dir)
        self.logger.debug(f"创建临时目录: {temp_dir}")
        
        return temp_dir
    
    def create_named_dir(self, name):
        """
        创建命名临时目录
        
        Args:
            name: 目录名
            
        Returns:
            str: 临时目录路径
        """
        temp_dir = os.path.join(self.base_dir, name)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 记录目录用于清理
        self.dirs.append(temp_dir)
        self.logger.debug(f"创建命名临时目录: {temp_dir}")
        
        return temp_dir
    
    def add_external_file(self, file_path):
        """
        添加外部文件到管理器，以便自动清理
        
        Args:
            file_path: 文件路径
        """
        if os.path.exists(file_path):
            self.files.append(file_path)
            self.logger.debug(f"添加外部文件: {file_path}")
    
    def add_external_dir(self, dir_path):
        """
        添加外部目录到管理器，以便自动清理
        
        Args:
            dir_path: 目录路径
        """
        if os.path.exists(dir_path):
            self.dirs.append(dir_path)
            self.logger.debug(f"添加外部目录: {dir_path}")
    
    def cleanup(self):
        """清理所有临时文件和目录"""
        # 首先清理文件
        for file_path in self.files[:]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"清理临时文件: {file_path}")
                self.files.remove(file_path)
            except Exception as e:
                self.logger.warning(f"清理文件失败 {file_path}: {str(e)}")
        
        # 然后清理目录（倒序清理，确保子目录先被清理）
        for dir_path in sorted(self.dirs, reverse=True):
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                    self.logger.debug(f"清理临时目录: {dir_path}")
                self.dirs.remove(dir_path)
            except Exception as e:
                self.logger.warning(f"清理目录失败 {dir_path}: {str(e)}")
        
        self.logger.debug("所有临时文件和目录已清理")
    
    def get_base_dir(self):
        """获取基础临时目录"""
        return self.base_dir
    
    def get_all_files(self):
        """获取所有临时文件的列表"""
        return self.files.copy()
    
    @staticmethod
    def get_system_temp_dir():
        """获取系统临时目录"""
        return tempfile.gettempdir()


# 单例模式，应用可以选择使用全局临时文件管理器
_global_manager = None

def get_global_manager(create_if_none=True):
    """
    获取全局临时文件管理器
    
    Args:
        create_if_none: 如果不存在是否创建
        
    Returns:
        TempFileManager: 全局管理器实例
    """
    global _global_manager
    if _global_manager is None and create_if_none:
        _global_manager = TempFileManager(prefix="global_")
    return _global_manager

def cleanup_global_manager():
    """清理全局临时文件管理器"""
    global _global_manager
    if _global_manager is not None:
        _global_manager.cleanup()
        _global_manager = None 