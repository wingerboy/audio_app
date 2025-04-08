#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
import threading
from datetime import datetime
import time
from typing import Optional, Dict, Any

# 线程本地存储，用于保存当前请求的上下文信息
_thread_local = threading.local()

class RequestContext:
    """请求上下文管理器，用于在日志中包含用户和任务相关信息"""
    
    @staticmethod
    def set_context(user_id: Optional[str] = None, task_id: Optional[str] = None, **kwargs) -> None:
        """
        设置当前线程的上下文信息
        
        Args:
            user_id: 用户ID
            task_id: 任务ID
            kwargs: 其他上下文信息
        """
        if not hasattr(_thread_local, 'context'):
            _thread_local.context = {}
        
        if user_id:
            _thread_local.context['user_id'] = user_id
        if task_id:
            _thread_local.context['task_id'] = task_id
        
        # 添加其他上下文信息
        for key, value in kwargs.items():
            _thread_local.context[key] = value
    
    @staticmethod
    def get_context() -> Dict[str, Any]:
        """
        获取当前线程的上下文信息
        
        Returns:
            包含上下文信息的字典
        """
        if not hasattr(_thread_local, 'context'):
            _thread_local.context = {}
        return _thread_local.context
    
    @staticmethod
    def clear_context() -> None:
        """清除当前线程的上下文信息"""
        if hasattr(_thread_local, 'context'):
            _thread_local.context = {}

class ContextFilter(logging.Filter):
    """日志过滤器，用于添加上下文信息到日志记录"""
    
    def filter(self, record):
        # 获取当前上下文信息
        context = RequestContext.get_context()
        
        # 添加上下文信息到日志记录
        record.user_id = context.get('user_id', '-')
        record.task_id = context.get('task_id', '-')
        
        # 添加其他上下文信息
        for key, value in context.items():
            if key not in ('user_id', 'task_id'):
                setattr(record, key, value)
        
        return True

class LoggingConfig:
    """日志系统配置类，统一管理应用中的日志配置"""
    
    @staticmethod
    def setup_logging(log_level=logging.DEBUG, log_to_file=True, app_name="audio_app"):
        """
        配置日志系统
        
        Args:
            log_level: 日志级别，默认DEBUG
            log_to_file: 是否保存日志到文件，默认True
            app_name: 应用名称，用于日志文件命名
            
        Returns:
            logger: 配置好的根日志记录器
        """
        # 创建日志目录
        log_dir = "/app/logs"  # 使用Docker容器中的固定路径
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置时区
        os.environ['TZ'] = 'Asia/Shanghai'
        try:
            time.tzset()  # 应用时区设置
        except AttributeError:
            # Windows系统不支持tzset
            pass
        
        # 设置日志文件名，包含日期
        log_file = os.path.join(log_dir, f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log")
        
        # 根日志配置
        logger = logging.getLogger()
        logger.setLevel(log_level)
        
        # 清除已有的处理器，避免重复
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 创建上下文过滤器
        context_filter = ContextFilter()
        
        # 详细的日志格式，包含用户ID和任务ID
        formatter = logging.Formatter(
            '%(asctime)s - [User:%(user_id)s] [Task:%(task_id)s] - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 详细的调试日志格式
        debug_formatter = logging.Formatter(
            '%(asctime)s - [User:%(user_id)s] [Task:%(task_id)s] - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console = logging.StreamHandler(sys.stdout)
        console.addFilter(context_filter)
        if log_level <= logging.DEBUG:
            console.setFormatter(debug_formatter)
        else:
            console.setFormatter(formatter)
        logger.addHandler(console)
        
        # 文件处理器(可选)
        if log_to_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.addFilter(context_filter)
            file_handler.setFormatter(debug_formatter)  # 文件中始终使用详细格式
            logger.addHandler(file_handler)
            
            # 添加一个错误日志文件处理器
            error_log_file = os.path.join(log_dir, f"{app_name}_errors_{datetime.now().strftime('%Y%m%d')}.log")
            error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
            error_handler.addFilter(context_filter)
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(debug_formatter)
            logger.addHandler(error_handler)
        
        logger.info(f"日志系统初始化完成，日志文件: {log_file}")
        return logger
    
    @staticmethod
    def get_logger(name):
        """
        获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称，通常为模块名 __name__
            
        Returns:
            logger: 指定名称的日志记录器
        """
        return logging.getLogger(name)
    
    @staticmethod
    def create_streamlit_handler():
        """
        创建Streamlit日志处理器，用于将日志消息发送到Streamlit界面
        
        Returns:
            handler: 自定义的Streamlit日志处理器
        """
        import streamlit as st
        
        class StreamlitHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    level = record.levelname
                    
                    # 根据日志级别使用不同的Streamlit函数
                    if level == 'DEBUG':
                        # 调试信息不在UI中显示
                        pass
                    elif level == 'INFO':
                        st.info(msg)
                    elif level == 'WARNING':
                        st.warning(msg)
                    elif level == 'ERROR':
                        st.error(msg)
                    elif level == 'CRITICAL':
                        st.error(f"严重错误: {msg}")
                except Exception:
                    self.handleError(record)
        
        return StreamlitHandler()

if __name__ == "__main__":
    # 测试日志配置
    logger = LoggingConfig.setup_logging(log_level=logging.DEBUG)
    
    # 测试上下文功能
    RequestContext.set_context(user_id="test_user_123", task_id="test_task_456")
    logger.debug("这是带有上下文的调试信息")
    logger.info("这是带有上下文的普通信息")
    logger.warning("这是带有上下文的警告信息")
    logger.error("这是带有上下文的错误信息")
    
    # 清除上下文
    RequestContext.clear_context()
    logger.info("这是没有上下文的信息")
    
    # 设置新的上下文
    RequestContext.set_context(user_id="another_user", task_id="another_task")
    logger.info("这是新上下文的信息") 