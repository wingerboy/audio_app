#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import subprocess
import logging
import tempfile
import wave
import contextlib
from typing import Dict, Any, Optional, Union
from pathlib import Path

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

class AudioUtils:
    """音频处理工具类"""
    
    logger = logging.getLogger(__name__)
    
    @staticmethod
    def load_audio(audio_path: str) -> Any:
        """加载音频文件"""
        if not PYDUB_AVAILABLE:
            AudioUtils.logger.error("未安装pydub库，无法加载音频")
            raise RuntimeError("未安装pydub库，无法加载音频")
            
        AudioUtils.logger.info(f"加载音频文件: {audio_path}")
        
        # 获取文件扩展名
        _, ext = os.path.splitext(audio_path)
        format = ext.strip('.').lower()
        
        # 加载音频
        if not format or format not in ['mp3', 'wav', 'ogg', 'flac', 'm4a']:
            # 如果扩展名不支持，默认使用WAV格式
            AudioUtils.logger.warning(f"未识别的音频格式: {format}，尝试作为WAV加载")
            format = 'wav'
        
        try:
            audio = AudioSegment.from_file(audio_path, format=format)
            AudioUtils.logger.info(f"成功加载音频: {len(audio)/1000:.2f}秒, {audio.channels}声道, {audio.frame_rate}Hz")
            return audio
        except Exception as e:
            AudioUtils.logger.exception(f"加载音频失败: {str(e)}")
            # 尝试直接加载，让pydub自动检测格式
            try:
                audio = AudioSegment.from_file(audio_path)
                AudioUtils.logger.info(f"使用自动检测成功加载音频: {len(audio)/1000:.2f}秒")
                return audio
            except Exception as e2:
                AudioUtils.logger.exception(f"使用自动检测加载音频也失败: {str(e2)}")
                raise RuntimeError(f"无法加载音频文件: {audio_path}") from e2
    
    @staticmethod
    def get_audio_duration(audio_path: str) -> float:
        """获取音频文件的时长（秒）"""
        AudioUtils.logger.info(f"获取音频时长: {audio_path}")
        
        if not os.path.exists(audio_path):
            AudioUtils.logger.error(f"文件不存在: {audio_path}")
            return 0.0
        
        # 获取文件大小以便在所有方法失败时提供估算
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
            
        # 根据文件扩展名确定格式
        _, ext = os.path.splitext(audio_path)
        format = ext.strip('.').lower()
        
        # 记录并跟踪所有尝试的方法和错误
        errors = []
        
        # 尝试使用wave模块读取WAV文件
        if format == 'wav':
            try:
                with contextlib.closing(wave.open(audio_path, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames / float(rate)
                    AudioUtils.logger.info(f"使用wave模块获取到WAV文件时长: {duration:.2f}秒")
                    return duration
            except Exception as e:
                error_msg = f"使用wave模块获取WAV文件时长失败: {str(e)}"
                AudioUtils.logger.warning(error_msg)
                errors.append(error_msg)
        
        # 尝试使用pydub获取时长
        if PYDUB_AVAILABLE:
            try:
                audio = AudioSegment.from_file(audio_path)
                duration = len(audio) / 1000.0  # pydub以毫秒为单位
                AudioUtils.logger.info(f"使用pydub获取到音频时长: {duration:.2f}秒")
                return duration
            except Exception as e:
                error_msg = f"使用pydub获取音频时长失败: {str(e)}"
                AudioUtils.logger.warning(error_msg)
                errors.append(error_msg)
        
        # 尝试使用ffprobe获取时长
        try:
            cmd = [
                'ffprobe', 
                '-i', audio_path,
                '-show_entries', 'format=duration',
                '-v', 'quiet',
                '-of', 'csv=p=0'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                try:
                    duration = float(result.stdout.strip())
                    AudioUtils.logger.info(f"使用ffprobe获取到音频时长: {duration:.2f}秒")
                    return duration
                except ValueError as e:
                    error_msg = f"ffprobe返回的时长无法转换为浮点数: {result.stdout.strip()}, 错误: {str(e)}"
                    AudioUtils.logger.warning(error_msg)
                    errors.append(error_msg)
            else:
                error_msg = f"ffprobe返回非零状态码或空输出: {result.returncode}, 输出: {result.stdout}"
                AudioUtils.logger.warning(error_msg)
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"使用ffprobe获取音频时长失败: {str(e)}"
            AudioUtils.logger.warning(error_msg)
            errors.append(error_msg)
        
        # 尝试使用mediainfo工具（如果可用）
        try:
            cmd = ['mediainfo', '--Output=General;%Duration%', audio_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                try:
                    # mediainfo返回的是毫秒
                    duration = float(result.stdout.strip()) / 1000.0
                    AudioUtils.logger.info(f"使用mediainfo获取到音频时长: {duration:.2f}秒")
                    return duration
                except ValueError:
                    AudioUtils.logger.warning(f"mediainfo返回的时长无法转换为浮点数: {result.stdout.strip()}")
        except (FileNotFoundError, subprocess.SubprocessError):
            # mediainfo可能不可用，忽略此错误
            AudioUtils.logger.debug("mediainfo工具不可用，跳过")
        
        # 所有方法都失败，根据文件大小估算
        estimated_duration = max(1.0, file_size_mb * 3)  # 假设每MB约3秒音频
        AudioUtils.logger.warning(f"所有方法获取音频时长失败，根据文件大小估算: {estimated_duration:.2f}秒 ({file_size_mb:.2f}MB)")
        AudioUtils.logger.debug(f"失败原因: {'; '.join(errors)}")
        
        return estimated_duration
    
    @staticmethod
    def get_audio_info(audio_path: str) -> Dict[str, Any]:
        """获取音频文件信息，包括时长、采样率、通道数等"""
        AudioUtils.logger.info(f"获取音频信息: {audio_path}")
        
        if not os.path.exists(audio_path):
            AudioUtils.logger.error(f"文件不存在: {audio_path}")
            raise FileNotFoundError(f"文件不存在: {audio_path}")
        
        info = {
            "path": audio_path,
            "exists": True,
            "size_bytes": os.path.getsize(audio_path),
            "size_mb": os.path.getsize(audio_path) / (1024 * 1024),
            "duration": 0.0,
            "sample_rate": 0,
            "channels": 0,
            "format": os.path.splitext(audio_path)[1].strip('.').lower()
        }
        
        # 尝试使用wave模块获取WAV文件信息
        if info["format"] == 'wav':
            try:
                with contextlib.closing(wave.open(audio_path, 'r')) as f:
                    info["channels"] = f.getnchannels()
                    info["sample_width"] = f.getsampwidth()
                    info["sample_rate"] = f.getframerate()
                    frames = f.getnframes()
                    info["duration"] = frames / float(info["sample_rate"])
                    AudioUtils.logger.info(f"使用wave模块获取到WAV文件信息: {info}")
                    return info
            except Exception as e:
                AudioUtils.logger.warning(f"使用wave模块获取WAV文件信息失败: {str(e)}")
        
        # 尝试使用pydub获取音频信息
        if PYDUB_AVAILABLE:
            try:
                audio = AudioUtils.load_audio(audio_path)
                info["duration"] = len(audio) / 1000.0  # pydub以毫秒为单位
                info["sample_rate"] = audio.frame_rate
                info["channels"] = audio.channels
                info["sample_width"] = audio.sample_width
                AudioUtils.logger.info(f"使用pydub获取到音频信息: {info}")
                return info
            except Exception as e:
                AudioUtils.logger.warning(f"使用pydub获取音频信息失败: {str(e)}")
        
        # 尝试使用ffprobe获取音频信息
        try:
            AudioUtils.logger.info(f"尝试使用ffprobe获取音频信息: {audio_path}")
            cmd = [
                'ffprobe', 
                '-i', audio_path,
                '-show_entries', 'format=duration,size : stream=sample_rate,channels',
                '-v', 'quiet',
                '-of', 'json'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                try:
                    import json
                    data = json.loads(result.stdout)
                    
                    if 'format' in data and 'duration' in data['format']:
                        info["duration"] = float(data['format']['duration'])
                    
                    if 'streams' in data and len(data['streams']) > 0:
                        audio_stream = None
                        # 查找音频流
                        for stream in data['streams']:
                            if 'codec_type' in stream and stream['codec_type'] == 'audio':
                                audio_stream = stream
                                break
                        
                        if audio_stream:
                            if 'sample_rate' in audio_stream:
                                info["sample_rate"] = int(audio_stream['sample_rate'])
                            if 'channels' in audio_stream:
                                info["channels"] = int(audio_stream['channels'])
                    
                    AudioUtils.logger.info(f"使用ffprobe获取到音频信息: {info}")
                    return info
                except json.JSONDecodeError as e:
                    AudioUtils.logger.warning(f"解析ffprobe输出失败: {str(e)}")
                except Exception as e:
                    AudioUtils.logger.warning(f"处理ffprobe输出时出错: {str(e)}")
                    
        except Exception as e:
            AudioUtils.logger.warning(f"使用ffprobe获取音频信息失败: {str(e)}")
        
        # 至少确保获取时长
        if info["duration"] == 0:
            info["duration"] = AudioUtils.get_audio_duration(audio_path)
        
        if info["duration"] > 0:
            AudioUtils.logger.info(f"获取到部分音频信息: {info}")
            return info
        
        AudioUtils.logger.error(f"无法获取任何音频信息: {audio_path}")
        raise RuntimeError(f"无法获取音频信息: {audio_path}")
    
    @staticmethod
    def make_safe_filename(text: str) -> str:
        """将文本转换为安全的文件名"""
        # 移除不安全的字符
        safe_text = re.sub(r'[^\w\s.-]', '', text)
        # 将空白替换为下划线
        safe_text = re.sub(r'\s+', '_', safe_text)
        # 确保不超过255个字符
        safe_text = safe_text[:255]
        # 移除开头的点号
        safe_text = safe_text.lstrip('.')
        return safe_text
    
    @staticmethod
    def is_valid_audio_file(file_path: str) -> bool:
        """检查音频文件是否有效"""
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