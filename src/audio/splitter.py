#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor
from pydub import AudioSegment
from src.utils.logging_config import LoggingConfig
from ..temp.manager import TempFileManager
import threading
from concurrent.futures import as_completed

# 添加PyAV导入
try:
    import av
    PYAV_AVAILABLE = True
except ImportError:
    PYAV_AVAILABLE = False

class SplitOptions:
    """音频分割选项"""
    
    def __init__(self, output_format="mp3", quality="medium"):
        """
        初始化分割选项
        
        Args:
            output_format: 输出格式
            quality: 输出质量
        """
        self.output_format = output_format
        self.quality = quality
        
        # 质量对应的比特率映射
        self.quality_map = {
            "low": "64k",
            "medium": "128k",
            "high": "192k",
            "very_high": "256k"
        }
    
    def get_bitrate(self):
        """获取对应质量的比特率"""
        return self.quality_map.get(self.quality, "128k")

class SegmentOptions:
    """片段处理选项"""
    
    def __init__(self, min_length=3.0, max_length=60.0, preserve_sentences=True):
        """
        初始化片段选项
        
        Args:
            min_length: 最小片段长度(秒)
            max_length: 最大片段长度(秒)
            preserve_sentences: 是否保持句子完整性
        """
        self.min_length = min_length
        self.max_length = max_length
        self.preserve_sentences = preserve_sentences

