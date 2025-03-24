#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import tempfile
import atexit
import shutil
import time
import logging
from environment_manager import EnvironmentManager
from logging_config import LoggingConfig

# 获取模块的logger
logger = LoggingConfig.get_logger(__name__)

def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发环境和PyInstaller打包后的环境"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def setup_environment():
    """设置运行环境，确保必要组件可用"""
    logger.info("正在检查运行环境...")
    
    # 检查FFmpeg
    ffmpeg_ready = EnvironmentManager.check_ffmpeg()
    if not ffmpeg_ready:
        logger.warning("FFmpeg未安装，尝试使用内置版本...")
        # 尝试使用内置的ffmpeg
        ffmpeg_dir = resource_path("ffmpeg")
        if os.path.exists(ffmpeg_dir):
            if sys.platform.startswith('win'):
                ffmpeg_exe = os.path.join(ffmpeg_dir, "bin", "ffmpeg.exe")
            else:
                ffmpeg_exe = os.path.join(ffmpeg_dir, "bin", "ffmpeg")
                
            if os.path.exists(ffmpeg_exe):
                # 将ffmpeg添加到PATH
                os.environ["PATH"] = os.path.join(ffmpeg_dir, "bin") + os.pathsep + os.environ["PATH"]
                logger.info(f"已添加内置FFmpeg到环境变量: {ffmpeg_exe}")
                ffmpeg_ready = True
        
        if not ffmpeg_ready:
            logger.warning("尝试安装FFmpeg...")
            ffmpeg_ready = EnvironmentManager.install_ffmpeg()
    
    # 检查PyTorch（可选）
    try:
        import torch
        pytorch_ready = torch.cuda.is_available()
        if pytorch_ready:
            logger.info(f"✅ PyTorch可用，CUDA状态: {pytorch_ready}")
        else:
            logger.warning("⚠️ PyTorch可用，但CUDA不可用，将使用CPU模式")
    except ImportError:
        logger.warning("⚠️ PyTorch未安装，部分功能可能受限")
    
    return ffmpeg_ready

def cleanup(temp_dir):
    """清理临时文件夹"""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"已清理临时目录: {temp_dir}")
    except Exception as e:
        logger.error(f"清理临时目录时出错: {str(e)}")

def run_streamlit():
    """启动Streamlit应用"""
    logger.info("正在启动智能音频分割应用...")
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="audio_splitter_")
    atexit.register(cleanup, temp_dir)
    
    # 设置环境变量
    os.environ["TEMP_DIR"] = temp_dir
    
    # 当前脚本的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    # 确保app.py存在
    if not os.path.exists(app_path):
        app_path = resource_path("app.py")
    
    # 启动Streamlit
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.headless", "true", 
           "--browser.serverAddress", "localhost", "--server.port", "8501"]
    
    logger.info(f"执行命令: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    
    # 等待服务启动
    time.sleep(2)
    
    # 打开浏览器
    import webbrowser
    webbrowser.open("http://localhost:8501")
    
    try:
        # 等待进程结束
        process.wait()
    except KeyboardInterrupt:
        logger.info("应用程序被用户中断")
    finally:
        # 确保进程被终止
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
            if process.poll() is None:
                process.kill()

if __name__ == "__main__":
    # 初始化日志系统
    LoggingConfig.setup_logging(log_level=logging.INFO)
    
    # 检查并设置环境
    if not setup_environment():
        logger.error("环境配置失败，应用程序可能无法正常工作")
        sys.exit(1)
    
    # 运行Streamlit应用
    run_streamlit() 