#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import torch
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
        
        # 情感分析（如果可用）
        sentiment = self._analyze_sentiment(transcript)
        
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
        简单的情感分析
        
        Args:
            text: 输入文本
            
        Returns:
            dict: 情感分析结果
        """
        try:
            from transformers import pipeline
            
            self.logger.info("使用transformers进行情感分析")
            # 使用预训练的情感分析模型
            sentiment_analyzer = pipeline("sentiment-analysis")
            result = sentiment_analyzer(text[:512])[0]  # 限制文本长度
            
            return {
                "label": result["label"],
                "score": result["score"]
            }
        except (ImportError, Exception) as e:
            self.logger.debug(f"无法使用transformers进行情感分析: {str(e)}")
            # 如果无法使用高级情感分析，返回空结果
            return {"label": "unknown", "score": 0}

class SpeakerDiarization:
    """说话人分割类，用于识别不同说话人的音频段落"""
    
    def __init__(self, model_name=None, device=None):
        """
        初始化说话人分割模型
        
        Args:
            model_name: 模型名称，默认使用推荐模型
            device: 计算设备，None为自动检测
        """
        self.logger = LoggingConfig.get_logger(__name__)
        self.model_name = model_name or "pyannote/speaker-diarization"
        
        # 设置设备
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        self.model = None
        self.logger.info(f"初始化说话人分割: 模型={self.model_name}, 设备={self.device}")
    
    def load_model(self):
        """加载说话人分割模型"""
        if self.model is not None:
            return
            
        try:
            self.logger.info(f"正在加载说话人分割模型...")
            from pyannote.audio import Pipeline
            
            # 检查是否有访问权限（Hugging Face令牌）
            hf_token = os.environ.get("HF_TOKEN")
            
            self.model = Pipeline.from_pretrained(
                self.model_name,
                use_auth_token=hf_token
            ).to(self.device)
            
            self.logger.info(f"说话人分割模型加载完成")
            
        except Exception as e:
            self.logger.error(f"加载说话人分割模型失败: {str(e)}")
            raise RuntimeError(f"加载说话人分割模型失败: {str(e)}")
    
    def process(self, audio_path, min_speakers=1, max_speakers=None):
        """
        处理音频文件，识别不同说话人
        
        Args:
            audio_path: 音频文件路径
            min_speakers: 最小说话人数
            max_speakers: 最大说话人数（None为自动检测）
            
        Returns:
            list: 说话人分割结果，每个元素为 (start, end, speaker_id)
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"音频文件不存在: {audio_path}")
            return []
            
        self.load_model()
        
        try:
            self.logger.info(f"开始说话人分割: {Path(audio_path).name}")
            
            # 设置参数
            diarization_options = {}
            if min_speakers is not None and min_speakers > 0:
                diarization_options["min_speakers"] = min_speakers
            if max_speakers is not None and max_speakers > 0:
                diarization_options["max_speakers"] = max_speakers
                
            # 执行分割
            diarization = self.model(audio_path, **diarization_options)
            
            # 转换结果
            results = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                results.append((turn.start, turn.end, speaker))
            
            self.logger.info(f"说话人分割完成: 识别到 {len(set(speaker for _, _, speaker in results))} 个说话人")
            return results
            
        except Exception as e:
            self.logger.exception(f"说话人分割出错: {str(e)}")
            return []
    
    def merge_with_transcript(self, diarization_results, transcript_segments):
        """
        将说话人分割结果与转录文本合并
        
        Args:
            diarization_results: 说话人分割结果 [(start, end, speaker_id), ...]
            transcript_segments: 转录文本分段 [{"start": start, "end": end, "text": text}, ...]
            
        Returns:
            list: 合并后的段落列表 [Segment对象, ...]
        """
        if not diarization_results or not transcript_segments:
            return []
            
        merged_segments = []
        
        for ts in transcript_segments:
            ts_start = ts.get("start", 0)
            ts_end = ts.get("end", 0)
            ts_text = ts.get("text", "")
            
            # 找出与当前文本段重叠最多的说话人
            speaker_overlaps = {}
            
            for dr_start, dr_end, dr_speaker in diarization_results:
                # 计算重叠
                overlap_start = max(ts_start, dr_start)
                overlap_end = min(ts_end, dr_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > 0:
                    speaker_overlaps[dr_speaker] = speaker_overlaps.get(dr_speaker, 0) + overlap
            
            # 选择重叠最多的说话人
            speaker = None
            if speaker_overlaps:
                speaker = max(speaker_overlaps.items(), key=lambda x: x[1])[0]
            
            # 创建合并后的段落
            segment = Segment(
                start=ts_start,
                end=ts_end,
                text=ts_text,
                speaker=speaker,
                confidence=ts.get("confidence", 0.0)
            )
            
            merged_segments.append(segment)
        
        return merged_segments 