class AudioSplitter:
    """音频分割器，负责音频文件的智能分割"""
    
    def __init__(self, max_workers=None):
        """
        初始化音频分割器
        
        Args:
            max_workers: 最大并行工作线程数（默认为CPU核心数-1，最小为2）
        """
        self.logger = LoggingConfig.get_logger(__name__)
        
        # 设置最大线程数，默认为CPU核心数-1（至少为2）
        if max_workers is None:
            import os
            cpu_count = os.cpu_count() or 4  # 如果获取失败，默认为4
            self.max_workers = max(2, cpu_count - 1)  # 至少为2
        else:
            self.max_workers = max(2, max_workers)  # 确保至少为2
        
        self.logger.info(f"初始化音频分割器: 最大线程数={self.max_workers}")
    
    def prepare_segments(self, segments, options=None):
        """
        处理和优化分段信息，合并过短的段落，切分过长的段落
        
        Args:
            segments: 原始分段信息列表
            options: 段落处理选项
            
        Returns:
            list: 处理后的分段列表
        """
        if options is None:
            options = SegmentOptions()
        
        if not segments:
            self.logger.warning("没有提供分段信息")
            return []
        
        self.logger.info(f"处理分段：原始分段数量={len(segments)}, 最小长度={options.min_length}秒, 最大长度={options.max_length}秒, 保持句子完整性={options.preserve_sentences}")
        
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
                # 如果options.preserve_sentences为True，判断文本是否以句号、问号或感叹号结束
                is_sentence_end = False
                if options.preserve_sentences:
                    last_char = temp_segment["text"].strip()[-1] if temp_segment["text"].strip() else ""
                    is_sentence_end = last_char in [".", "?", "!", "。", "？", "！"]
                
                # 如果当前临时段 + 当前段 <= 最大长度，并且（不需要保持句子完整性或当前是句尾），则合并它们
                temp_duration = temp_segment["end"] - temp_segment["start"]
                if temp_duration + duration <= options.max_length and (not options.preserve_sentences or is_sentence_end):
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
            if temp_duration >= options.max_length:
                processed_segments.append(temp_segment)
                temp_segment = None
        
        # 添加最后一个临时段
        if temp_segment is not None:
            temp_duration = temp_segment["end"] - temp_segment["start"]
            # 只有当长度足够或没有其他段落时才添加
            if temp_duration >= options.min_length or len(processed_segments) == 0:
                processed_segments.append(temp_segment)
        
        self.logger.info(f"处理后的分段数量: {len(processed_segments)}")
        return processed_segments
    
    def split_audio(self, audio_path, segments, output_dir=None, split_options=None, 
                   segment_options=None, temp_manager=None, progress_callback=None):
        """
        根据分段信息分割音频
        
        Args:
            audio_path: 音频文件路径
            segments: 分段信息列表
            output_dir: 输出目录
            split_options: 分割选项
            segment_options: 段落处理选项
            temp_manager: 临时文件管理器
            progress_callback: 进度回调函数
            
        Returns:
            list: 输出文件路径列表
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"音频文件不存在: {audio_path}")
            return []
        
        # 设置默认选项
        if split_options is None:
            split_options = SplitOptions()
        
        if segment_options is None:
            segment_options = SegmentOptions()
        
        # 处理输出目录
        if output_dir is None:
            # 如果有临时文件管理器，在其中创建输出目录
            if temp_manager:
                output_dir = temp_manager.create_named_dir("output")
            else:
                # 否则在系统临时目录中创建
                output_dir = os.path.join(tempfile.gettempdir(), f"audio_output_{int(time.time())}")
                os.makedirs(output_dir, exist_ok=True)
        else:
            # 确保目录存在
            os.makedirs(output_dir, exist_ok=True)
        
        # 处理和优化分段
        processed_segments = self.prepare_segments(segments, segment_options)
        
        # 检查文件大小，对于大文件使用不同的处理策略
        # 使用磁盘处理以避免内存溢出
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        if file_size_mb > 200:  # 大于200MB的文件使用直接处理
            self.logger.info(f"检测到大文件 ({file_size_mb:.1f}MB)，使用直接处理方式")
            return self._split_large_audio(
                audio_path, processed_segments, output_dir, 
                split_options.output_format, split_options.get_bitrate(),
                progress_callback
            )
        
        # 加载音频文件到内存
        try:
            self.logger.info(f"加载音频文件: {audio_path}")
            audio = AudioSegment.from_file(audio_path)
            self.logger.info(f"音频长度: {len(audio)/1000:.1f}秒, 声道数: {audio.channels}, 采样率: {audio.frame_rate}Hz")
            
            # 使用线程池并行处理分段
            output_files = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交处理任务
                future_to_segment = {
                    executor.submit(
                        self._process_segment, 
                        audio, segment, i, output_dir, 
                        split_options.output_format, split_options.get_bitrate()
                    ): (i, segment) for i, segment in enumerate(processed_segments)
                }
                
                # 处理结果
                total = len(future_to_segment)
                completed = 0
                
                for future in future_to_segment:
                    try:
                        output_file = future.result()
                        if output_file:
                            output_files.append(output_file)
                        
                        # 更新进度
                        completed += 1
                        if progress_callback:
                            progress = int(completed * 100 / total)
                            progress_callback(f"分割音频 ({completed}/{total})", progress)
                    
                    except Exception as e:
                        i, segment = future_to_segment[future]
                        self.logger.exception(f"处理分段 {i} 时出错: {str(e)}")
            
            # 按序号排序输出文件
            output_files.sort()
            self.logger.info(f"音频分割完成，共生成 {len(output_files)} 个文件")
            return output_files
            
        except Exception as e:
            self.logger.exception(f"分割音频时出错: {str(e)}")
            return []
    
    def _process_segment(self, audio, segment, index, output_dir, output_format, bitrate):
        """
        处理单个音频片段
        
        Args:
            audio: 音频数据
            segment: 分段信息
            index: 分段索引
            output_dir: 输出目录
            output_format: 输出格式
            bitrate: 比特率
            
        Returns:
            str: 输出文件路径
        """
        try:
            start_ms = int(segment["start"] * 1000)
            end_ms = int(segment["end"] * 1000)
            
            # 安全检查：确保时间范围有效
            if start_ms < 0:
                start_ms = 0
            if end_ms > len(audio):
                end_ms = len(audio)
            if start_ms >= end_ms:
                self.logger.warning(f"片段 {index+1} 时间范围无效: {start_ms}ms - {end_ms}ms")
                return None
            
            # 提取片段
            segment_audio = audio[start_ms:end_ms]
            
            # 创建文件名
            start_time_str = time.strftime('%H-%M-%S', time.gmtime(segment["start"]))
            duration = segment["end"] - segment["start"]
            
            # 处理文本，限制长度并移除非法字符
            text = segment.get("text", "").strip()
            if len(text) > 30:
                text = text[:27] + "..."
            
            # 清理文件名中的非法字符
            text = "".join(c for c in text if c.isalnum() or c in " .,;-_()[]{}").strip()
            if not text:
                text = "segment"
            
            # 构建文件名和路径
            filename = f"{index+1:03d}_{start_time_str}_{int(duration)}s_{text}.{output_format}"
            output_path = os.path.join(output_dir, filename)
            
            # 导出音频
            segment_audio.export(
                output_path,
                format=output_format,
                bitrate=bitrate,
                tags={
                    "artist": "Audio Segmentation Tool",
                    "title": text,
                    "album": "Segmented Audio",
                    "track": str(index + 1)
                }
            )
            
            self.logger.debug(f"已处理分段 {index+1}: {start_time_str}, 长度={duration:.1f}秒")
            return output_path
            
        except Exception as e:
            self.logger.exception(f"处理分段 {index+1} 时出错: {str(e)}")
            return None
    
    def _process_segment_with_pyav(self, audio_path, segment, index, output_dir, output_format, bitrate, total_segments):
        """
        使用PyAV处理单个音频片段
        
        Args:
            audio_path: 音频文件路径
            segment: 分段信息
            index: 分段索引
            output_dir: 输出目录
            output_format: 输出格式
            bitrate: 比特率
            total_segments: 分段总数
            
        Returns:
            tuple: (索引, 输出文件路径) 或 None（如果失败）
        """
        try:
            start_sec = segment["start"]
            end_sec = segment["end"]
            duration = end_sec - start_sec
            
            # 创建文件名
            start_time_str = time.strftime('%H-%M-%S', time.gmtime(start_sec))
            
            # 处理文本
            text = segment.get("text", "").strip()
            if len(text) > 30:
                text = text[:27] + "..."
            
            # 清理文件名
            text = "".join(c for c in text if c.isalnum() or c in " .,;-_()[]{}").strip()
            if not text:
                text = "segment"
            
            filename = f"{index+1:03d}_{start_time_str}_{int(duration)}s_{text}.{output_format}"
            output_path = os.path.join(output_dir, filename)
            
            self.logger.debug(f"使用PyAV处理分段 {index+1}: {start_sec}s - {end_sec}s")
            
            # 打开输入文件
            input_container = av.open(audio_path)
            
            # 创建输出容器
            output_container = av.open(output_path, mode='w')
            
            # 找到输入文件中的音频流
            audio_input_stream = next((s for s in input_container.streams if s.type == 'audio'), None)
            if audio_input_stream is None:
                raise ValueError("找不到音频流")
            
            # 设置输出格式和编码器
            if output_format == "mp3":
                audio_stream = output_container.add_stream('mp3', rate=audio_input_stream.sample_rate)
                audio_stream.bit_rate = 192000  # Equivalent to q:a 2
            elif output_format == "wav":
                audio_stream = output_container.add_stream('pcm_s16le', rate=audio_input_stream.sample_rate) 
            elif output_format == "ogg":
                audio_stream = output_container.add_stream('libvorbis', rate=audio_input_stream.sample_rate)
                audio_stream.bit_rate = 128000  # Equivalent to q:a 4
            elif output_format == "flac":
                audio_stream = output_container.add_stream('flac', rate=audio_input_stream.sample_rate)
            else:
                # 默认使用AAC
                audio_stream = output_container.add_stream('aac', rate=audio_input_stream.sample_rate)
                if isinstance(bitrate, str) and 'k' in bitrate:
                    audio_stream.bit_rate = int(bitrate.replace('k', '000'))
                else:
                    audio_stream.bit_rate = 128000  # 默认128kbps
            
            # 计算片段的起始和结束时间点（以时间基为单位）
            timebase = audio_input_stream.time_base
            start_pts = int(start_sec / timebase)
            end_pts = int(end_sec / timebase)
            
            # 设置采样率等格式
            if hasattr(audio_stream, 'frame_size') and audio_stream.frame_size == 0:
                audio_stream.frame_size = 1024
            
            # 设置seek位置
            try:
                # 尝试不同的seek方法，某些文件格式可能需要不同的seek方法
                input_container.seek(int(start_sec * 1000000))  # 微秒单位
            except Exception as e:
                self.logger.warning(f"使用微秒seek失败，尝试使用时间戳: {str(e)}")
                try:
                    # 尝试使用时间戳seek
                    input_container.seek(int(start_sec * audio_input_stream.time_base.denominator), stream=audio_input_stream)
                except Exception as e2:
                    self.logger.warning(f"使用时间戳seek也失败，使用帧跳过方式: {str(e2)}")
                    # 如果都失败，回退到FFmpeg
                    raise ValueError("PyAV无法正确seek，将使用FFmpeg处理")
            
            # 处理每一帧
            for frame in input_container.decode(audio=0):
                # 计算帧的时间点
                frame_time = frame.pts * frame.time_base
                
                # 检查是否超出了片段结束时间
                if frame_time > end_sec:
                    break
                
                # 编码并写入输出帧
                for packet in audio_stream.encode(frame):
                    output_container.mux(packet)
            
            # Flush编码器
            for packet in audio_stream.encode(None):
                output_container.mux(packet)
                
            # 关闭容器
            output_container.close()
            input_container.close()
            
            self.logger.debug(f"已处理分段 {index+1}/{total_segments}: {start_time_str}, 长度={duration:.1f}秒")
            
            # 验证输出文件是否创建成功
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return (index, output_path)
            else:
                self.logger.warning(f"PyAV生成的文件无效或为空: {output_path}")
                return None
            
        except Exception as e:
            self.logger.exception(f"PyAV处理分段 {index+1} 时出错: {str(e)}")
            return None

    def _process_segment_with_ffmpeg(self, audio_path, segment, index, output_dir, output_format, bitrate, total_segments):
        """
        使用FFmpeg命令行处理单个音频片段
        
        Args:
            audio_path: 音频文件路径
            segment: 分段信息
            index: 分段索引
            output_dir: 输出目录
            output_format: 输出格式
            bitrate: 比特率
            total_segments: 分段总数
            
        Returns:
            tuple: (索引, 输出文件路径) 或 None（如果失败）
        """
        try:
            start_sec = segment["start"]
            end_sec = segment["end"]
            duration = end_sec - start_sec
            
            # 创建文件名
            start_time_str = time.strftime('%H-%M-%S', time.gmtime(start_sec))
            
            # 处理文本
            text = segment.get("text", "").strip()
            if len(text) > 30:
                text = text[:27] + "..."
            
            # 清理文件名
            text = "".join(c for c in text if c.isalnum() or c in " .,;-_()[]{}").strip()
            if not text:
                text = "segment"
            
            filename = f"{index+1:03d}_{start_time_str}_{int(duration)}s_{text}.{output_format}"
            output_path = os.path.join(output_dir, filename)
            
            # 针对不同格式选择合适的编码器
            if output_format == "mp3":
                codec = ["-c:a", "libmp3lame", "-q:a", "2"]
            elif output_format == "wav":
                codec = ["-c:a", "pcm_s16le"]
            elif output_format == "ogg":
                codec = ["-c:a", "libvorbis", "-q:a", "4"]
            elif output_format == "flac":
                codec = ["-c:a", "flac"]
            else:
                # 默认使用AAC
                codec = ["-c:a", "aac", "-b:a", bitrate]
            
            # 构建FFmpeg命令
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-ss", str(start_sec),
                "-t", str(duration)
            ] + codec + [
                "-ar", "44100",  # 采样率
                "-y",  # 覆盖输出文件
                "-loglevel", "error",  # 减少FFmpeg日志输出
                output_path
            ]
            
            self.logger.debug(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 执行命令
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0 and os.path.exists(output_path):
                self.logger.debug(f"已处理分段 {index+1}/{total_segments}: {start_time_str}, 长度={duration:.1f}秒")
                return (index, output_path)
            else:
                self.logger.error(f"处理分段 {index+1} 失败: {process.stderr}")
                return None
            
        except Exception as e:
            self.logger.exception(f"处理分段 {index+1} 时出错: {str(e)}")
            return None
    
    def _split_large_audio(self, audio_path, segments, output_dir, output_format, bitrate, progress_callback=None):
        """
        使用直接处理方式处理大型音频文件，避免内存问题
        
        Args:
            audio_path: 音频文件路径
            segments: 分段信息列表
            output_dir: 输出目录
            output_format: 输出格式
            bitrate: 比特率
            progress_callback: 进度回调函数
            
        Returns:
            list: 输出文件路径列表
        """
        use_pyav = PYAV_AVAILABLE
        processing_method = "PyAV" if use_pyav else "FFmpeg"
        self.logger.info(f"使用{processing_method}直接处理大文件 (并行处理, {self.max_workers}线程)")
        
        output_files = []
        output_files_lock = threading.Lock()  # 用于安全更新输出文件列表
        processed_count = [0]  # 使用列表以便在闭包中修改
        total_segments = len(segments)
        
        def process_segment(i, segment):
            # 首先尝试使用PyAV处理
            result = None
            if use_pyav:
                try:
                    result = self._process_segment_with_pyav(
                        audio_path, segment, i, output_dir, output_format, bitrate, total_segments
                    )
                except Exception as e:
                    self.logger.warning(f"使用PyAV处理分段 {i+1} 失败，回退到FFmpeg: {str(e)}")
                    result = None
            
            # 如果PyAV失败或不可用，回退到FFmpeg
            if result is None:
                result = self._process_segment_with_ffmpeg(
                    audio_path, segment, i, output_dir, output_format, bitrate, total_segments
                )
            
            # 更新处理计数并报告进度
            with output_files_lock:
                processed_count[0] += 1
                if progress_callback:
                    progress = int(processed_count[0] * 100 / total_segments)
                    progress_callback(f"分割大文件 ({processed_count[0]}/{total_segments})", progress)
            
            return result
        
        # 使用线程池并行处理分段
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_segment = {executor.submit(process_segment, i, segment): i for i, segment in enumerate(segments)}
            
            # 处理结果
            for future in as_completed(future_to_segment):
                result = future.result()
                if result:
                    idx, path = result
                    with output_files_lock:
                        output_files.append((idx, path))
        
        # 按索引排序输出文件并只返回路径部分
        output_files.sort()
        sorted_paths = [path for _, path in output_files]
        
        self.logger.info(f"大文件分割完成，共生成 {len(sorted_paths)} 个文件")
        return sorted_paths 