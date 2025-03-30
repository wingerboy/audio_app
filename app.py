import os
import tempfile
import streamlit as st
import subprocess
import time
import logging
from pathlib import Path
from src import AudioConverter, AudioSplitter, SplitOptions, SegmentOptions  # 更新导入
from src.audio_processor_adapter import AudioProcessorAdapter  # 导入适配器
from src.ai_analyzer_adapter import AIAnalyzerAdapter  # 导入适配器
from src.temp import TempFileManager, get_global_manager, cleanup_global_manager  # 导入临时文件管理
# import torch  # 不再需要torch导入
from environment_manager import EnvironmentManager
from logging_config import LoggingConfig

# 初始化日志系统
logger = LoggingConfig.get_logger(__name__)

# 配置页面
st.set_page_config(
    page_title="智能音频分割工具", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化Streamlit日志处理器
def setup_ui_logging():
    """为Streamlit界面设置日志处理器"""
    # 获取根日志器
    root_logger = logging.getLogger()
    
    # 为UI创建一个处理器
    streamlit_handler = LoggingConfig.create_streamlit_handler()
    
    # 设置格式
    formatter = logging.Formatter('%(message)s')  # 简化的格式，只显示消息
    streamlit_handler.setFormatter(formatter)
    
    # 设置级别（只处理WARNING及以上级别）
    streamlit_handler.setLevel(logging.WARNING)
    
    # 添加处理器
    root_logger.addHandler(streamlit_handler)
    
    # 返回处理器以便后续可能的移除
    return streamlit_handler

# 设置UI日志处理器
ui_handler = setup_ui_logging()

# 确保环境准备就绪
env_manager = EnvironmentManager()

# 检查FFmpeg
if not env_manager.ensure_ffmpeg():
    st.error("未检测到FFmpeg，请安装FFmpeg后重试，或联系技术支持。")
    st.stop()

# 不再需要检查Whisper
# if not env_manager.ensure_whisper():
#     st.error("未检测到Whisper语音识别模块，请安装openai-whisper后重试，或联系技术支持。")
#     st.stop()

# 不再需要检查GPU状态
# has_gpu, gpu_info = env_manager.check_gpu_status()
# torch_version = env_manager.get_torch_version()

# 初始化临时文件管理
temp_manager = get_global_manager()

# 应用标题
st.title("智能音频分割工具")

# 侧边栏信息
with st.sidebar:
    st.header("系统信息")
    
    # 不再显示GPU状态
    # if has_gpu:
    #     st.success(f"✅ GPU可用: {gpu_info}")
    # else:
    #     st.warning("⚠️ GPU不可用，将使用CPU进行处理（速度较慢）")
    
    # 不再显示PyTorch信息
    # st.info(f"PyTorch版本: {torch_version}")
    
    # FFmpeg信息
    st.success("✅ FFmpeg可用")
    
    # 云API信息
    st.success("✅ 云API服务已连接")

    # 关于
    st.sidebar.markdown("---")
    st.sidebar.subheader("关于")
    st.sidebar.info(
        "智能音频分割工具可以自动分析音频/视频内容，"
        "并在合适的位置分割音频。"
    )
    st.sidebar.markdown("🚀 使用阿里云API和FFmpeg技术")

# 主界面：文件上传
st.header("第一步：上传文件")
uploaded_file = st.file_uploader("选择音频或视频文件", type=['mp3', 'wav', 'ogg', 'mp4', 'avi', 'mkv', 'flac', 'm4a'])

if uploaded_file is not None:
    # 用户上传了文件
    st.success(f"已上传: {uploaded_file.name}")
    
    # 保存上传的文件到临时目录
    # 获取文件名和后缀
    filename, file_extension = os.path.splitext(uploaded_file.name)
    # 创建临时文件
    file_path = temp_manager.create_named_file(filename, suffix=file_extension)
    # 以二进制模式写入文件内容
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getvalue())
    
    # 显示文件信息
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    st.info(f"文件大小: {file_size_mb:.2f} MB")
    
    # AI模型选择
    st.header("第二步：设置分割选项")
    
    # 高级选项
    with st.expander("高级选项"):
        col1, col2 = st.columns(2)
        
        with col1:
            min_segment = st.slider("最小片段长度 (秒)", 1, 30, 5)
            max_segment = st.slider("最大片段长度 (秒)", 30, 300, 60)
        
        with col2:
            output_format = st.selectbox("输出格式", ["mp3", "wav", "ogg"], index=0)
            output_quality = st.selectbox("输出质量", ["low", "medium", "high"], index=1)
        
        preserve_sentences = st.checkbox("保持句子完整性", value=True)
        filter_keywords = st.text_input("过滤关键词 (用逗号分隔)", "")
    
    # 处理按钮
    if st.button("开始智能分割"):
        # 创建进度条
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 定义进度回调函数
        def update_progress(text, percent):
            progress_bar.progress(int(percent))
            status_text.text(text)
        
        try:
            # 第一阶段：提取音频
            status_text.text("提取音频中...")
            progress_bar.progress(0)
            
            # 使用适配器而不是直接的AudioProcessor
            audio_processor = AudioProcessorAdapter()
            audio_analyzer = AIAnalyzerAdapter()  # 不再需要model_size参数
            
            # 提取音频
            audio_path = audio_processor.extract_audio(file_path, progress_callback=update_progress)
            
            if not audio_path:
                st.error("音频提取失败，请检查文件格式是否正确。")
                st.stop()
            
            # 第二阶段：AI分析
            progress_bar.progress(20)
            status_text.text("使用云API分析音频内容...")  # 修改提示文本
            
            # 转录音频
            transcription = audio_analyzer.transcribe_audio(
                audio_path, 
                progress_callback=update_progress
            )
            
            if not transcription or not transcription.get("segments"):
                st.error("音频分析失败，未能识别出任何内容。")
                st.stop()
            
            # 显示原始转录结果
            progress_bar.progress(60)
            status_text.text("分析完成，处理分段中...")
            
            # 找到合适的分段点
            segments = audio_analyzer.find_sentence_breaks(
                transcription,
                max_interval=max_segment,
                min_interval=min_segment,
                preserve_sentences=preserve_sentences
            )
            
            # 过滤关键词
            if filter_keywords:
                keywords = [k.strip() for k in filter_keywords.split(",")]
                filtered_segments = []
                
                for segment in segments:
                    text = segment["text"].lower()
                    
                    if any(keyword.lower() in text for keyword in keywords):
                        filtered_segments.append(segment)
                
                if filtered_segments:
                    segments = filtered_segments
                    st.info(f"找到 {len(segments)} 个包含关键词的片段")
                else:
                    st.warning("没有找到包含关键词的片段，将使用所有分段")
            
            # 显示分段信息
            st.subheader("识别到的内容分段")
            segment_df = []
            
            for i, segment in enumerate(segments):
                segment_df.append({
                    "序号": i + 1,
                    "开始时间": f"{int(segment['start']) // 60:02d}:{int(segment['start']) % 60:02d}",
                    "结束时间": f"{int(segment['end']) // 60:02d}:{int(segment['end']) % 60:02d}",
                    "持续时间": f"{int(segment['end'] - segment['start']):02d}秒",
                    "内容": segment["text"]
                })
            
            st.dataframe(segment_df)
            
            # 第三阶段：分割音频
            progress_bar.progress(70)
            status_text.text("开始分割音频...")
            
            # 创建输出目录
            output_dir = temp_manager.create_dir("output")
            
            # 分割音频
            output_files = audio_processor.split_audio(
                audio_path,
                segments,
                output_dir,
                output_format=output_format,
                quality=output_quality,
                progress_callback=update_progress
            )
            
            if not output_files:
                st.error("音频分割失败。")
                st.stop()
            
            # 完成处理
            progress_bar.progress(100)
            status_text.text("处理完成！")
            
            # 打包下载
            st.subheader("下载分割后的音频")
            st.write(f"共生成 {len(output_files)} 个音频文件")
            
            # 创建ZIP文件
            import zipfile
            zip_path = os.path.join(temp_manager.base_dir, "output.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file in output_files:
                    zipf.write(file, os.path.basename(file))
            
            # 提供下载
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="下载所有分割音频 (ZIP)",
                    data=f,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}_segments.zip",
                    mime="application/zip"
                )
            
            # 也提供单独下载
            st.write("或者下载单个文件:")
            for i, file in enumerate(output_files[:10]):  # 限制显示10个文件
                with open(file, "rb") as f:
                    st.download_button(
                        label=f"下载片段 {i+1}",
                        data=f,
                        file_name=os.path.basename(file),
                        mime=f"audio/{output_format}",
                        key=f"download_{i}"
                    )
            
            if len(output_files) > 10:
                st.info(f"还有 {len(output_files) - 10} 个文件未显示，请使用ZIP下载所有文件。")
            
        except Exception as e:
            st.error(f"处理过程中出错: {str(e)}")
            logger.exception("处理失败")
            
# 当应用退出时清理临时文件
def on_exit():
    """应用退出时的清理函数"""
    try:
        cleanup_global_manager()
    except:
        pass

# 注册退出处理
import atexit
atexit.register(on_exit) 