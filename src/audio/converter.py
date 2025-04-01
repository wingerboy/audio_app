#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import shutil
from pathlib import Path
from src.utils.logging_config import LoggingConfig
from ..temp.manager import TempFileManager

class AudioConverter:
    """音频格式转换器，负责检测和转换音频格式"""
    
    # 音频和视频格式列表
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus']
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.3gp', '.m4v', '.ts', '.mts', '.vob']
    
    def __init__(self):
        """初始化音频转换器"""
        self.logger = LoggingConfig.get_logger(__name__)
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检查FFmpeg是否已安装"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            self.has_ffmpeg = (result.returncode == 0)
            if self.has_ffmpeg:
                self.logger.debug("FFmpeg已安装")
            else:
                self.logger.warning("FFmpeg似乎已安装但返回错误")
        except FileNotFoundError:
            self.has_ffmpeg = False
            self.logger.warning("FFmpeg未安装或不在PATH中")
        except Exception as e:
            self.has_ffmpeg = False
            self.logger.error(f"检查FFmpeg时出错: {str(e)}")
    
    def is_audio_file(self, file_path):
        """
        检查文件是否为音频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为音频文件
        """
        if not os.path.exists(file_path):
            return False
        
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.AUDIO_EXTENSIONS
    
    def is_video_file(self, file_path):
        """
        检查文件是否为视频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为视频文件
        """
        if not os.path.exists(file_path):
            return False
        
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.VIDEO_EXTENSIONS
    
    def is_media_file(self, file_path):
        """
        检查文件是否为媒体文件（音频或视频）
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为媒体文件
        """
        return self.is_audio_file(file_path) or self.is_video_file(file_path)
    
    def extract_audio(self, file_path, output_format="wav", temp_manager=None):
        """
        从媒体文件中提取音频
        
        Args:
            file_path: 媒体文件路径
            output_format: 输出音频格式
            temp_manager: 临时文件管理器，如果为None则创建新的
            
        Returns:
            str: 输出音频文件路径，如果失败则返回None
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        # 检查是否需要创建临时文件管理器
        own_temp_manager = temp_manager is None
        if own_temp_manager:
            temp_manager = TempFileManager(prefix="audio_convert_")
        
        try:
            file_basename = os.path.basename(file_path)
            file_name, file_ext = os.path.splitext(file_basename)
            
            # 如果已经是音频文件且格式匹配，直接返回
            if self.is_audio_file(file_path) and file_ext.lower() == f".{output_format}":
                self.logger.info(f"文件已经是{output_format}格式，无需转换")
                # 复制到临时位置
                output_path = temp_manager.create_named_file(file_name, f".{output_format}")
                shutil.copy2(file_path, output_path)
                return output_path
            
            # 为输出创建临时文件路径
            output_path = temp_manager.create_named_file(file_name, f".{output_format}")
            
            # 检查是否可以使用FFmpeg
            if not self.has_ffmpeg:
                self.logger.error("FFmpeg未安装，无法处理媒体文件")
                return None
            
            # 根据文件类型选择合适的处理方式
            if self.is_audio_file(file_path):
                self.logger.info(f"转换音频格式: {file_ext} -> .{output_format}")
                return self._convert_audio(file_path, output_path, output_format)
            elif self.is_video_file(file_path):
                self.logger.info(f"从视频中提取音频: {file_ext} -> .{output_format}")
                return self._extract_audio_from_video(file_path, output_path, output_format)
            else:
                self.logger.error(f"不支持的文件类型: {file_ext}")
                return None
                
        except Exception as e:
            self.logger.exception(f"处理文件时出错: {str(e)}")
            return None
        finally:
            # 如果我们创建了临时管理器，需要确保正确清理
            if own_temp_manager:
                temp_manager.cleanup()
    
    def _convert_audio(self, input_path, output_path, output_format):
        """
        转换音频格式
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            output_format: 输出格式
            
        Returns:
            str: 输出文件路径，如果失败则返回None
        """
        try:
            # 针对不同格式选择合适的编码器和参数
            codec_map = {
                "mp3": "libmp3lame -q:a 2", 
                "wav": "pcm_s16le",  
                "ogg": "libvorbis -q:a 4",  
                "flac": "flac",
                "aac": "aac -strict experimental -b:a 192k",
                "m4a": "aac -strict experimental -b:a 192k"
            }
            
            codec = codec_map.get(output_format, "copy")
            
            # 构建基本命令
            cmd = ["ffmpeg", "-i", input_path]
            
            # 添加编码器参数
            codec_parts = codec.split()
            cmd.extend(["-c:a"] + codec_parts)
            
            # 设置采样率等参数
            cmd.extend([
                "-ar", "44100",  # 设置采样率
                "-y",  # 覆盖输出文件
                output_path
            ])
            
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 执行转换
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                self.logger.error(f"转换失败: {process.stderr}")
                return None
            
            if not os.path.exists(output_path):
                self.logger.error("转换后的文件不存在")
                return None
                
            self.logger.info(f"音频转换成功: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.exception(f"转换音频时出错: {str(e)}")
            return None
    
    def _extract_audio_from_video(self, input_path, output_path, output_format):
        """
        从视频中提取音频
        
        Args:
            input_path: 输入视频文件路径
            output_path: 输出音频文件路径
            output_format: 输出格式
            
        Returns:
            str: 输出文件路径，如果失败则返回None
        """
        try:
            # 根据输出格式选择合适的参数
            if output_format == "wav":
                cmd = [
                    "ffmpeg", "-i", input_path, 
                    "-vn",  # 不要视频
                    "-acodec", "pcm_s16le",  # 使用PCM编码
                    "-ar", "44100",  # 采样率
                    "-ac", "2",  # 双声道
                    "-y",  # 覆盖输出文件
                    output_path
                ]
            elif output_format == "mp3":
                cmd = [
                    "ffmpeg", "-i", input_path, 
                    "-vn",  # 不要视频
                    "-acodec", "libmp3lame",  # 使用LAME MP3编码器
                    "-q:a", "2",  # 质量设置
                    "-ar", "44100",  # 采样率
                    "-ac", "2",  # 双声道
                    "-y",  # 覆盖输出文件
                    output_path
                ]
            else:
                # 其他格式使用一般参数
                cmd = [
                    "ffmpeg", "-i", input_path, 
                    "-vn",  # 不要视频
                    "-ar", "44100",  # 采样率
                    "-ac", "2",  # 双声道
                    "-y",  # 覆盖输出文件
                    output_path
                ]
            
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            
            # 执行提取
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                self.logger.error(f"提取失败: {process.stderr}")
                return None
            
            if not os.path.exists(output_path):
                self.logger.error("提取后的文件不存在")
                return None
                
            self.logger.info(f"音频提取成功: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.exception(f"从视频提取音频时出错: {str(e)}")
            return None
    
    def get_audio_info(self, audio_path):
        """
        获取音频文件信息
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            dict: 音频信息，包含格式、时长、比特率、通道数等
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"文件不存在: {audio_path}")
            return {}
        
        try:
            # 使用FFprobe获取媒体信息
            cmd = [
                "ffprobe", 
                "-v", "quiet", 
                "-print_format", "json", 
                "-show_format", 
                "-show_streams", 
                audio_path
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode != 0:
                self.logger.error(f"获取音频信息失败: {process.stderr}")
                return {}
            
            # 解析JSON输出
            import json
            data = json.loads(process.stdout)
            
            # 提取关键信息
            info = {}
            
            # 格式信息
            if "format" in data:
                format_data = data["format"]
                info["format"] = format_data.get("format_name", "unknown")
                info["duration"] = float(format_data.get("duration", 0))
                info["size"] = int(format_data.get("size", 0))
                info["bit_rate"] = int(format_data.get("bit_rate", 0))
            
            # 音频流信息
            if "streams" in data:
                for stream in data["streams"]:
                    if stream.get("codec_type") == "audio":
                        info["codec"] = stream.get("codec_name", "unknown")
                        info["sample_rate"] = int(stream.get("sample_rate", 0))
                        info["channels"] = int(stream.get("channels", 0))
                        info["channel_layout"] = stream.get("channel_layout", "unknown")
                        break
            
            return info
            
        except Exception as e:
            self.logger.exception(f"获取音频信息时出错: {str(e)}")
            return {} 