#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import time
import wave
import contextlib
from pathlib import Path
from src.utils.logging_config import LoggingConfig

class AudioUtils:
    """音频处理常用工具函数集"""
    
    logger = LoggingConfig.get_logger(__name__)
    
    @staticmethod
    def get_audio_duration(file_path):
        """
        获取音频文件时长
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            float: 音频时长（秒），如果出错则返回-1
        """
        if not os.path.exists(file_path):
            AudioUtils.logger.error(f"文件不存在: {file_path}")
            return -1
        
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        try:
            # 针对WAV文件使用wave模块
            if ext == '.wav':
                with contextlib.closing(wave.open(file_path, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames / float(rate)
                    return duration
            
            # 其他格式使用FFmpeg
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                file_path
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                try:
                    return float(process.stdout.strip())
                except (ValueError, TypeError):
                    AudioUtils.logger.error(f"无法解析音频时长: {process.stdout}")
                    return -1
            else:
                AudioUtils.logger.error(f"获取音频时长失败: {process.stderr}")
                return -1
                
        except Exception as e:
            AudioUtils.logger.exception(f"获取音频时长时出错: {str(e)}")
            return -1
    
    @staticmethod
    def is_valid_audio_file(file_path):
        """
        检查音频文件是否有效
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            bool: 是否为有效音频文件
        """
        if not os.path.exists(file_path):
            return False
        
        try:
            # 使用FFprobe检查文件是否为有效音频
            cmd = [
                "ffprobe", 
                "-v", "error", 
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type", 
                "-of", "default=noprint_wrappers=1:nokey=1", 
                file_path
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # 检查FFprobe是否成功找到音频流
            return process.returncode == 0 and "audio" in process.stdout.strip()
                
        except Exception as e:
            AudioUtils.logger.error(f"检查音频文件有效性时出错: {str(e)}")
            return False
    
    @staticmethod
    def ensure_valid_filename(filename):
        """
        确保文件名有效（移除非法字符）
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 有效的文件名
        """
        # 替换Windows和Unix系统上的非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # 限制长度
        max_length = 220  # 留一些余量给路径和扩展名
        if len(filename) > max_length:
            base, ext = os.path.splitext(filename)
            base = base[:max_length - len(ext) - 3] + "..."
            filename = base + ext
            
        return filename
    
    @staticmethod
    def format_time(seconds):
        """
        格式化时间（秒）为人类可读格式
        
        Args:
            seconds: 秒数
            
        Returns:
            str: 格式化的时间字符串 (HH:MM:SS)
        """
        if seconds < 0:
            return "00:00:00"
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def parse_time_str(time_str):
        """
        解析时间字符串为秒数
        
        Args:
            time_str: 时间字符串 (HH:MM:SS 或 MM:SS)
            
        Returns:
            float: 秒数，如果格式无效则返回-1
        """
        try:
            parts = time_str.split(":")
            
            if len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 1:  # SS
                return float(parts[0])
            else:
                AudioUtils.logger.error(f"无效的时间格式: {time_str}")
                return -1
                
        except (ValueError, IndexError) as e:
            AudioUtils.logger.error(f"解析时间字符串出错: {time_str}, {str(e)}")
            return -1
    
    @staticmethod
    def detect_silence(audio_path, noise_threshold_db=-50, min_silence_len=1000):
        """
        检测音频中的静音片段
        
        Args:
            audio_path: 音频文件路径
            noise_threshold_db: 噪声阈值（dB）
            min_silence_len: 最小静音长度（毫秒）
            
        Returns:
            list: 静音片段列表，每个元素为 (start_ms, end_ms) 元组
        """
        try:
            from pydub import AudioSegment
            from pydub.silence import detect_silence
            
            # 加载音频
            audio = AudioSegment.from_file(audio_path)
            
            # 检测静音
            silence_ranges = detect_silence(
                audio, 
                min_silence_len=min_silence_len, 
                silence_thresh=noise_threshold_db
            )
            
            # 转换为秒
            silence_ranges_sec = [(start/1000, end/1000) for start, end in silence_ranges]
            
            return silence_ranges_sec
            
        except Exception as e:
            AudioUtils.logger.error(f"检测静音时出错: {str(e)}")
            return []
    
    @staticmethod
    def estimate_speech_rate(text, duration):
        """
        估计语速
        
        Args:
            text: 文本内容
            duration: 音频时长（秒）
            
        Returns:
            float: 估计的语速（字/分钟）
        """
        if duration <= 0:
            return 0
            
        # 去除标点符号和空白
        import re
        clean_text = re.sub(r'[^\w\s]', '', text)
        clean_text = clean_text.replace(' ', '')
        
        # 计算字符数
        char_count = len(clean_text)
        
        # 计算语速（字/分钟）
        speech_rate = char_count / (duration / 60)
        
        return speech_rate 