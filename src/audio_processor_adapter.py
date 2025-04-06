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
        
        # 初始化临时文件管理器
        self.temp_manager = TempFileManager(prefix="audio_processor_")
        
        # 创建音频转换器
        self.converter = AudioConverter()
        
        # 设置最大线程数，默认为CPU核心数-1（至少为2）
        if max_workers is None:
            cpu_count = os.cpu_count() or 4  # 如果获取失败，默认为4
            self.max_workers = max(2, cpu_count - 1)  # 至少为2
        else:
            self.max_workers = max(2, max_workers)  # 确保至少为2
        
        # 创建音频分割器
        self.splitter = AudioSplitter(max_workers=self.max_workers)
        
        # 保存参数配置
        self.use_disk_processing = use_disk_processing
        self.chunk_size_mb = chunk_size_mb
        self.auto_cleanup = auto_cleanup
        
        # 检查是否可使用PyAV
        try:
            import av
            self.pyav_available = True
            self.logger.info(f"检测到PyAV库 (版本: {av.__version__})，将优先使用PyAV处理音频")
        except ImportError:
            self.pyav_available = False
            self.logger.warning("未检测到PyAV库，将使用FFmpeg处理音频")
        
        self.logger.info(f"初始化AudioProcessorAdapter: 硬盘处理={use_disk_processing}, 分块大小={chunk_size_mb}MB, 最大线程数={self.max_workers}, 自动清理={auto_cleanup}, CPU核心数={os.cpu_count()}")
    
    @property
    def temp_dir(self):
        """获取临时目录路径"""
        return self.temp_manager.base_dir
    
    def extract_audio(self, file_path, progress_callback=None):
        """
        从文件中提取音频（兼容旧接口）
        
        Args:
            file_path: 文件路径
            progress_callback: 进度回调函数
            
        Returns:
            提取出的音频文件路径，如果失败则返回None
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
        
        try:
            self.logger.info(f"提取音频: {file_path}")
            
            # 进度更新
            if progress_callback:
                progress_callback("准备提取音频...", 10)
            
            # 使用新的转换器提取音频
            output_audio_path = self.converter.extract_audio(
                file_path, 
                output_format="wav",
                temp_manager=self.temp_manager
            )
            
            # 将提取的文件添加到不清理列表
            if hasattr(self, 'important_files'):
                self.important_files.append(output_audio_path)
            else:
                self.important_files = [output_audio_path]
            
            self.logger.info(f"添加到保护列表，防止被清理: {output_audio_path}")
            
            # 更新进度
            if progress_callback:
                progress_callback("音频提取完成", 100)
                
            return output_audio_path
            
        except Exception as e:
            self.logger.exception(f"提取音频时发生错误: {str(e)}")
            if progress_callback:
                progress_callback(f"提取失败: {str(e)}", 0)
            return None
    
    def split_audio(self, audio_path, segments, output_dir, output_format="mp3", quality="medium", progress_callback=None):
        """
        根据时间段列表分割音频（兼容旧接口）
        
        Args:
            audio_path (str): 音频文件路径
            segments (list): 包含start和end时间的字典列表 [{"start": 0, "end": 10, "text": "..."}]
            output_dir (str): 输出目录
            output_format (str): 输出格式 (mp3, wav, ogg)
            quality (str): 输出质量 (low, medium, high)
            progress_callback: 进度回调函数
            
        Returns:
            输出文件路径列表，如果失败则返回空列表
        """
        if not os.path.exists(audio_path):
            error_msg = f"音频文件不存在: {audio_path}"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(error_msg, 0)
            return []
        
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
        
        # 打印调试信息
        self.logger.info(f"开始分割音频: {audio_path}")
        self.logger.info(f"输出目录: {output_dir}")
        self.logger.info(f"分段数量: {len(segments)}")
        self.logger.info(f"输出格式: {output_format}")
        self.logger.info(f"输出质量: {quality}")
        
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
            
            # 使用新的分割器分割音频
            self.logger.info(f"调用 AudioSplitter.split 方法，共{len(segment_options_list)}个分段")
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
            for i, file_path in enumerate(result):
                self.logger.info(f"输出文件{i+1}: {file_path}")
            
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
    
    def cleanup(self):
        """清理临时文件，跳过标记为重要的文件"""
        try:
            self.logger.info("开始清理临时文件...")
            
            # 如果有重要文件需要保留
            if hasattr(self, 'important_files') and self.important_files:
                self.logger.info(f"保留{len(self.important_files)}个重要文件，不进行清理: {self.important_files}")
                
                # 获取当前所有临时文件
                files_to_clean = list(self.temp_manager.temp_files)
                
                # 排除标记为重要的文件
                for file_path in files_to_clean:
                    if file_path not in self.important_files:
                        self.temp_manager.remove_file(file_path)
                        self.logger.debug(f"清理非重要临时文件: {file_path}")
                    else:
                        self.logger.info(f"保留重要文件: {file_path}")
            else:
                # 没有重要文件，正常清理
                self.temp_manager.cleanup()
                self.logger.info("临时文件清理完成")
        except Exception as e:
            self.logger.error(f"清理临时文件时出错: {str(e)}")
    
    def __del__(self):
        """析构函数，根据设置决定是否清理临时文件"""
        if hasattr(self, 'auto_cleanup') and self.auto_cleanup:
            try:
                self.cleanup()
            except:
                pass  # 忽略在析构函数中的错误 