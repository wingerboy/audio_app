#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
# import torch  # 注释掉torch导入
import logging
import concurrent.futures
from pathlib import Path
from typing import Dict, Any, Optional
from src.utils.logging_config import LoggingConfig

import json
import time
import threading
import requests
import uuid
import tempfile

# 设置日志
logger = LoggingConfig.setup_logging(log_level=logging.INFO)

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
        # 使用标准logging模块
        self.logger = logging.getLogger(__name__)
    
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


class DashScopeTranscriber(BaseTranscriber):
    """使用达摩院DashScope转录服务的转录器"""
    
    def __init__(self, api_key=None, oss_access_key_id=None, oss_access_key_secret=None, model='paraformer-v1'):
        """
        初始化DashScope转录器
        
        Args:
            api_key: DashScope API密钥
            oss_access_key_id: 阿里云OSS访问密钥ID
            oss_access_key_secret: 阿里云OSS访问密钥Secret
            model: 使用的模型，默认为'paraformer-v1'
        """
        super().__init__()
        # from dotenv import load_dotenv
        # load_dotenv()
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.oss_access_key_id = oss_access_key_id or os.environ.get("ALIYUN_ACCESS_KEY_ID")
        self.oss_access_key_secret = oss_access_key_secret or os.environ.get("ALIYUN_ACCESS_KEY_SECRET")
        self.model = model
        self.bucket_name = 'wingerboy-audio-app-online'
        self.endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
        self.region = "cn-hangzhou"
        
        self.logger.info(f"初始化DashScope转录器: 模型={model}")
        
        if not self.api_key:
            self.logger.warning("未设置DashScope API密钥，请在环境变量或初始化参数中设置")
        
        if not self.oss_access_key_id or not self.oss_access_key_secret:
            self.logger.warning("未设置OSS访问密钥，请在环境变量或初始化参数中设置")
    
    def _upload_to_oss(self, audio_path):
        """
        将音频文件上传到OSS并返回签名URL
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            str: 签名后的OSS URL
        """
        try:
            import oss2
            from oss2.credentials import StaticCredentialsProvider
            
            # 禁用系统代理设置
            original_http_proxy = os.environ.get('http_proxy')
            original_https_proxy = os.environ.get('https_proxy')
            
            if 'http_proxy' in os.environ:
                del os.environ['http_proxy']
            if 'https_proxy' in os.environ:
                del os.environ['https_proxy']
            
            # 创建凭证提供者
            creds = StaticCredentialsProvider(
                access_key_id=self.oss_access_key_id,
                access_key_secret=self.oss_access_key_secret
            )
            
            # 创建认证对象
            auth = oss2.ProviderAuthV4(creds)
            
            # 创建Bucket对象
            bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name, region=self.region)
            
            # 生成唯一的对象名
            object_name = f"audio_{uuid.uuid4().hex}_{os.path.basename(audio_path)}"
            
            # 上传文件
            self.logger.info(f"正在上传音频文件到OSS: {object_name}")
            result = bucket.put_object_from_file(object_name, audio_path)
            
            if result.status != 200:
                self.logger.error(f"上传失败，状态码: {result.status}")
                return None
            
            # 生成签名URL，有效期1小时
            download_url = bucket.sign_url('GET', object_name, 3600)
            
            self.logger.info(f"文件上传成功，签名URL: {download_url}")
            
            # 还原代理设置
            if original_http_proxy:
                os.environ['http_proxy'] = original_http_proxy
            if original_https_proxy:
                os.environ['https_proxy'] = original_https_proxy
                
            return download_url
            
        except Exception as e:
            self.logger.exception(f"上传文件到OSS时出错: {str(e)}")
            # 确保即使出错也还原代理设置
            if 'original_http_proxy' in locals() and original_http_proxy:
                os.environ['http_proxy'] = original_http_proxy
            if 'original_https_proxy' in locals() and original_https_proxy:
                os.environ['https_proxy'] = original_https_proxy
            return None
    
    def _get_dashscope_transcription(self, file_url):
        """
        使用DashScope API转录音频
        
        Args:
            file_url: OSS文件URL
            
        Returns:
            dict: 转录结果
        """
        try:
            import dashscope
            
            # 设置API密钥
            dashscope.api_key = self.api_key
            
            # 提交异步转录任务
            self.logger.info("提交DashScope转录任务")
            task_response = dashscope.audio.asr.Transcription.async_call(
                model=self.model,
                file_urls=[file_url]
            )
            
            # 检查任务提交状态
            if not task_response.status_code == 200:
                error_msg = f"提交任务失败: {task_response.code}, {task_response.message}"
                self.logger.error(error_msg)
                return None
            
            # 等待任务完成
            task_id = task_response.output.task_id
            self.logger.info(f"任务提交成功，任务ID: {task_id}，等待转录结果...")
            
            # 等待转录完成
            transcribe_response = dashscope.audio.asr.Transcription.wait(task=task_id)
            
            # 检查转录状态
            if transcribe_response.status_code != 200 or transcribe_response.output.get('task_status') != 'SUCCEEDED':
                error_msg = f"转录失败: {transcribe_response.output.get('task_status', 'UNKNOWN')}"
                self.logger.error(error_msg)
                return None
            
            # 获取转录结果URL
            results = transcribe_response.output.get('results', [])
            if not results or 'transcription_url' not in results[0]:
                self.logger.error("未找到转录结果URL")
                return None
            
            transcription_url = results[0]['transcription_url']
            
            # 下载转录结果
            self.logger.info(f"下载转录结果: {transcription_url}")
            response = requests.get(transcription_url)
            
            if response.status_code != 200:
                self.logger.error(f"下载转录结果失败: {response.status_code}")
                return None
            
            # 解析JSON结果
            try:
                return response.json()
            except json.JSONDecodeError:
                self.logger.error("无法解析转录结果JSON")
                return None
                
        except Exception as e:
            self.logger.exception(f"使用DashScope转录时出错: {str(e)}")
            return None
    
    def _parse_dashscope_result(self, result):
        """
        解析DashScope转录结果
        
        Args:
            result: DashScope转录结果JSON
            
        Returns:
            TranscriptionResult: 转录结果对象
        """
        if not result or 'transcripts' not in result:
            return TranscriptionResult("", 0.0, {"error": "无效的转录结果"})
        
        try:
            # 获取主要转录文本
            transcript = result['transcripts'][0] if result['transcripts'] else None
            
            if not transcript:
                return TranscriptionResult("", 0.0, {"error": "无转录信息"})
            
            # 获取完整文本
            text = transcript.get('text', '')
            
            # 基于词级别分割句子
            segments = []
            all_words = []
            
            # 获取所有词级别信息
            for sentence in transcript.get('sentences', []):
                words = sentence.get('words', [])
                all_words.extend(words)
            
            if not all_words:
                # 如果没有词级别信息，退回到使用句子级别信息
                for sentence in transcript.get('sentences', []):
                    begin_time_sec = sentence.get('begin_time', 0) / 1000  # 转换为秒
                    end_time_sec = sentence.get('end_time', 0) / 1000  # 转换为秒
                    sentence_text = sentence.get('text', '')
                    
                    segments.append({
                        "start": begin_time_sec,
                        "end": end_time_sec,
                        "text": sentence_text
                    })
            else:
                # 基于句子自然结束点（句号等）分段，同时考虑最大长度限制
                current_sentence = []
                sentence_start_time = all_words[0]['begin_time'] / 1000 if all_words else 0
                
                MAX_SENTENCE_DURATION = 10  # 最大句子时长为10秒
                
                # 定义标点符号集合
                end_punctuation = ['。', '！', '？', '.', '!', '?']  # 结束标点（句子自然终结点）
                other_punctuation = ['，', ',', '；', ';', '：', ':']  # 其他标点（仅在句子过长时使用）
                
                for word in all_words:
                    word_text = word.get('text', '')
                    word_punctuation = word.get('punctuation', '')
                    word_begin_time = word.get('begin_time', 0) / 1000  # 转换为秒
                    word_end_time = word.get('end_time', 0) / 1000  # 转换为秒
                    
                    current_sentence.append(word)
                    current_duration = word_end_time - sentence_start_time
                    
                    # 判断是否应该结束当前句子
                    should_end_sentence = False
                    
                    # 条件1: 遇到结束标点(句号、问号、感叹号)时，总是分割句子
                    if word_punctuation in end_punctuation:
                        should_end_sentence = True
                    
                    # 条件2: 如果句子超过最大长度(10秒)，且遇到其他标点(逗号等)时分割
                    if current_duration >= MAX_SENTENCE_DURATION and word_punctuation in other_punctuation:
                        should_end_sentence = True
                    
                    # 条件3: 如果是最后一个词，结束当前句子
                    if word is all_words[-1]:
                        should_end_sentence = True
                    
                    if should_end_sentence:
                        # 构建句子文本
                        sentence_text = ''.join([w.get('text', '') + w.get('punctuation', '') for w in current_sentence])
                        sentence_end_time = word_end_time
                        
                        # 添加到分段
                        segments.append({
                            "start": sentence_start_time,
                            "end": sentence_end_time,
                            "text": sentence_text
                        })
                        
                        # 重置当前句子
                        current_sentence = []
                        if word is not all_words[-1]:  # 如果不是最后一个词
                            sentence_start_time = all_words[all_words.index(word) + 1].get('begin_time', 0) / 1000
                
                # 处理最后一个可能未结束的句子 - 这部分可能已经在循环中处理了，但保留以防万一
                if current_sentence:
                    sentence_text = ''.join([w.get('text', '') + w.get('punctuation', '') for w in current_sentence])
                    sentence_end_time = current_sentence[-1].get('end_time', 0) / 1000
                    
                    segments.append({
                        "start": sentence_start_time,
                        "end": sentence_end_time,
                        "text": sentence_text
                    })
            
            self.logger.info(f"转录完成: 共{len(segments)}个段落")
            
            # 计算粗略的置信度（这里只是一个示例，实际上DashScope没有返回明确的置信度）
            confidence = 0.95
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                metadata={
                    "segments": segments,
                    "language": "auto",  # DashScope会自动检测语言
                    "words": all_words
                }
            )
            
        except Exception as e:
            self.logger.exception(f"解析转录结果时出错: {str(e)}")
            return TranscriptionResult("", 0.0, {"error": str(e)})
    
    def transcribe(self, audio_path):
        """
        使用DashScope转录音频
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            TranscriptionResult: 转录结果
        """
        if not os.path.exists(audio_path):
            self.logger.error(f"音频文件不存在: {audio_path}")
            return TranscriptionResult("", 0.0, {"error": "文件不存在"})
        
        try:
            # 1. 上传文件到OSS
            file_url = self._upload_to_oss(audio_path)
            if not file_url:
                return TranscriptionResult("", 0.0, {"error": "上传文件到OSS失败"})
            
            # 2. 使用DashScope转录
            result = self._get_dashscope_transcription(file_url)
            if not result:
                return TranscriptionResult("", 0.0, {"error": "DashScope转录失败"})
            
            # 3. 解析结果
            return self._parse_dashscope_result(result)
            
        except Exception as e:
            self.logger.exception(f"转录文件 {audio_path} 时出错: {str(e)}")
            return TranscriptionResult("", 0.0, {"error": str(e)})


class TranscriberFactory:
    """转录器工厂类"""
    
    @classmethod
    def create(cls, transcriber_type, **kwargs):
        """
        创建转录器实例
        
        Args:
            transcriber_type: 转录器类型名称
            **kwargs: 传递给转录器构造函数的参数
            
        Returns:
            BaseTranscriber: 转录器实例
        """
        logger = logging.getLogger(__name__)
        
        # 通过类型名称创建转录器
        if transcriber_type == "dashscope":
            return DashScopeTranscriber(**kwargs)
        # elif transcriber_type == "aliyun_nls":
        #     return AliyunNlsTranscriber(**kwargs)
        # 不再支持Whisper转录器
        # elif transcriber_type == "whisper":
        #     return WhisperTranscriber(**kwargs)
        else:
            # 默认使用DashScope转录器
            logger.warning(f"未知的转录器类型 '{transcriber_type}'，使用默认的DashScope转录器")
            return DashScopeTranscriber(**kwargs)
