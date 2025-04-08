#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Union

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
                     temp_manager: Optional[TempFileManager] = None) -> str:
        """从音频或视频文件中提取音频"""
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return ""
        
        # 使用传入的临时文件管理器或创建一个新的
        manager = temp_manager or TempFileManager(prefix="audio_converter_")
        
        try:
            # 如果已经是音频文件且格式匹配，考虑直接返回
            if self.is_audio_file(file_path) and file_path.lower().endswith(f".{output_format}"):
                self.logger.info(f"文件已经是{output_format}格式，无需转换")
                output_path = manager.create_named_file(Path(file_path).stem, f".{output_format}")
                shutil.copy2(file_path, output_path)
                return output_path
                
            # 创建输出文件路径
            file_name = Path(file_path).stem
            output_path = manager.create_named_file(f"{file_name}_extracted", suffix=f".{output_format}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            self.logger.info(f"提取音频: {file_path} -> {output_path}")
            
            # 优先使用 PyAV 提取音频
            if PYAV_AVAILABLE:
                success = self._extract_with_pyav(file_path, output_path, output_format)
                if success:
                    self.logger.info(f"使用 PyAV 成功提取音频: {output_path}")
                    return output_path
                else:
                    self.logger.warning("PyAV 提取失败，回退到 FFmpeg 命令行方式")
            
            # 如果 PyAV 不可用或提取失败，回退到 FFmpeg 命令行
            success = self._extract_with_ffmpeg(file_path, output_path, output_format)
            if success:
                self.logger.info(f"使用 FFmpeg 成功提取音频: {output_path}")
                return output_path
            else:
                self.logger.error("音频提取失败")
                return ""
            
        except Exception as e:
            self.logger.exception(f"提取音频时出错: {str(e)}")
            return ""
    
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
    
    def _extract_with_ffmpeg(self, file_path: str, output_path: str, output_format: str) -> bool:
        """使用 FFmpeg 命令行提取音频（备选方法）"""
        try:
            # 选择适当的编码器和参数
            codec_params = []
            if output_format.lower() == 'wav':
                codec_params = ['-acodec', 'pcm_s16le']
            elif output_format.lower() == 'mp3':
                codec_params = ['-acodec', 'libmp3lame', '-q:a', '2']
            elif output_format.lower() == 'ogg':
                codec_params = ['-acodec', 'libvorbis', '-q:a', '4']
            else:
                codec_params = ['-acodec', 'copy']  # 默认复制音频流
                
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-i', file_path,       # 输入文件
                '-vn',                 # 禁用视频
                *codec_params,         # 音频编码器参数
                '-ar', '44100',        # 采样率
                '-ac', '2',            # 声道数
                '-y',                  # 覆盖已存在的文件
                output_path            # 输出文件
            ]
            
            # 执行命令
            self.logger.debug(f"执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 检查结果
            if result.returncode != 0:
                self.logger.error(f"FFmpeg 提取音频失败: {result.stderr}")
                return False
            
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                self.logger.error(f"输出文件为空: {output_path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.exception(f"FFmpeg 提取音频失败: {str(e)}")
            return False