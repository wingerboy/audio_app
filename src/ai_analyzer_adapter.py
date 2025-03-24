#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import torch
import logging
from logging_config import LoggingConfig

# 导入新的AI分析组件
from .ai import WhisperTranscriber, ContentAnalyzer

class AIAnalyzerAdapter:
    """
    适配器类，提供与旧版AudioAnalyzer兼容的接口，但内部使用新的AI分析组件
    """
    
    def __init__(self, model_size="base"):
        """
        使用指定大小的Whisper模型初始化音频分析器
        
        Args:
            model_size: 模型大小，可选tiny/base/small/medium/large
        """
        self.logger = LoggingConfig.get_logger(__name__)
        self.model_size = model_size
        
        # 检查GPU状态并记录日志
        self._log_gpu_status()
        
        # 选择设备
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 创建转录器和内容分析器
        self.transcriber = WhisperTranscriber(
            model_name=model_size,
            device=self.device
        )
        
        self.content_analyzer = ContentAnalyzer()
        
        self.logger.info(f"初始化AI分析适配器: 模型={model_size}, 设备={self.device}")
    
    def _log_gpu_status(self):
        """记录GPU状态信息"""
        self.logger.debug(f"CUDA是否可用: {torch.cuda.is_available()}")
        self.logger.debug(f"PyTorch版本: {torch.__version__}")
        
        if torch.cuda.is_available():
            self.logger.info(f"使用GPU进行音频分析")
            self.logger.debug(f"GPU数量: {torch.cuda.device_count()}")
            self.logger.debug(f"GPU型号: {torch.cuda.get_device_name(0)}")
            self.logger.debug(f"当前选择的GPU: {torch.cuda.current_device()}")
            try:
                self.logger.debug(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024:.2f} GB")
            except Exception as e:
                self.logger.warning(f"获取GPU内存信息失败: {e}")
        else:
            self.logger.warning("未检测到可用的GPU。转录将使用CPU，这可能会很慢。")
            self.logger.info("如果您有NVIDIA GPU，请确保正确安装了CUDA和相应版本的PyTorch。")
    
    def transcribe_audio(self, audio_path, language=None, progress_callback=None):
        """
        转录音频文件（兼容旧接口）
        
        Args:
            audio_path: 音频文件路径
            language: 指定语言代码（如zh, en, ja等），None为自动检测
            progress_callback: 进度回调函数
            
        Returns:
            包含转录结果的字典
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"音频文件不存在: {audio_path}")
            return {"text": "", "segments": []}
        
        try:
            # 更新进度
            if progress_callback:
                progress_callback("开始转录音频...", 0)
            
            # 使用新的转录器进行转录
            result = self.transcriber.transcribe(audio_path)
            
            # 转换结果格式，适配旧接口
            text = result.text
            metadata = result.metadata
            
            # 构建分段信息
            segments = []
            if "segments" in metadata:
                for i, segment in enumerate(metadata["segments"]):
                    segments.append({
                        "id": i,
                        "start": segment.get("start", 0),
                        "end": segment.get("end", 0),
                        "text": segment.get("text", "").strip()
                    })
            
            # 更新进度
            if progress_callback:
                progress_callback("转录完成", 100)
            
            self.logger.info(f"转录完成，识别到 {len(segments)} 个片段")
            
            return {
                "text": text,
                "segments": segments
            }
            
        except Exception as e:
            self.logger.exception(f"转录过程中出错: {str(e)}")
            if progress_callback:
                progress_callback(f"转录失败: {str(e)}", 0)
            return {"text": "", "segments": []}
    
    def find_sentence_breaks(self, transcription, max_interval=60, min_interval=10, preserve_sentences=True):
        """
        在最小和最大间隔之间找到逻辑句子断点，同时保持句子完整性（兼容旧接口）
        
        Args:
            transcription: 转录结果，包含segments
            max_interval: 最大片段间隔（秒）
            min_interval: 最小片段间隔（秒）
            preserve_sentences: 是否保留句子完整性
        
        Returns:
            带有优化断点的分段列表
        """
        if not transcription or "segments" not in transcription:
            return []
            
        # 获取原始片段
        original_segments = transcription["segments"]
        if not original_segments:
            return []
            
        try:
            self.logger.info(f"优化断句: 最大间隔={max_interval}秒, 最小间隔={min_interval}秒, 保留句子完整性={preserve_sentences}")
            
            # 配置段落处理选项
            from .audio import SegmentOptions
            segment_options = SegmentOptions(
                min_length=min_interval,
                max_length=max_interval,
                preserve_sentences=preserve_sentences
            )
            
            # 使用AudioSplitter的prepare_segments方法处理段落
            from .audio import AudioSplitter
            splitter = AudioSplitter()
            processed_segments = splitter.prepare_segments(original_segments, segment_options)
            
            self.logger.info(f"优化断句完成: 输入{len(original_segments)}个段落，输出{len(processed_segments)}个优化段落")
            
            return processed_segments
            
        except Exception as e:
            self.logger.exception(f"优化断句过程中出错: {str(e)}")
            return original_segments  # 出错时返回原始段落 