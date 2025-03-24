#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
音频处理和分析模块
提供音频转换、分割、转录和内容分析功能
"""

# 导入各子模块
from . import audio
from . import ai
from . import temp

# 从各子模块导入常用组件用于方便访问
from .audio import AudioConverter, AudioSplitter, SplitOptions, SegmentOptions, AudioUtils
from .ai import TranscriptionResult, WhisperTranscriber, ContentAnalyzer, Segment
from .temp import TempFileManager, get_global_manager, cleanup_global_manager

# 定义公开的API
__all__ = [
    # 子模块
    'audio', 
    'ai', 
    'temp',
    
    # 音频处理组件
    'AudioConverter',
    'AudioSplitter',
    'SplitOptions',
    'SegmentOptions',
    'AudioUtils',
    
    # AI分析组件
    'TranscriptionResult',
    'WhisperTranscriber',
    'ContentAnalyzer',
    'Segment',
    
    # 临时文件管理
    'TempFileManager',
    'get_global_manager',
    'cleanup_global_manager'
] 