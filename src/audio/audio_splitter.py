import os
import tempfile
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Callable, Dict, Any, Optional

from .audio_utils import AudioUtils
from ..temp import TempFileManager

@dataclass
class SegmentOptions:
    """音频片段选项"""
    start: float = 0.0  # 开始时间 (秒)
    end: float = 0.0    # 结束时间 (秒)
    text: str = ""      # 片段文本内容

@dataclass
class SplitOptions:
    """音频分割选项"""
    
    def __init__(self, output_format="mp3", quality="medium"):
        """
        初始化分割选项
        
        Args:
            output_format: 输出格式 (mp3, wav, ogg)
            quality: 输出质量 (low, medium, high)
        """
        self.output_format = output_format
        self.quality = quality
    
    def get_format_options(self) -> Dict[str, Any]:
        """获取格式特定的选项"""
        if self.output_format == "mp3":
            # MP3 质量选项
            quality_map = {
                "low": {"bitrate": "96k"},
                "medium": {"bitrate": "192k"},
                "high": {"bitrate": "320k"}
            }
            return quality_map.get(self.quality, quality_map["medium"])
            
        elif self.output_format == "wav":
            # WAV 质量选项 (采样率)
            quality_map = {
                "low": {"sample_rate": 22050},
                "medium": {"sample_rate": 44100},
                "high": {"sample_rate": 48000}
            }
            return quality_map.get(self.quality, quality_map["medium"])
            
        elif self.output_format == "ogg":
            # OGG 质量选项
            quality_map = {
                "low": {"quality": 3},
                "medium": {"quality": 6},
                "high": {"quality": 9}
            }
            return quality_map.get(self.quality, quality_map["medium"])
            
        else:
            # 默认使用中等质量
            return {}

