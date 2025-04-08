import os
import subprocess
import tempfile
from pydub import AudioSegment
import shutil
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from src.utils.logging_config import LoggingConfig

class AudioProcessor:
    def __init__(self, use_disk_processing=True, chunk_size_mb=200, max_workers=2):
        """
        初始化音频处理器
        
        Args:
            use_disk_processing (bool): 是否使用硬盘处理大文件
            chunk_size_mb (int): 处理大文件时的分块大小(MB)
            max_workers (int): 并行处理的最大线程数
        """
        self.temp_dir = tempfile.mkdtemp()
        self.use_disk_processing = use_disk_processing
        self.chunk_size_mb = chunk_size_mb
        self.max_workers = max_workers
        self.logger = LoggingConfig.get_logger(__name__)
        self._check_ffmpeg()
        
        # 记录大文件处理配置
        self.logger.info(f"AudioProcessor初始化: 硬盘处理={use_disk_processing}, 分块大小={chunk_size_mb}MB, 最大线程数={max_workers}")
    
    def _check_ffmpeg(self):
        """检查FFmpeg是否已安装并可被pydub访问"""
        # 尝试设置ffmpeg路径
        self.has_ffmpeg = False
        try:
            # 尝试使用subprocess检测ffmpeg
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=False)
            self.has_ffmpeg = True
        except (FileNotFoundError, subprocess.SubprocessError):
            # 尝试为pydub设置ffmpeg路径
            try:
                # 查找可能的ffmpeg路径
                possible_paths = [
                    "ffmpeg",
                    r"C:\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
                    os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),
                    os.path.join(os.path.expanduser("~"), "ffmpeg", "ffmpeg.exe"),
                    os.path.join(os.path.expanduser("~"), "ffmpeg", "bin", "ffmpeg.exe"),
                    r"C:\Users\Administrator\ffmpeg\ffmpeg.exe",
                    r"C:\Users\Administrator\ffmpeg\bin\ffmpeg.exe"
                ]
                
                for path in possible_paths:
                    try:
                        if os.path.exists(path):
                            AudioSegment.converter = path
                            self.has_ffmpeg = True
                            break
                    except:
                        continue
            except:
                pass

    def extract_audio(self, file_path, progress_callback=None):
        """
        从文件中提取音频
        
        Args:
            file_path: 文件路径
            progress_callback: 进度回调函数
            
        Returns:
            提取出的音频文件路径，如果失败则返回None
        """
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return None
            
        file_basename = os.path.basename(file_path)
        file_name, file_ext = os.path.splitext(file_basename)
        
        # 输出路径
        audio_ext = ".wav"  # 使用WAV格式以保持高质量
        output_audio_path = os.path.join(self.temp_dir, f"{file_name}{audio_ext}")
        
        # 检查文件是否已经是音频文件
        audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.opus']
        if file_ext.lower() in audio_extensions:
            self.logger.info(f"文件已经是音频格式: {file_ext}")
            # 复制文件到临时目录
            shutil.copy2(file_path, output_audio_path)
            return output_audio_path
            
        # 非音频文件，尝试提取
        try:
            self.logger.info(f"从{file_ext}文件中提取音频: {file_basename}")
            
            # 使用FFmpeg提取音频
            ffmpeg_cmd = [
                "ffmpeg", "-i", file_path, 
                "-vn",  # 不要视频
                "-acodec", "pcm_s16le",  # 使用无损编码
                "-ar", "44100",  # 采样率
                "-ac", "2",  # 双声道
                "-y",  # 覆盖已存在文件
                output_audio_path
            ]
            
            self.logger.debug(f"执行FFmpeg命令: {' '.join(ffmpeg_cmd)}")
            
            # 执行命令并处理进度
            process = subprocess.Popen(
                ffmpeg_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True
            )
            
            # 读取FFmpeg输出
            for line in process.stderr:
                if progress_callback and "time=" in line:
                    # 尝试解析FFmpeg进度
                    try:
                        time_str = line.split("time=")[1].split()[0]
                        h, m, s = time_str.split(":")
                        current_time = float(h) * 3600 + float(m) * 60 + float(s)
                        # 文件总长度未知，给出近似进度
                        progress_callback("提取音频中", 50)
                    except (ValueError, IndexError):
                        pass
            
            # 等待进程完成
            process.wait()
            
            # 检查是否成功
            if process.returncode != 0:
                self.logger.error(f"FFmpeg提取音频失败，错误码: {process.returncode}")
                return None
                
            if not os.path.exists(output_audio_path):
                self.logger.error(f"输出音频文件不存在: {output_audio_path}")
                return None
                
            self.logger.info(f"音频提取成功: {output_audio_path}")
            return output_audio_path
            
        except Exception as e:
            self.logger.exception(f"提取音频时发生错误: {str(e)}")
            return None

    def split_audio(self, audio_path, segments, output_dir, output_format="mp3", quality="medium", progress_callback=None):
        """
        根据时间段列表分割音频
        
        Args:
            audio_path (str): 音频文件路径
            segments (list): 包含start和end时间的字典列表 [{"start": 0, "end": 10, "text": "..."}]
            output_dir (str): 输出目录
            output_format (str): 输出格式 (mp3, wav, ogg)
            quality (str): 输出质量 (low, medium, high)
            progress_callback (function): 进度回调函数
            
        Returns:
            list: 输出文件路径列表
        """
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置质量参数
        quality_settings = {
            "low": {"mp3": "96k", "wav": "16", "ogg": "1"},
            "medium": {"mp3": "192k", "wav": "24", "ogg": "5"},
            "high": {"mp3": "320k", "wav": "32", "ogg": "9"}
        }
        
        bitrate = quality_settings.get(quality, quality_settings["medium"]).get(output_format, "192k")
        
        # 计算总段数用于进度计算
        total_segments = len(segments)
        
        try:
            # 加载音频文件
            if progress_callback:
                progress_callback("加载音频文件...", 20)
            
            # 使用硬盘处理大文件
            if self.use_disk_processing and os.path.getsize(audio_path) > self.chunk_size_mb * 1024 * 1024:
                return self._split_large_audio(audio_path, segments, output_dir, output_format, bitrate, progress_callback)
            
            # 标准处理方式
            audio = AudioSegment.from_file(audio_path)
            
            if progress_callback:
                progress_callback("开始分割音频...", 30)
            
            output_files = []
            
            # 使用多线程处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建任务列表
                futures = []
                for i, segment in enumerate(segments):
                    futures.append(
                        executor.submit(
                            self._process_segment,
                            audio=audio,
                            segment=segment,
                            index=i,
                            output_dir=output_dir,
                            output_format=output_format,
                            bitrate=bitrate
                        )
                    )
                
                # 等待所有任务完成并更新进度
                for i, future in enumerate(futures):
                    try:
                        output_file = future.result()
                        output_files.append(output_file)
                        if progress_callback:
                            progress = 30 + (i + 1) / total_segments * 60
                            progress_callback(f"已处理 {i+1}/{total_segments} 个片段", progress)
                    except Exception as e:
                        print(f"处理片段 {i} 时出错: {str(e)}")
            
            if progress_callback:
                progress_callback("分割完成！", 100)
            
            return output_files
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"分割失败: {str(e)}", 0)
            raise Exception(f"分割音频失败: {str(e)}")
    
    def _process_segment(self, audio, segment, index, output_dir, output_format, bitrate):
        """处理单个音频片段"""
        start_ms = int(segment["start"] * 1000)
        end_ms = int(segment["end"] * 1000)
        
        # 确保开始时间不小于0
        start_ms = max(0, start_ms)
        
        # 确保结束时间不超过音频长度
        if end_ms > len(audio):
            end_ms = len(audio)
        
        # 提取片段
        segment_audio = audio[start_ms:end_ms]
        
        # 创建安全的文件名
        safe_filename = f"segment_{index+1:03d}_{start_ms/1000:.1f}-{end_ms/1000:.1f}"
        
        # 如果文本存在，添加一部分到文件名
        if "text" in segment and segment["text"]:
            # 清理文本使其适合作为文件名
            text = segment["text"].strip()
            text = ''.join(c for c in text if c.isalnum() or c.isspace())
            text = text[:30]  # 限制长度
            if text:
                safe_filename = f"{safe_filename}_{text}"
        
        # 创建输出文件路径
        output_file = os.path.join(output_dir, f"{safe_filename}.{output_format}")
        
        # 导出音频
        if output_format == "mp3":
            segment_audio.export(output_file, format=output_format, bitrate=bitrate)
        elif output_format == "wav":
            segment_audio.export(output_file, format=output_format, parameters=["-sample_fmt", f"s{bitrate}"])
        else:
            segment_audio.export(output_file, format=output_format, parameters=["-q:a", bitrate])
        
        return output_file
    
    def _split_large_audio(self, audio_path, segments, output_dir, output_format, bitrate, progress_callback=None):
        """使用FFmpeg直接分割大型音频文件，避免加载整个文件到内存"""
        output_files = []
        
        # 根据总段数计算进度增量
        total_segments = len(segments)
        progress_increment = 60 / total_segments if total_segments > 0 else 0
        current_progress = 30
        
        if progress_callback:
            progress_callback("使用磁盘处理大型音频文件...", current_progress)
        
        for i, segment in enumerate(segments):
            try:
                start_time = segment["start"]
                end_time = segment["end"]
                duration = end_time - start_time
                
                # 创建安全的文件名
                safe_filename = f"segment_{i+1:03d}_{start_time:.1f}-{end_time:.1f}"
                
                # 如果文本存在，添加一部分到文件名
                if "text" in segment and segment["text"]:
                    # 清理文本使其适合作为文件名
                    text = segment["text"].strip()
                    text = ''.join(c for c in text if c.isalnum() or c.isspace())
                    text = text[:30]  # 限制长度
                    if text:
                        safe_filename = f"{safe_filename}_{text}"
                
                # 创建输出文件路径
                output_file = os.path.join(output_dir, f"{safe_filename}.{output_format}")
                
                # 使用FFmpeg直接切割
                cmd = [
                    "ffmpeg",
                    "-i", audio_path,
                    "-ss", str(start_time),
                    "-t", str(duration),
                    "-acodec"
                ]
                
                # 添加格式特定的参数
                if output_format == "mp3":
                    cmd.extend(["libmp3lame", "-ab", bitrate])
                elif output_format == "wav":
                    cmd.extend(["pcm_s16le", "-sample_fmt", f"s{bitrate}"])
                elif output_format == "ogg":
                    cmd.extend(["libvorbis", "-q:a", bitrate])
                
                cmd.extend(["-y", output_file])
                
                # 执行命令
                subprocess.run(cmd, check=True, capture_output=True)
                
                output_files.append(output_file)
                
                # 更新进度
                current_progress += progress_increment
                if progress_callback:
                    progress_callback(f"已处理 {i+1}/{total_segments} 个片段", current_progress)
                
            except Exception as e:
                print(f"处理片段 {i} 时出错: {str(e)}")
        
        if progress_callback:
            progress_callback("分割完成！", 100)
        
        return output_files
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理临时文件时出错: {str(e)}") 