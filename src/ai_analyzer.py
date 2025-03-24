import os
import numpy as np
import torch
from transformers import pipeline
import re
import logging
from logging_config import LoggingConfig

class AudioAnalyzer:
    def __init__(self, model_size="base"):
        """
        使用指定大小的Whisper模型初始化音频分析器
        
        Args:
            model_size: 模型大小，可选tiny/base/small/medium/large
        """
        # 配置日志
        self.logger = LoggingConfig.get_logger(__name__)
        
        # 映射模型大小到实际模型名称
        size_to_model = {
            "tiny": "openai/whisper-tiny",
            "base": "openai/whisper-base",
            "small": "openai/whisper-small",
            "medium": "openai/whisper-medium",
            "large": "openai/whisper-large-v2",
        }
        
        model_name = size_to_model.get(model_size, "openai/whisper-base")
        self.model_name = model_name
        
        # 详细检查GPU状态
        self.logger.info(f"初始化AI分析器，模型: {model_name}")
        self.logger.debug(f"CUDA是否可用: {torch.cuda.is_available()}")
        self.logger.debug(f"PyTorch版本: {torch.__version__}")
        
        if torch.cuda.is_available():
            self.device = "cuda"
            self.logger.info(f"使用GPU进行音频分析")
            self.logger.debug(f"GPU数量: {torch.cuda.device_count()}")
            self.logger.debug(f"GPU型号: {torch.cuda.get_device_name(0)}")
            self.logger.debug(f"当前选择的GPU: {torch.cuda.current_device()}")
            try:
                self.logger.debug(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024 / 1024 / 1024:.2f} GB")
            except Exception as e:
                self.logger.warning(f"获取GPU内存信息失败: {e}")
        else:
            self.device = "cpu"
            self.logger.warning("未检测到可用的GPU。转录将使用CPU，这可能会很慢。")
            self.logger.info("如果您有NVIDIA GPU，请确保正确安装了CUDA和相应版本的PyTorch。")
            
            # 尝试诊断CUDA问题
            try:
                import subprocess
                self.logger.debug("尝试运行nvidia-smi检查GPU状态...")
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.logger.debug("nvidia-smi输出成功，可能是CUDA版本不匹配或PyTorch配置问题")
                else:
                    self.logger.debug(f"nvidia-smi错误: {result.stderr}")
            except Exception as e:
                self.logger.debug(f"无法执行nvidia-smi: {e}")
        
        self.logger.info(f"音频分析将使用设备: {self.device}")
        self.pipe = None
    
    def _ensure_model_loaded(self, chunk_length_s=30):
        """确保模型已加载"""
        if self.pipe is None:
            try:
                self.logger.info(f"加载Whisper模型: {self.model_name}")
                
                # 检查模型下载路径
                model_path = os.path.expanduser("~/.cache/huggingface/hub")
                if not os.path.exists(model_path):
                    os.makedirs(model_path, exist_ok=True)
                    self.logger.debug(f"创建模型缓存目录: {model_path}")
                
                self.logger.debug(f"使用设备: {self.device}，分块大小: {chunk_length_s}秒")
                self.pipe = pipeline(
                    "automatic-speech-recognition",
                    model=self.model_name,
                    device=self.device,
                    chunk_length_s=chunk_length_s,
                    return_timestamps=True
                )
                self.logger.info("模型加载成功")
            except Exception as e:
                self.logger.error(f"加载模型时出错: {str(e)}")
                # 尝试使用CPU作为后备
                if self.device != "cpu":
                    self.logger.warning("尝试使用CPU作为备选...")
                    self.device = "cpu"
                    try:
                        self.pipe = pipeline(
                            "automatic-speech-recognition",
                            model=self.model_name,
                            device=self.device,
                            chunk_length_s=chunk_length_s,
                            return_timestamps=True
                        )
                        self.logger.info("使用CPU模式加载模型成功")
                    except Exception as cpu_error:
                        self.logger.error(f"CPU模式加载失败: {str(cpu_error)}")
                        raise RuntimeError(f"无法加载模型: {str(e)} 且 CPU后备也失败: {str(cpu_error)}")
                else:
                    raise RuntimeError(f"无法加载模型: {str(e)}")
        return self.pipe
    
    def transcribe_audio(self, audio_path, language=None, progress_callback=None):
        """
        转录音频文件
        
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
            self.logger.info(f"开始转录音频: {audio_path}")
            if language:
                self.logger.info(f"指定语言: {language}")
                
            # 确保模型已加载
            self._ensure_model_loaded()
            
            # 报告转录开始
            if progress_callback:
                progress_callback("开始转录音频...", 0)
                
            # 转录设置
            transcribe_params = {
                "task": "transcribe",
            }
            
            # 设置语言
            if language:
                transcribe_params["language"] = language
                
            # 进行转录
            self.logger.debug("调用模型进行转录...")
            result = self.pipe(
                audio_path,
                return_timestamps=True,
                generate_kwargs=transcribe_params
            )
            
            # 提取结果
            result_text = result.get("text", "")
            chunks = result.get("chunks", [])
            
            # 处理时间戳分段
            segments = []
            if "chunks" in result:
                for i, chunk in enumerate(result["chunks"]):
                    segments.append({
                        "id": i,
                        "start": chunk["timestamp"][0],
                        "end": chunk["timestamp"][1],
                        "text": chunk["text"].strip()
                    })
            
            self.logger.info(f"转录完成，识别到 {len(segments)} 个片段")
            
            # 分析分段
            if progress_callback:
                progress_callback("后处理转录结果...", 90)
                
            # 返回结果
            return {
                "text": result_text,
                "segments": segments
            }
            
        except Exception as e:
            self.logger.exception(f"转录过程中出错: {str(e)}")
            return {"text": "", "segments": []}
    
    def find_sentence_breaks(self, transcription, max_interval=60, min_interval=10, preserve_sentences=True):
        """
        在最小和最大间隔之间找到逻辑句子断点，同时保持句子完整性
        
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
            
        # 如果只有一个片段且较短，直接返回
        if len(original_segments) == 1 and original_segments[0]["end"] - original_segments[0]["start"] <= max_interval:
            return original_segments
            
        # 重新组织片段，确保更好的断句
        merged_segments = []
        current_segment = {
            "start": original_segments[0]["start"],
            "end": original_segments[0]["end"],
            "text": original_segments[0]["text"]
        }
        
        # 句子结束标记正则表达式
        sentence_end_markers = r'[。！？.!?;；]'
        
        for i in range(1, len(original_segments)):
            segment = original_segments[i]
            duration = segment["end"] - current_segment["start"]
            
            # 检查是否应该开始新片段
            should_split = duration >= max_interval
            
            # 如果需要保留句子完整性，检查当前文本是否以句子结束符结尾
            if preserve_sentences and not should_split and duration >= min_interval:
                prev_text = current_segment["text"].strip()
                # 如果当前文本以句子结束符结尾，考虑分割
                if prev_text and re.search(f'{sentence_end_markers}\\s*$', prev_text):
                    should_split = True
            
            if should_split:
                # 保存当前片段并开始新片段
                merged_segments.append(current_segment)
                current_segment = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                }
            else:
                # 扩展当前片段
                current_segment["end"] = segment["end"]
                current_segment["text"] += " " + segment["text"]
        
        # 添加最后一个片段
        if current_segment:
            merged_segments.append(current_segment)
        
        return merged_segments
    
    def filter_segments_by_keywords(self, transcription, keywords=None):
        """
        根据关键词过滤分段
        
        Args:
            transcription: 包含分段的转录结果
            keywords: 要匹配的关键词列表
            
        Returns:
            过滤后的转录结果
        """
        if not keywords or not isinstance(keywords, list) or len(keywords) == 0:
            self.logger.debug("未提供关键词，跳过过滤")
            return transcription
            
        # 提取分段
        segments = transcription.get("segments", [])
        if not segments:
            self.logger.warning("没有找到可过滤的分段")
            return transcription
            
        self.logger.info(f"使用 {len(keywords)} 个关键词过滤 {len(segments)} 个分段")
        
        # 准备正则表达式
        patterns = []
        for keyword in keywords:
            keyword = keyword.strip()
            if keyword:
                # 转义特殊字符
                escaped_keyword = re.escape(keyword)
                # 创建不区分大小写的模式
                pattern = re.compile(escaped_keyword, re.IGNORECASE)
                patterns.append(pattern)
                
        # 过滤分段
        filtered_segments = []
        for segment in segments:
            text = segment.get("text", "")
            match_found = any(pattern.search(text) for pattern in patterns)
            
            if match_found:
                filtered_segments.append(segment)
                
        # 更新文本
        full_text = " ".join([s.get("text", "") for s in filtered_segments])
        
        self.logger.info(f"过滤后保留了 {len(filtered_segments)} 个分段")
        
        # 返回结果
        return {
            "text": full_text,
            "segments": filtered_segments
        } 