class AudioSplitter:
    """音频分割器类"""
    
    def __init__(self, max_workers=2):
        """
        初始化音频分割器
        
        Args:
            max_workers (int): 最大并行工作线程数
        """
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
    
    def _split_segment(self, audio_file, segment_options, output_file, split_options):
        """
        分割单个音频片段
        
        Args:
            audio_file: 音频文件路径
            segment_options: 分段选项
            output_file: 输出文件路径
            split_options: 分割选项
            
        Returns:
            分割是否成功
        """
        try:
            start_time = segment_options.start
            end_time = segment_options.end
            
            self.logger.debug(f"分割音频片段: {start_time:.2f}s - {end_time:.2f}s -> {output_file}")
            
            # 加载音频文件
            self.logger.debug(f"加载音频文件: {audio_file}")
            audio_segment = AudioUtils.load_audio(audio_file)
            
            # 计算时间点（毫秒）
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            
            # 提取片段
            self.logger.debug(f"提取音频片段: {start_ms}ms - {end_ms}ms")
            extract = audio_segment[start_ms:end_ms]
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 根据输出格式和质量导出
            format_type = split_options.output_format.lower()
            
            self.logger.debug(f"导出音频片段为 {format_type} 格式: {output_file}")
            
            # 根据格式和质量选择导出参数
            if format_type == 'mp3':
                bitrate = '64k'  # 默认中等质量
                if split_options.quality == 'low':
                    bitrate = '32k'
                elif split_options.quality == 'high':
                    bitrate = '192k'
                
                extract.export(output_file, format="mp3", bitrate=bitrate)
                
            elif format_type == 'wav':
                # WAV通常不压缩，质量设置主要影响采样率
                parameters = []
                if split_options.quality == 'low':
                    parameters = ["-ar", "22050"]  # 降低采样率
                elif split_options.quality == 'high':
                    parameters = ["-ar", "48000"]  # 提高采样率
                
                extract.export(output_file, format="wav", parameters=parameters)
                
            elif format_type == 'ogg':
                quality = '5'  # 默认中等质量 (0-10)
                if split_options.quality == 'low':
                    quality = '3'
                elif split_options.quality == 'high':
                    quality = '8'
                
                extract.export(output_file, format="ogg", quality=quality)
                
            else:
                # 默认其他格式
                extract.export(output_file, format=format_type)
            
            # 验证导出是否成功
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                self.logger.error(f"导出失败: 输出文件 {output_file} 不存在或为空")
                return False
            
            file_size = os.path.getsize(output_file) / 1024  # KB
            self.logger.info(f"成功导出音频片段: {output_file} ({file_size:.2f} KB)")
            return True
            
        except Exception as e:
            self.logger.exception(f"分割音频片段失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def split(self, audio_file, segment_options_list, output_dir, options=None, on_progress=None):
        """
        按照给定的时间段列表分割音频文件
        
        Args:
            audio_file: 要分割的音频文件路径
            segment_options_list: 分段选项列表
            output_dir: 输出目录
            options: 分割选项
            on_progress: 进度回调函数 (current, total) -> None
            
        Returns:
            生成的分段文件路径列表
        """
        self.logger.info(f"开始分割音频文件: {audio_file}")
        self.logger.info(f"输出目录: {output_dir}")
        self.logger.info(f"分段数量: {len(segment_options_list)}")
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_file):
            self.logger.error(f"音频文件不存在: {audio_file}")
            return []
        
        try:
            # 获取音频信息
            audio_info = AudioUtils.get_audio_info(audio_file)
            self.logger.info(f"音频信息: 时长={audio_info.get('duration', 'unknown')}秒, "
                            f"格式={audio_info.get('format', 'unknown')}, "
                            f"比特率={audio_info.get('bit_rate', 'unknown')}")
            audio_duration = float(audio_info.get('duration', 0))
            
            # 验证输出目录
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    self.logger.info(f"创建输出目录: {output_dir}")
                except Exception as e:
                    self.logger.error(f"创建输出目录失败: {str(e)}")
                    return []
            
            # 使用默认选项或传入的选项
            split_options = options or SplitOptions()
            self.logger.info(f"分割选项: 格式={split_options.output_format}, 质量={split_options.quality}")
            
            # 准备线程池
            output_files = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_segment = {}
                
                # 提交所有分段任务
                for i, segment_option in enumerate(segment_options_list):
                    # 检查时间是否有效
                    if segment_option.start < 0:
                        self.logger.warning(f"分段{i+1}的开始时间无效 ({segment_option.start}秒)，已调整为0")
                        segment_option.start = 0
                    
                    if audio_duration > 0 and segment_option.end > audio_duration:
                        self.logger.warning(f"分段{i+1}的结束时间 ({segment_option.end}秒) 超过音频时长 ({audio_duration}秒)，已调整")
                        segment_option.end = audio_duration
                    
                    if segment_option.end <= segment_option.start:
                        self.logger.warning(f"跳过分段{i+1}：结束时间 ({segment_option.end}秒) 小于等于开始时间 ({segment_option.start}秒)")
                        continue
                    
                    segment_text = segment_option.text or f"segment_{i+1}"
                    safe_filename = AudioUtils.make_safe_filename(segment_text)
                    if len(safe_filename) > 100:  # 限制文件名长度
                        safe_filename = safe_filename[:100]
                    
                    output_file = os.path.join(
                        output_dir, 
                        f"{safe_filename}_{segment_option.start:.2f}-{segment_option.end:.2f}.{split_options.output_format}"
                    )
                    
                    self.logger.info(f"提交分段{i+1}任务: {segment_option.start:.2f}秒 - {segment_option.end:.2f}秒 -> {os.path.basename(output_file)}")
                    
                    future = executor.submit(
                        self._split_segment, 
                        audio_file, 
                        segment_option,
                        output_file, 
                        split_options
                    )
                    future_to_segment[future] = (i, segment_option, output_file)
                
                # 处理所有任务结果
                total_segments = len(future_to_segment)
                completed = 0
                
                for future in as_completed(future_to_segment):
                    completed += 1
                    i, segment_option, output_file = future_to_segment[future]
                    
                    try:
                        success = future.result()
                        if success:
                            self.logger.info(f"分段{i+1}处理成功: {os.path.basename(output_file)}")
                            output_files.append(output_file)
                        else:
                            self.logger.error(f"分段{i+1}处理失败: {segment_option.start:.2f}秒 - {segment_option.end:.2f}秒")
                    except Exception as e:
                        self.logger.exception(f"分段{i+1}处理异常: {str(e)}")
                    
                    # 更新进度
                    if on_progress:
                        on_progress(completed, total_segments)
            
            self.logger.info(f"音频分割完成: 成功处理 {len(output_files)}/{total_segments} 个分段")
            return output_files
            
        except Exception as e:
            self.logger.exception(f"分割音频时出错: {str(e)}")
            import traceback
            self.logger.error(f"详细错误跟踪: {traceback.format_exc()}")
            return [] 