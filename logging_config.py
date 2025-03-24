#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import sys
from datetime import datetime

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
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志文件名，包含日期
        log_file = os.path.join(log_dir, f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log")
        
        # 根日志配置
        logger = logging.getLogger()
        logger.setLevel(log_level)
        
        # 清除已有的处理器，避免重复
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 详细的日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 详细的调试日志格式
        debug_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console = logging.StreamHandler(sys.stdout)
        if log_level <= logging.DEBUG:
            console.setFormatter(debug_formatter)
        else:
            console.setFormatter(formatter)
        logger.addHandler(console)
        
        # 文件处理器(可选)
        if log_to_file:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(debug_formatter)  # 文件中始终使用详细格式
            logger.addHandler(file_handler)
            
            # 添加一个错误日志文件处理器
            error_log_file = os.path.join(log_dir, f"{app_name}_errors_{datetime.now().strftime('%Y%m%d')}.log")
            error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
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
    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误信息") 