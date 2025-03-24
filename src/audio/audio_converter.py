#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import tempfile
from typing import Optional, Dict, Any, Union
from pathlib import Path

from .audio_utils import AudioUtils
from ..temp import TempFileManager

class AudioConverter:
    """音频转换器类"""
    
    def __init__(self):
        """初始化音频转换器"""
        self.logger = logging.getLogger(__name__)
    
    def extract_audio(self, file_path: str, output_format: str = "wav", 
                     temp_manager: Optional[TempFileManager] = None) -> str:
        """
        从音频或视频文件中提取音频
        
        Args:
            file_path: 输入文件路径
            output_format: 输出音频格式
            temp_manager: 临时文件管理器
            
        Returns:
            提取出的音频文件路径
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return ""
        
        # 使用传入的临时文件管理器或创建一个新的
        manager = temp_manager or TempFileManager(prefix="audio_converter_")
        
        try:
            # 获取文件名（不带扩展名）
            file_name = Path(file_path).stem
            
            # 创建输出文件路径
            output_path = manager.create_named_file(
                f"{file_name}_extracted", 
                suffix=f".{output_format}"
            )
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            self.logger.info(f"提取音频: {file_path} -> {output_path}")
            
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-i', file_path,           # 输入文件
                '-vn',                     # 禁用视频
                '-acodec', 'pcm_s16le',    # 音频编码器 (对于WAV)
                '-ar', '44100',            # 采样率
                '-ac', '2',                # 声道数
                '-y',                      # 覆盖已存在的文件
                output_path                # 输出文件
            ]
            
            # 如果输出格式不是WAV，使用适当的编码器
            if output_format.lower() != 'wav':
                if output_format.lower() == 'mp3':
                    cmd = [
                        'ffmpeg',
                        '-i', file_path,
                        '-vn',
                        '-acodec', 'libmp3lame',
                        '-q:a', '2',       # 音质设置 (0-9, 0最好)
                        '-y',
                        output_path
                    ]
                elif output_format.lower() == 'ogg':
                    cmd = [
                        'ffmpeg',
                        '-i', file_path,
                        '-vn',
                        '-acodec', 'libvorbis',
                        '-q:a', '4',       # 音质设置 (0-10, 10最好)
                        '-y',
                        output_path
                    ]
            
            # 执行命令
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 检查结果
            if result.returncode != 0:
                self.logger.error(f"提取音频失败: {result.stderr}")
                return ""
            
            # 检查输出文件是否存在
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                self.logger.error(f"提取音频失败，输出文件为空: {output_path}")
                return ""
            
            self.logger.info(f"成功提取音频: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.exception(f"提取音频时出错: {str(e)}")
            return "" 