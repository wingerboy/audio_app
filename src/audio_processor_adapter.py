#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import shutil
import logging
from concurrent.futures import ThreadPoolExecutor
from src.utils.logging_config import LoggingConfig

# 导入新的音频处理组件
from .audio import AudioConverter, AudioSplitter, SplitOptions, SegmentOptions, AudioUtils
from .temp import TempFileManager, get_global_manager

class AudioProcessorAdapter:
    """
    适配器类，提供与旧版AudioProcessor兼容的接口，但内部使用新的音频处理组件
    增强版：批处理能力、智能缓存和更好的资源管理
    """
    
    def __init__(self, use_disk_processing=True, chunk_size_mb=200, max_workers=None, auto_cleanup=True):
        """
        初始化音频处理器适配器
        
        Args:
            use_disk_processing (bool): 是否使用硬盘处理大文件
            chunk_size_mb (int): 处理大文件时的分块大小(MB)
            max_workers (int): 并行处理的最大线程数（默认为系统CPU核心数-1，最小为2）
            auto_cleanup (bool): 是否在析构时自动清理临时文件
        """
        self.logger = LoggingConfig.get_logger(__name__)
        
        # 初始化临时文件管理器 - 带有更好的内存限制
        self.temp_manager = TempFileManager(prefix="audio_processor_")
        self.auto_cleanup = auto_cleanup
        
        # 处理音频时的内存限制（MB）
        self.memory_limit_mb = min(1024, max(256, os.getenv("AUDIO_MEMORY_LIMIT_MB", 512)))
        self.logger.info(f"设置音频处理内存限制: {self.memory_limit_mb} MB")
        
        # 初始化重要文件列表，防止被自动清理
        self.important_files = []
        
        # 创建音频转换器
        self.converter = AudioConverter()
        
        # 设置最大线程数，默认为CPU核心数-1（至少为2，但不超过12）
        if max_workers is None:
            cpu_count = os.cpu_count() or 4  # 如果获取失败，默认为4
            self.max_workers = max(2, min(12, cpu_count - 1))  # 至少为2，最多为12
        else:
            self.max_workers = max(2, min(12, max_workers))  # 确保至少为2，最多为12
        
        # 创建音频分割器 - 设置更智能的线程池管理
        self.splitter = AudioSplitter(max_workers=self.max_workers)
        
        # 保存参数配置
        self.use_disk_processing = use_disk_processing
        self.chunk_size_mb = chunk_size_mb
        
        # 添加缓存机制
        self.cache = {}
        self.max_cache_entries = 10
        
        self.logger.info(f"初始化音频处理适配器: 使用磁盘处理={use_disk_processing}, 分块大小={chunk_size_mb}MB, "
                        f"最大线程数={self.max_workers}, 自动清理={auto_cleanup}")
    
    @property
    def temp_dir(self):
        """获取临时目录路径"""
        return self.temp_manager.base_dir
    
    def protect_file(self, file_path):
        """将文件添加到保护列表，避免被清理"""
        if file_path and os.path.exists(file_path) and file_path not in self.important_files:
            self.important_files.append(file_path)
            self.temp_manager.protect_file(file_path)
            self.logger.debug(f"文件已加入保护列表: {file_path}")
    
    def extract_audio(self, file_path, output_path=None, progress_callback=None):
        """
        从文件中提取音频（兼容旧接口）- 增强版：更好的内存管理和输出控制
        
        Args:
            file_path: 文件路径
            output_path: 可选的输出路径，允许控制提取的音频保存位置
            progress_callback: 进度回调函数
            
        Returns:
            提取出的音频文件路径，如果失败则返回None
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        # 缓存检查 - 如果已经处理过相同的文件，直接返回缓存结果
        cache_key = f"extract_{file_path}"
        if cache_key in self.cache and os.path.exists(self.cache[cache_key]):
            self.logger.info(f"使用缓存的提取结果: {self.cache[cache_key]}")
            return self.cache[cache_key]
        
        # 检查文件大小
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        # 对大文件使用特殊优化
        large_file = file_size_mb > self.memory_limit_mb
        if large_file:
            self.logger.info(f"大文件检测 ({file_size_mb:.2f} MB > {self.memory_limit_mb} MB), 使用特殊优化")
        
        try:
            self.logger.info(f"提取音频: {file_path}, 大小: {file_size_mb:.2f} MB")
            
            # 进度更新
            if progress_callback:
                progress_callback("准备提取音频...", 10)
            
            # 设置具体的输出路径
            if output_path:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
            else:
                # 如果没有指定输出路径，使用临时目录
                output_path = self.temp_manager.get_temp_file(suffix=".wav")
            
            # 使用音频转换器提取音频 - 设置适当的转换选项
            conversion_options = {
                "output_format": "wav",
                "use_disk_processing": self.use_disk_processing or large_file,
                "temp_manager": self.temp_manager
            }
            
            # 对于大文件，使用更优化的处理方法
            if large_file:
                conversion_options["chunk_size_mb"] = min(self.chunk_size_mb, self.memory_limit_mb // 2)
            
            # 使用新的转换器提取音频
            output_audio_path = self.converter.extract_audio(
                file_path, 
                output_path=output_path,
                **conversion_options
            )
            
            # 将提取的文件添加到不清理列表
            if output_audio_path:
                self.protect_file(output_audio_path)
                
                # 添加到缓存
                if len(self.cache) >= self.max_cache_entries:
                    # 移除最早的缓存项
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                
                self.cache[cache_key] = output_audio_path
            
            # 更新进度
            if progress_callback:
                progress_callback("音频提取完成", 100)
                
            return output_audio_path
            
        except Exception as e:
            self.logger.exception(f"提取音频时发生错误: {str(e)}")
            if progress_callback:
                progress_callback(f"提取失败: {str(e)}", 0)
            return None
    
    def split_audio(self, audio_path, segments, output_dir, output_format="mp3", 
                   quality="medium", progress_callback=None, batch_size=None):
        """
        根据时间段列表分割音频（兼容旧接口）- 增强版：批处理和内存优化
        
        Args:
            audio_path (str): 音频文件路径
            segments (list): 包含start和end时间的字典列表 [{"start": 0, "end": 10, "text": "..."}]
            output_dir (str): 输出目录
            output_format (str): 输出格式 (mp3, wav, ogg)
            quality (str): 输出质量 (low, medium, high)
            progress_callback: 进度回调函数
            batch_size: 批处理大小，如果为None则自动计算
            
        Returns:
            输出文件路径列表，如果失败则返回空列表
        """
        if not os.path.exists(audio_path):
            error_msg = f"音频文件不存在: {audio_path}"
            self.logger.error(error_msg)
            
            # 尝试再次查找文件
            alternative_found = False
            for alt_file in self.important_files:
                if os.path.exists(alt_file) and os.path.basename(alt_file) == os.path.basename(audio_path):
                    self.logger.info(f"找到替代音频文件: {alt_file}")
                    audio_path = alt_file
                    alternative_found = True
                    break
            
            if not alternative_found:
                if progress_callback:
                    progress_callback(error_msg, 0)
                return []
        
        # 将音频文件添加到重要文件列表，防止被清理
        self.protect_file(audio_path)
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            try:
                self.logger.info(f"输出目录不存在，尝试创建: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                error_msg = f"创建输出目录失败: {str(e)}"
                self.logger.error(error_msg)
                if progress_callback:
                    progress_callback(error_msg, 0)
                return []
        
        # 获取文件大小并判断是否为大文件
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        large_file = file_size_mb > self.memory_limit_mb
        
        # 打印调试信息
        self.logger.info(f"开始分割音频: {audio_path}, 大小: {file_size_mb:.2f} MB")
        self.logger.info(f"输出目录: {output_dir}")
        self.logger.info(f"分段数量: {len(segments)}")
        self.logger.info(f"输出格式: {output_format}")
        self.logger.info(f"输出质量: {quality}")
        self.logger.info(f"大文件检测: {large_file}")
        
        # 计算最佳批处理大小 - 根据分段数量和文件大小
        if batch_size is None:
            if large_file:
                # 大文件使用较小的批次
                batch_size = max(1, min(5, 50 // len(segments)))
            else:
                # 小文件可以使用较大的批次
                batch_size = max(1, min(20, 100 // len(segments)))
        
        self.logger.info(f"使用批处理大小: {batch_size}")
        
        try:
            # 验证音频文件是否存在且可读
            if not os.access(audio_path, os.R_OK):
                error_msg = f"无法读取音频文件，权限不足: {audio_path}"
                self.logger.error(error_msg)
                if progress_callback:
                    progress_callback(error_msg, 0)
                return []

            # 验证音频文件是否有效
            try:
                audio_info = AudioUtils.get_audio_info(audio_path)
                self.logger.info(f"音频信息: {audio_info}")
            except Exception as e:
                error_msg = f"无法获取音频信息，文件可能损坏: {str(e)}"
                self.logger.error(error_msg)
                if progress_callback:
                    progress_callback(error_msg, 0)
                return []
            
            # 更新进度
            if progress_callback:
                progress_callback("准备分割音频", 0)
            
            # 设置分割选项
            split_options = SplitOptions(
                output_format=output_format,
                quality=quality
            )
            
            # 准备分段选项
            segment_options_list = []
            for i, segment in enumerate(segments):
                try:
                    start_time = float(segment.get("start", 0))
                    end_time = float(segment.get("end", 0))
                    text = segment.get("text", "").strip()
                    
                    # 验证时间段是否有效
                    if end_time <= start_time:
                        self.logger.warning(f"跳过无效的时间段: 段落{i}, 开始={start_time}, 结束={end_time}")
                        continue
                    
                    segment_options = SegmentOptions(
                        start=start_time,
                        end=end_time,
                        text=text
                    )
                    segment_options_list.append(segment_options)
                except Exception as e:
                    self.logger.error(f"处理分段{i}时出错: {str(e)}")
            
            # 检查是否有有效的分段
            if not segment_options_list:
                error_msg = "没有有效的分段信息可处理"
                self.logger.error(error_msg)
                if progress_callback:
                    progress_callback(error_msg, 0)
                return []
            
            # 批量处理分段
            if batch_size > 1 and len(segment_options_list) > batch_size:
                self.logger.info(f"使用批处理模式，共 {len(segment_options_list)} 个分段，批次大小 {batch_size}")
                
                all_output_files = []
                num_batches = (len(segment_options_list) + batch_size - 1) // batch_size
                
                for batch_idx in range(num_batches):
                    start_idx = batch_idx * batch_size
                    end_idx = min(start_idx + batch_size, len(segment_options_list))
                    
                    batch_segments = segment_options_list[start_idx:end_idx]
                    
                    # 计算批次进度
                    batch_progress_base = (batch_idx / num_batches) * 100
                    batch_progress_step = 100 / num_batches
                    
                    def batch_progress_callback(msg, percent):
                        if progress_callback:
                            # 将批次内进度转换为总体进度
                            total_percent = batch_progress_base + (percent / 100 * batch_progress_step)
                            progress_callback(f"批次 {batch_idx+1}/{num_batches}: {msg}", int(total_percent))
                    
                    self.logger.info(f"处理批次 {batch_idx+1}/{num_batches}, 分段 {start_idx+1}-{end_idx}")
                    
                    # 使用新的分割器分割音频
                    batch_results = self.splitter.split(
                        audio_path,
                        batch_segments,
                        output_dir,
                        split_options,
                        on_progress=batch_progress_callback
                    )
                    
                    # 如果当前批次失败，记录错误但继续处理
                    if not batch_results:
                        self.logger.error(f"批次 {batch_idx+1} 处理失败")
                        if progress_callback:
                            progress_callback(f"批次 {batch_idx+1} 处理失败，继续处理其他批次", 
                                            int(batch_progress_base + batch_progress_step))
                    else:
                        all_output_files.extend(batch_results)
                        self.logger.info(f"批次 {batch_idx+1} 完成，生成了 {len(batch_results)} 个文件")
                
                # 清理批处理的临时资源
                if hasattr(self, 'temp_manager'):
                    # 保护重要文件
                    if hasattr(self, 'important_files'):
                        for file_path in self.important_files:
                            self.temp_manager.protect_file(file_path)
                    # 清理其他临时文件
                    self.temp_manager.cleanup()
                
                # 更新最终进度
                if progress_callback:
                    progress_callback(f"分割完成！共处理 {len(all_output_files)} 个文件", 100)
                
                return all_output_files
            else:
                # 对于少量分段或小批次，使用标准处理
                self.logger.info(f"使用标准处理模式，共 {len(segment_options_list)} 个分段")
                
                # 使用新的分割器分割音频
                result = self.splitter.split(
                    audio_path,
                    segment_options_list,
                    output_dir,
                    split_options,
                    on_progress=lambda current, total: 
                        progress_callback(f"分割进度 {current}/{total}", int(current/total*100)) 
                        if progress_callback else None
                )
                
                # 验证结果
                if not result:
                    error_msg = "分割结果为空，可能是所有分段都失败了"
                    self.logger.error(error_msg)
                    if progress_callback:
                        progress_callback(error_msg, 0)
                    return []
                
                # 打印结果
                self.logger.info(f"分割结果: 成功生成{len(result)}个文件")
                
                # 完成进度
                if progress_callback:
                    progress_callback("分割完成！", 100)
                
                return result
            
        except Exception as e:
            error_msg = f"分割音频失败: {str(e)}"
            self.logger.exception(error_msg)
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            if progress_callback:
                progress_callback(f"分割失败: {str(e)}", 0)
            return []
    
    def cleanup_temp_files(self):
        """清理临时文件，保留重要文件"""
        try:
            self.logger.info("开始清理临时文件...")
            
            # 对于TempFileManager管理的文件，使用其清理机制
            if hasattr(self, 'temp_manager'):
                # 保护重要文件
                if hasattr(self, 'important_files'):
                    for file_path in self.important_files:
                        self.temp_manager.protect_file(file_path)
                # 清理其他临时文件
                self.temp_manager.cleanup()
            
            self.logger.info("临时文件清理完成，保留了重要文件")
        except Exception as e:
            self.logger.error(f"清理临时文件时出错: {str(e)}")
    
    def cleanup(self):
        """保持兼容性的清理方法"""
        self.cleanup_temp_files()
    
    def __del__(self):
        """析构函数，根据设置决定是否清理临时文件"""
        if hasattr(self, 'auto_cleanup') and self.auto_cleanup:
            try:
                self.cleanup_temp_files()
            except:
                pass  # 忽略在析构函数中的错误 