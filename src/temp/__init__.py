#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .temp_file_manager import TempFileManager

# 创建一个全局的临时文件管理器实例
_global_manager = None

def get_global_manager():
    """
    获取全局临时文件管理器实例
    
    Returns:
        全局的TempFileManager实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = TempFileManager(prefix="global_temp_")
    return _global_manager

def cleanup_global_manager():
    """
    清理全局临时文件管理器
    """
    global _global_manager
    if _global_manager is not None:
        _global_manager.cleanup()
        _global_manager = None

__all__ = ['TempFileManager', 'get_global_manager', 'cleanup_global_manager'] 