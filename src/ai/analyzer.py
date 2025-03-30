#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
# import torch  # 注释掉torch导入
import logging
from logging_config import LoggingConfig
from pathlib import Path

class Segment:
    """音频段落信息结构"""
    def __init__(self, start, end, text="", speaker=None, confidence=0.0):
        self.start = start  # 开始时间（秒）
        self.end = end      # 结束时间（秒）
        self.text = text    # 文本内容
        self.speaker = speaker  # 说话人（如果有）
        self.confidence = confidence  # 置信度

    @property
    def duration(self):
        """获取段落持续时间"""
        return self.end - self.start
    
    def __str__(self):
        speaker_info = f"[{self.speaker}] " if self.speaker else ""
        return f"{speaker_info}[{self.start:.2f}-{self.end:.2f}]: {self.text}"
    
    def __repr__(self):
        return (f"Segment(start={self.start:.2f}, end={self.end:.2f}, "
                f"text='{self.text[:20]}...', speaker={self.speaker})")
    
    def to_dict(self):
        """转为字典表示"""
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
            "confidence": self.confidence,
            "duration": self.duration
        }

class ContentAnalyzer:
    """音频内容分析器"""
    
    def __init__(self):
        self.logger = LoggingConfig.get_logger(__name__)
    
    def analyze_transcript(self, transcript):
        """
        分析转录文本
        
        Args:
            transcript: 转录文本
            
        Returns:
            dict: 文本分析结果
        """
        if not transcript:
            self.logger.warning("转录文本为空，无法进行分析")
            return {"error": "转录文本为空"}
        
        # 文本统计
        word_count = len(transcript.split())
        char_count = len(transcript.replace(" ", ""))
        sentence_count = len(re.split(r'[.!?。！？]', transcript))
        
        # 关键词提取（简化版）
        keywords = self._extract_keywords(transcript)
        
        # 情感分析不再使用，返回基本信息
        sentiment = {"label": "unknown", "score": 0}
        
        return {
            "word_count": word_count,
            "char_count": char_count,
            "sentence_count": sentence_count,
            "keywords": keywords,
            "sentiment": sentiment
        }
    
    def _extract_keywords(self, text, max_keywords=5):
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            max_keywords: 最大关键词数量
            
        Returns:
            list: 关键词列表
        """
        try:
            # 优先使用jieba关键词提取（中文友好）
            import jieba.analyse
            return jieba.analyse.extract_tags(text, topK=max_keywords)
        except ImportError:
            # 回退到简单的频率统计
            self.logger.debug("无法导入jieba，使用简单词频统计提取关键词")
            words = re.findall(r'\w+', text.lower())
            # 过滤停用词
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with'}
            word_freq = {}
            for word in words:
                if word not in stopwords and len(word) > 1:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 按频率排序
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, _ in sorted_words[:max_keywords]]
    
    def _analyze_sentiment(self, text):
        """
        简单的情感分析 - 已弃用，使用云API不需要本地情感分析
        
        Args:
            text: 输入文本
            
        Returns:
            dict: 情感分析结果
        """
        self.logger.debug("情感分析功能已弃用，返回默认结果")
        return {"label": "unknown", "score": 0}

class SpeakerDiarization:
    """说话人分割类 - 已弃用，使用云API不需要本地说话人分割"""
    
    def __init__(self, model_name=None, device=None):
        """
        初始化说话人分割模型
        
        Args:
            model_name: 模型名称，默认使用推荐模型
            device: 计算设备，None为自动检测
        """
        self.logger = LoggingConfig.get_logger(__name__)
        self.model_name = model_name or "pyannote/speaker-diarization"
        self.device = "cpu"  # 固定为CPU，不再使用GPU
        self.model = None
        self.logger.info("说话人分割功能已弃用，使用云API不需要本地说话人分割")
    
    def load_model(self):
        """加载说话人分割模型 - 已弃用"""
        self.logger.warning("说话人分割功能已弃用，不会加载模型")
        return False
    
    def process(self, audio_path, min_speakers=1, max_speakers=None):
        """
        处理音频文件，识别不同说话人 - 已弃用
        
        Args:
            audio_path: 音频文件路径
            min_speakers: 最小说话人数
            max_speakers: 最大说话人数（None为自动检测）
            
        Returns:
            list: 空列表，功能已弃用
        """
        self.logger.warning("说话人分割功能已弃用，返回空结果")
        return []
    
    def merge_with_transcript(self, diarization_results, transcript_segments):
        """
        将说话人分割结果与转录文本合并 - 已弃用
        
        Args:
            diarization_results: 说话人分割结果
            transcript_segments: 转录文本分段
            
        Returns:
            list: 原始文本分段，不附加说话人信息
        """
        self.logger.warning("说话人分割功能已弃用，返回原始文本分段")
        # 简单转换为Segment对象
        segments = []
        for ts in transcript_segments:
            segments.append(Segment(
                start=ts.get("start", 0),
                end=ts.get("end", 0),
                text=ts.get("text", ""),
                confidence=ts.get("confidence", 0.0)
            ))
        return segments 