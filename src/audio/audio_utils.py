#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import subprocess
import logging
import tempfile
from typing import Dict, Any, Optional, Union
from pydub import AudioSegment

class AudioUtils:
    """音频处理工具类"""
    
    @staticmethod
    def load_audio(audio_path: str) -> AudioSegment:
        """
        加载音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            AudioSegment对象
        """
        logger = logging.getLogger(__name__)
        logger.info(f"加载音频文件: {audio_path}")
        
        # 获取文件扩展名
        _, ext = os.path.splitext(audio_path)
        format = ext.strip('.').lower()
        
        # 加载音频
        if not format or format not in ['mp3', 'wav', 'ogg', 'flac', 'm4a']:
            # 如果扩展名不支持，默认使用WAV格式
            logger.warning(f"未识别的音频格式: {format}，尝试作为WAV加载")
            format = 'wav'
        
        try:
            audio = AudioSegment.from_file(audio_path, format=format)
            logger.info(f"成功加载音频: {len(audio)/1000:.2f}秒, {audio.channels}声道, {audio.frame_rate}Hz")
            return audio
        except Exception as e:
            logger.exception(f"加载音频失败: {str(e)}")
            # 尝试直接加载，让pydub自动检测格式
            try:
                audio = AudioSegment.from_file(audio_path)
                logger.info(f"使用自动检测成功加载音频: {len(audio)/1000:.2f}秒")
                return audio
            except Exception as e2:
                logger.exception(f"使用自动检测加载音频也失败: {str(e2)}")
                raise RuntimeError(f"无法加载音频文件: {audio_path}") from e2
    
    @staticmethod
    def get_audio_info(audio_path: str) -> Dict[str, Any]:
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            包含音频信息的字典
        """
        logger = logging.getLogger(__name__)
        
        try:
            # 使用FFmpeg获取音频信息
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                  '-show_format', '-show_streams', audio_path]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                data = eval(result.stdout.replace('null', 'None').replace('true', 'True').replace('false', 'False'))
                
                # 解析结果
                info = {}
                
                # 基本信息
                if 'format' in data:
                    info['format'] = data['format'].get('format_name', '')
                    info['duration'] = float(data['format'].get('duration', 0))
                    info['size'] = int(data['format'].get('size', 0))
                    info['bit_rate'] = int(data['format'].get('bit_rate', 0))
                
                # 流信息
                if 'streams' in data and data['streams']:
                    audio_stream = next((s for s in data['streams'] if s.get('codec_type') == 'audio'), None)
                    if audio_stream:
                        info['codec'] = audio_stream.get('codec_name', '')
                        info['sample_rate'] = int(audio_stream.get('sample_rate', 0))
                        info['channels'] = int(audio_stream.get('channels', 0))
                
                logger.info(f"音频信息: {info}")
                return info
                
            except (subprocess.SubprocessError, ValueError) as e:
                logger.warning(f"使用FFprobe获取音频信息失败: {str(e)}")
                
                # 回退方法：使用pydub加载音频获取基本信息
                audio = AudioUtils.load_audio(audio_path)
                return {
                    'duration': len(audio) / 1000,  # 秒
                    'channels': audio.channels,
                    'sample_rate': audio.frame_rate,
                    'bit_rate': audio.frame_rate * audio.sample_width * audio.channels * 8
                }
                
        except Exception as e:
            logger.exception(f"获取音频信息失败: {str(e)}")
            # 返回一个空字典，而不是抛出异常
            return {}
    
    @staticmethod
    def make_safe_filename(text: str) -> str:
        """
        将文本转换为安全的文件名
        
        Args:
            text: 输入文本
            
        Returns:
            安全的文件名
        """
        # 移除不安全的字符
        safe_text = re.sub(r'[^\w\s.-]', '', text)
        # 将空白替换为下划线
        safe_text = re.sub(r'\s+', '_', safe_text)
        # 确保不超过255个字符
        safe_text = safe_text[:255]
        # 移除开头的点号
        safe_text = safe_text.lstrip('.')
        return safe_text 