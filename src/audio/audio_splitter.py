import os
import tempfile
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Callable, Dict, Any, Optional, Union

from .audio_utils import AudioUtils
from ..temp import TempFileManager

# 添加PyAV支持检测
try:
    import av
    PYAV_AVAILABLE = True
except ImportError:
    PYAV_AVAILABLE = False

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
            quality: 输出质量 (low, medium, high, very_high)
        """
        self.output_format = output_format
        self.quality = quality
    
    def get_format_options(self) -> Dict[str, Any]:
        """获取格式特定的选项"""
        if self.output_format == "mp3":
            # MP3 质量选项
            quality_map = {
                "low": {"bitrate": "64k"},
                "medium": {"bitrate": "128k"},
                "high": {"bitrate": "192k"},
                "very_high": {"bitrate": "256k"}
            }
            return quality_map.get(self.quality, quality_map["medium"])
            
        elif self.output_format == "wav":
            # WAV 质量选项 (采样率)
            quality_map = {
                "low": {"sample_rate": 22050},
                "medium": {"sample_rate": 44100},
                "high": {"sample_rate": 48000},
                "very_high": {"sample_rate": 96000}
            }
            return quality_map.get(self.quality, quality_map["medium"])
            
        elif self.output_format == "ogg":
            # OGG 质量选项
            quality_map = {
                "low": {"quality": 3},
                "medium": {"quality": 5},
                "high": {"quality": 7},
                "very_high": {"quality": 9}
            }
            return quality_map.get(self.quality, quality_map["medium"])
            
        else:
            # 默认使用中等质量
            return {}

class AudioSplitter:
    """音频分割器类"""
    
    def __init__(self, max_workers=None):
        """
        初始化音频分割器
        
        Args:
            max_workers: 最大并行工作线程数（默认为CPU核心数-1，最小为2）
        """
        self.logger = logging.getLogger(__name__)
        
        # 设置最大线程数，默认为CPU核心数-1（至少为2）
        if max_workers is None:
            import os
            cpu_count = os.cpu_count() or 4  # 如果获取失败，默认为4
            self.max_workers = max(2, cpu_count - 1)  # 至少为2
        else:
            self.max_workers = max(2, max_workers)  # 确保至少为2
            
        self.logger.info(f"初始化音频分割器: 最大线程数={self.max_workers}, PyAV可用={PYAV_AVAILABLE}")
    
    def prepare_segments(self, segments: List[Dict[str, Any]], min_length: float = 3.0, 
                        max_length: float = 60.0, preserve_sentences: bool = True) -> List[Dict[str, Any]]:
        """
        处理和优化分段信息，合并过短的段落，切分过长的段落
        
        Args:
            segments: 原始分段信息列表
            min_length: 最小片段长度(秒)
            max_length: 最大片段长度(秒)
            preserve_sentences: 是否保持句子完整性
            
        Returns:
            处理后的分段列表
        """
        if not segments:
            self.logger.warning("没有提供分段信息")
            return []
        
        self.logger.info(f"处理分段：原始分段数量={len(segments)}, 最小长度={min_length}秒, "
                        f"最大长度={max_length}秒, 保持句子完整性={preserve_sentences}")
        
        # 处理分段，合并过短片段
        processed_segments = []
        temp_segment = None
        
        for segment in segments:
            # 确保分段信息格式正确
            start = segment.get("start", 0)
            end = segment.get("end", 0)
            text = segment.get("text", "").strip()
            
            # 计算当前段长度
            duration = end - start
            
            # 如果没有临时段，创建一个
            if temp_segment is None:
                temp_segment = {
                    "start": start,
                    "end": end,
                    "text": text,
                    "words": segment.get("words", [])
                }
            else:
                # 如果preserve_sentences为True，判断文本是否以句号、问号或感叹号结束
                is_sentence_end = False
                if preserve_sentences:
                    last_char = temp_segment["text"].strip()[-1] if temp_segment["text"].strip() else ""
                    is_sentence_end = last_char in [".", "?", "!", "。", "？", "！"]
                
                # 如果当前临时段 + 当前段 <= 最大长度，并且（不需要保持句子完整性或当前是句尾），则合并它们
                temp_duration = temp_segment["end"] - temp_segment["start"]
                if temp_duration + duration <= max_length and (not preserve_sentences or is_sentence_end):
                    temp_segment["end"] = end
                    temp_segment["text"] += " " + text
                    if "words" in segment and "words" in temp_segment:
                        temp_segment["words"].extend(segment.get("words", []))
                else:
                    # 当前临时段长度已足够或是句子结束
                    processed_segments.append(temp_segment)
                    temp_segment = {
                        "start": start,
                        "end": end,
                        "text": text,
                        "words": segment.get("words", [])
                    }
            
            # 检查临时段长度
            temp_duration = temp_segment["end"] - temp_segment["start"]
            if temp_duration >= max_length:
                processed_segments.append(temp_segment)
                temp_segment = None
        
        # 添加最后一个临时段
        if temp_segment is not None:
            temp_duration = temp_segment["end"] - temp_segment["start"]
            # 只有当长度足够或没有其他段落时才添加
            if temp_duration >= min_length or len(processed_segments) == 0:
                processed_segments.append(temp_segment)
        
        self.logger.info(f"处理后的分段数量: {len(processed_segments)}")
        return processed_segments
    
    def _split_segment(self, audio_file: str, segment_options: SegmentOptions, 
                      output_file: str, split_options: SplitOptions) -> bool:
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
            
            # 获取音频文件类型
            _, ext = os.path.splitext(audio_file)
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 如果PyAV可用，使用PyAV切割
            if PYAV_AVAILABLE and ext.lower() in ['.mp3', '.wav', '.ogg', '.m4a', '.flac']:
                success = self._split_with_pyav(
                    audio_file, start_time, end_time, output_file, split_options
                )
                if success:
                    return True
                self.logger.warning(f"PyAV分割失败，回退到传统方法")
            
            # 回退到传统方法(pydub)
            return self._split_with_pydub(
                audio_file, start_time, end_time, output_file, split_options
            )
            
        except Exception as e:
            self.logger.exception(f"分割音频片段失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def _split_with_pyav(self, audio_file: str, start_time: float, end_time: float, 
                        output_file: str, split_options: SplitOptions) -> bool:
        """使用PyAV分割音频（更高效）"""
        try:
            format_options = split_options.get_format_options()
            
            # 计算时间点（秒）
            start_sec = float(start_time)
            end_sec = float(end_time)
            
            # 打开输入文件
            input_container = av.open(audio_file)
            
            # 找到音频流
            audio_stream = next(s for s in input_container.streams if s.type == 'audio')
            
            # 计算时间戳（使用timebase）
            time_base = audio_stream.time_base
            start_ts = int(start_sec / time_base)
            end_ts = int(end_sec / time_base)
            
            # 创建输出容器
            output_container = av.open(output_file, 'w')
            
            # 添加音频流
            output_stream = output_container.add_stream(template=audio_stream)
            
            # 设置输出质量（如果适用）
            if split_options.output_format == 'mp3':
                bitrate = format_options.get('bitrate', '128k')
                output_stream.bit_rate = int(bitrate.replace('k', '000'))
            elif split_options.output_format == 'wav':
                sample_rate = format_options.get('sample_rate', 44100)
                output_stream.sample_rate = sample_rate
            
            # 寻找到起始位置
            input_container.seek(start_ts, stream=audio_stream)
            
            # 读取和写入帧
            for frame in input_container.decode(audio_stream):
                # 检查是否已经超过结束时间
                if frame.pts > end_ts:
                    break
                
                for packet in output_stream.encode(frame):
                    output_container.mux(packet)
            
            # 刷新剩余帧
            for packet in output_stream.encode(None):
                output_container.mux(packet)
                
            # 关闭容器
            output_container.close()
            input_container.close()
            
            # 验证输出文件
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                self.logger.error(f"PyAV分割失败: 输出文件{output_file}不存在或为空")
                return False
                
            return True
            
        except Exception as e:
            self.logger.warning(f"使用PyAV分割音频失败: {str(e)}")
            return False
    
    def _split_with_pydub(self, audio_file: str, start_time: float, end_time: float, 
                         output_file: str, split_options: SplitOptions) -> bool:
        """使用pydub分割音频（更兼容）"""
        try:
            format_options = split_options.get_format_options()
            
            # 加载音频文件
            self.logger.debug(f"加载音频文件: {audio_file}")
            audio_segment = AudioUtils.load_audio(audio_file)
            
            # 计算时间点（毫秒）
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            
            # 提取片段
            self.logger.debug(f"提取音频片段: {start_ms}ms - {end_ms}ms")
            extract = audio_segment[start_ms:end_ms]
            
            # 根据输出格式和质量导出
            format_type = split_options.output_format.lower()
            
            self.logger.debug(f"导出音频片段为 {format_type} 格式: {output_file}")
            
            # 根据格式和质量选择导出参数
            if format_type == 'mp3':
                bitrate = format_options.get('bitrate', '128k')
                extract.export(output_file, format="mp3", bitrate=bitrate)
                
            elif format_type == 'wav':
                # WAV通常不压缩，质量设置主要影响采样率
                sample_rate = format_options.get('sample_rate', 44100)
                parameters = ["-ar", str(sample_rate)]
                extract.export(output_file, format="wav", parameters=parameters)
                
            elif format_type == 'ogg':
                quality = str(format_options.get('quality', 5))  # 0-10
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
            self.logger.exception(f"使用pydub分割音频失败: {str(e)}")
            return False
    
    def split(self, audio_file: str, segment_options_list: List[SegmentOptions], 
             output_dir: str, options: Optional[SplitOptions] = None, 
             on_progress: Optional[Callable[[int, int], None]] = None) -> List[str]:
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
                os.makedirs(output_dir, exist_ok=True)
                self.logger.info(f"创建输出目录: {output_dir}")
            
            # 设置默认选项
            if options is None:
                options = SplitOptions()
            
            # 格式化文件名（使用序号）
            output_files = []
            
            # 创建一个线程安全的计数器
            progress_counter = {"current": 0, "total": len(segment_options_list), "lock": threading.Lock()}
            
            # 定义分割任务
            def split_task(idx, segment_opt):
                try:
                    # 创建输出文件名
                    segment_text = segment_opt.text.strip()[:30]
                    safe_filename = AudioUtils.make_safe_filename(segment_text)
                    output_filename = f"{idx+1:03d}_{safe_filename}.{options.output_format}"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # 分割片段
                    success = self._split_segment(audio_file, segment_opt, output_path, options)
                    
                    # 更新进度
                    with progress_counter["lock"]:
                        progress_counter["current"] += 1
                        current = progress_counter["current"]
                        total = progress_counter["total"]
                    
                    if on_progress:
                        on_progress(current, total)
                    
                    self.logger.info(f"处理进度: {current}/{total} - 完成度: {current/total*100:.1f}%")
                    
                    if success:
                        return output_path
                    return None
                    
                except Exception as e:
                    self.logger.exception(f"处理分段 {idx} 时出错: {str(e)}")
                    return None
            
            # 使用线程池并行处理
            self.logger.info(f"使用 {self.max_workers} 个线程并行处理 {len(segment_options_list)} 个片段")
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建分割任务
                futures = {
                    executor.submit(split_task, idx, segment_opt): idx 
                    for idx, segment_opt in enumerate(segment_options_list)
                }
                
                # 收集结果
                for future in as_completed(futures):
                    try:
                        output_path = future.result()
                        if output_path:
                            output_files.append(output_path)
                    except Exception as e:
                        idx = futures[future]
                        self.logger.error(f"处理片段 {idx} 时出错: {str(e)}")
            
            # 输出处理总结
            success_count = len(output_files)
            total_count = len(segment_options_list)
            success_rate = success_count / total_count * 100 if total_count > 0 else 0
            
            self.logger.info(f"音频分割完成: 成功 {success_count}/{total_count} ({success_rate:.1f}%)")
            
            # 返回成功生成的文件路径列表
            return sorted(output_files)
            
        except Exception as e:
            self.logger.exception(f"分割音频文件失败: {str(e)}")
            return []