#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Union
import tempfile
import time

# 添加 PyAV 导入和可用性检查
try:
    import av
    PYAV_AVAILABLE = True
except ImportError:
    PYAV_AVAILABLE = False
from ..temp import TempFileManager

class AudioConverter:
    """音频转换器类"""
    
    # 音频和视频格式列表
    AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus']
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.3gp', '.m4v']
    
    def __init__(self):
        """初始化音频转换器"""
        self.logger = logging.getLogger(__name__)
        self._check_ffmpeg()
        if PYAV_AVAILABLE:
            self.logger.info("PyAV 可用，将优先使用 PyAV 提取音频")
        else:
            self.logger.info("PyAV 不可用，将使用 FFmpeg 命令行提取音频")
    
    def _check_ffmpeg(self):
        """检查FFmpeg是否已安装"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            self.has_ffmpeg = (result.returncode == 0)
        except FileNotFoundError:
            self.has_ffmpeg = False
            self.logger.warning("FFmpeg未安装或不在PATH中")
        except Exception as e:
            self.has_ffmpeg = False
            self.logger.error(f"检查FFmpeg时出错: {str(e)}")
    
    def is_audio_file(self, file_path):
        """检查文件是否为音频文件"""
        if not os.path.exists(file_path):
            return False
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.AUDIO_EXTENSIONS
    
    def is_video_file(self, file_path):
        """检查文件是否为视频文件"""
        if not os.path.exists(file_path):
            return False
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.VIDEO_EXTENSIONS
    
    def extract_audio(self, file_path: str, output_format: str = "wav", 
                     temp_manager: Optional[TempFileManager] = None,
                     output_path: Optional[str] = None,
                     use_disk_processing: bool = False,
                     chunk_size_mb: int = 100) -> str:
        """从音频或视频文件中提取音频
        
        Args:
            file_path: 输入文件路径
            output_format: 输出音频格式 (wav/mp3/ogg)
            temp_manager: 临时文件管理器
            output_path: 指定输出路径，如果为None则使用临时文件
            use_disk_processing: 是否使用磁盘处理（对大文件更友好）
            chunk_size_mb: 处理大文件时的分块大小(MB)
            
        Returns:
            提取的音频文件路径，如果失败则返回None
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        # 获取输入文件信息
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # 决定是否为大文件 (>100MB)
        is_large_file = file_size_mb > 100
        
        # 对大文件，强制使用磁盘处理
        if is_large_file:
            use_disk_processing = True
            self.logger.info(f"检测到大文件 ({file_size_mb:.2f}MB)，启用磁盘处理模式")
        
        self.logger.info(f"提取音频: {file_path} -> {output_format} (大小: {file_size_mb:.2f}MB, 磁盘处理: {use_disk_processing})")
        
        # 确定输出文件路径
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
        else:
            # 如果未指定输出路径，使用临时文件
            if temp_manager:
                output_path = temp_manager.get_temp_file(suffix=f".{output_format}")
            else:
                # 使用python内置的临时文件机制
                output_dir = os.path.join(tempfile.gettempdir(), f"audio_converter_{int(time.time())}")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"extracted_audio.{output_format}")
        
        # 获取文件类型
        input_format = os.path.splitext(file_path)[1].lower().strip('.')
        self.logger.info(f"输入文件格式: {input_format}")
        
        # 如果输入已经是指定的音频格式，可以直接复制
        audio_formats = {'mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac'}
        if input_format in audio_formats and input_format == output_format:
            self.logger.info(f"输入文件已经是 {output_format} 格式，直接复制")
            shutil.copy2(file_path, output_path)
            return output_path
        
        # 优先使用PyAV提取音频（更高效）
        try:
            # 大文件或明确指定使用磁盘处理时使用FFmpeg直接处理
            if use_disk_processing or is_large_file:
                return self._extract_with_ffmpeg(file_path, output_path, output_format, chunk_size_mb)
            else:
                # 尝试使用PyAV处理
                if self._extract_with_pyav(file_path, output_path, output_format):
                    return output_path
                
                # 如果PyAV失败，回退到pydub
                self.logger.warning("PyAV提取失败，尝试使用pydub")
                if self._extract_with_pydub(file_path, output_path, output_format):
                    return output_path
                
                # 如果pydub也失败，回退到FFmpeg
                self.logger.warning("pydub提取失败，尝试使用FFmpeg")
                return self._extract_with_ffmpeg(file_path, output_path, output_format, chunk_size_mb)
        except Exception as e:
            self.logger.exception(f"提取音频失败: {str(e)}")
            
            # 如果出现任何错误，尝试使用FFmpeg作为最后的备选方案
            try:
                self.logger.info("尝试使用FFmpeg作为备选方案")
                return self._extract_with_ffmpeg(file_path, output_path, output_format, chunk_size_mb)
            except Exception as e2:
                self.logger.exception(f"使用FFmpeg提取音频也失败: {str(e2)}")
                return None
    
    def _extract_with_ffmpeg(self, input_path: str, output_path: str, output_format: str = "wav",
                           chunk_size_mb: int = 100) -> str:
        """使用FFmpeg直接提取音频，适合大文件处理"""
        self.logger.info(f"使用FFmpeg提取音频: {input_path} -> {output_path}")
        
        try:
            # 准备FFmpeg命令
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-vn",  # 禁用视频
                "-acodec", self._get_codec_for_format(output_format)
            ]
            
            # 根据输出格式添加相应参数
            if output_format == "mp3":
                cmd.extend(["-b:a", "192k"])
            elif output_format == "wav":
                cmd.extend(["-ar", "44100"])
            
            # 添加输出路径
            cmd.append(output_path)
            
            # 确保安静模式
            cmd.extend(["-y", "-v", "quiet"])
            
            # 执行命令
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
            
            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                self.logger.error(f"提取失败: {output_path} 不存在或为空")
                return None
            
            output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            self.logger.info(f"音频提取成功: {output_path} ({output_size_mb:.2f}MB)")
            return output_path
            
        except Exception as e:
            self.logger.exception(f"FFmpeg提取音频失败: {str(e)}")
            return None
    
    def _extract_with_pyav(self, file_path: str, output_path: str, output_format: str) -> bool:
        """使用 PyAV 提取音频"""
        try:
            # 打开输入文件
            self.logger.debug(f"使用 PyAV 打开文件: {file_path}")
            input_container = av.open(file_path)
            
            # 检查是否有音频流
            audio_stream = None
            for stream in input_container.streams:
                if stream.type == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                self.logger.warning(f"文件中没有音频流: {file_path}")
                return False
            
            self.logger.debug(f"找到音频流: 编码={audio_stream.codec_context.name}, "
                             f"采样率={audio_stream.sample_rate}, 声道数={audio_stream.channels}")
            
            # 创建输出容器
            output_container = av.open(output_path, mode='w')
            
            # 配置输出格式和编码器
            codec_name = self._get_codec_for_format(output_format)
            
            # 添加音频流到输出容器
            output_stream = output_container.add_stream(codec_name)
            output_stream.channels = audio_stream.channels
            output_stream.sample_rate = audio_stream.sample_rate
            
            # 设置质量
            if output_format == 'mp3':
                # 对于MP3设置比特率
                output_stream.bit_rate = 192000  # 192 kbps
            
            # 对于WAV设置采样格式
            if output_format == 'wav':
                output_stream.options = {'sample_fmt': 's16'}
            
            # 执行转码
            total_frames = 0
            for frame in input_container.decode(audio_stream):
                total_frames += 1
                # 编码帧并写入输出容器
                for packet in output_stream.encode(frame):
                    output_container.mux(packet)
                    
                # 记录进度（每100帧记录一次）
                if total_frames % 100 == 0:
                    self.logger.debug(f"已处理 {total_frames} 帧音频")
            
            # 刷新剩余帧
            for packet in output_stream.encode(None):
                output_container.mux(packet)
            
            # 关闭容器
            output_container.close()
            input_container.close()
            
            # 验证输出文件
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                self.logger.error(f"输出文件为空: {output_path}")
                return False
                
            self.logger.info(f"使用 PyAV 成功提取了 {total_frames} 帧音频到: {output_path}")
            return True
        
        except Exception as e:
            self.logger.exception(f"PyAV 提取音频失败: {str(e)}")
            return False
    
    def _get_codec_for_format(self, output_format: str) -> str:
        """根据输出格式获取适当的音频编码器"""
        format_codec_map = {
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'ogg': 'libvorbis',
            'aac': 'aac',
            'flac': 'flac',
        }
        return format_codec_map.get(output_format.lower(), 'copy')