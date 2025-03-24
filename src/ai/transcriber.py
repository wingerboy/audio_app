#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import torch
import logging
import concurrent.futures
from pathlib import Path
from logging_config import LoggingConfig
from ..temp import TempFileManager

class TranscriptionResult:
    """转录结果类"""
    def __init__(self, text, confidence=0.0, metadata=None):
        self.text = text  # 文本内容
        self.confidence = confidence  # 置信度
        self.metadata = metadata or {}  # 其他元数据
    
    def __str__(self):
        return self.text
    
    def __repr__(self):
        return f"TranscriptionResult(text='{self.text[:30]}...', confidence={self.confidence:.2f})"

class BaseTranscriber:
    """转录器基类，定义转录接口"""
    
    def __init__(self):
        self.logger = LoggingConfig.get_logger(__name__)
    
    def transcribe(self, audio_path):
        """
        转录音频文件为文本
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            TranscriptionResult: 转录结果
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def transcribe_batch(self, audio_paths, max_workers=4):
        """
        批量转录多个音频文件
        
        Args:
            audio_paths: 音频文件路径列表
            max_workers: 最大工作线程数
            
        Returns:
            list: TranscriptionResult对象列表
        """
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(self.transcribe, path): path for path in audio_paths}
            
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"已完成转录: {Path(path).name}")
                except Exception as e:
                    self.logger.error(f"转录文件 {path} 时出错: {str(e)}")
                    results.append(TranscriptionResult("", 0.0, {"error": str(e)}))
        
        return results

class WhisperTranscriber(BaseTranscriber):
    """使用OpenAI Whisper模型的转录器"""
    
    def __init__(self, model_name="base", device=None, language=None):
        """
        初始化Whisper转录器
        
        Args:
            model_name: 模型大小名称 "tiny", "base", "small", "medium", "large"
            device: 计算设备 "cpu", "cuda", None (自动检测)
            language: 语言代码，如"zh"为中文，None为自动检测
        """
        super().__init__()
        self.model_name = model_name
        self.language = language
        
        # 自动检测设备
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.model = None
        self.logger.info(f"初始化Whisper转录器: 模型={model_name}, 设备={self.device}, 语言={language or '自动检测'}")
    
    def load_model(self):
        """加载Whisper模型"""
        if self.model is not None:
            return
            
        try:
            import whisper
            self.logger.info(f"正在加载Whisper模型 '{self.model_name}'...")
            self.model = whisper.load_model(self.model_name, device=self.device)
            self.logger.info(f"Whisper模型 '{self.model_name}' 加载完成")
        except Exception as e:
            self.logger.error(f"加载Whisper模型失败: {str(e)}")
            raise RuntimeError(f"加载Whisper模型失败: {str(e)}")
    
    def transcribe(self, audio_path):
        """
        使用Whisper模型转录音频
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            TranscriptionResult: 转录结果
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"音频文件不存在: {audio_path}")
            return TranscriptionResult("", 0.0, {"error": "文件不存在"})
            
        self.load_model()
        
        try:
            # 转录选项
            options = {}
            if self.language:
                options["language"] = self.language
                
            # 执行转录
            self.logger.info(f"开始转录: {Path(audio_path).name}")
            result = self.model.transcribe(audio_path, **options)
            
            # 提取结果
            text = result.get("text", "").strip()
            segments = result.get("segments", [])
            
            # 计算简单的置信度指标（平均分数）
            confidence = 0.0
            if segments:
                avg_confidence = sum(seg.get("confidence", 0) for seg in segments) / len(segments)
                confidence = avg_confidence
                
            self.logger.info(f"转录完成: {Path(audio_path).name}")
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                metadata={
                    "segments": segments,
                    "language": result.get("language", "unknown")
                }
            )
            
        except Exception as e:
            self.logger.exception(f"转录文件 {audio_path} 时出错: {str(e)}")
            return TranscriptionResult("", 0.0, {"error": str(e)})

class TranscriberFactory:
    """转录器工厂类，用于创建不同类型的转录器"""
    
    @staticmethod
    def create(transcriber_type="whisper", **kwargs):
        """
        创建指定类型的转录器
        
        Args:
            transcriber_type: 转录器类型，目前支持 "whisper"
            **kwargs: 传递给转录器的参数
            
        Returns:
            BaseTranscriber: 转录器实例
        """
        if transcriber_type.lower() == "whisper":
            return WhisperTranscriber(**kwargs)
        else:
            raise ValueError(f"不支持的转录器类型: {transcriber_type}") 