#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import tempfile
import zipfile
import platform
import subprocess
import logging
from urllib.request import urlretrieve
from logging_config import LoggingConfig

# 获取模块的logger
logger = LoggingConfig.get_logger(__name__)

class EnvironmentManager:
    """
    环境管理器类，负责检查和配置运行环境所需的依赖
    包含GPU检测、PyTorch安装和FFmpeg安装等功能
    """
    
    @staticmethod
    def check_gpu():
        """
        检查GPU状态并输出详细信息 - 已废弃，不再需要GPU
        
        Returns:
            bool: GPU是否可用
        """
        logger.info("不再检查GPU状态，使用云API不需要GPU")
        return False
    
    @staticmethod
    def check_gpu_status():
        """检查GPU是否可用 - 已废弃，使用云API不需要GPU"""
        logger.info("不再检查GPU状态，使用云API不需要GPU")
        return False, "不可用（使用云API）"
    
    @staticmethod
    def check_pytorch():
        """
        检查PyTorch安装状态 - 已废弃，使用云API不需要PyTorch
        
        Returns:
            bool: PyTorch是否可用且CUDA支持正常
        """
        logger.info("不再检查PyTorch，使用云API不需要PyTorch")
        return False
    
    @staticmethod
    def get_torch_version():
        """返回PyTorch版本 - 已废弃，使用云API不需要PyTorch"""
        return "不可用（使用云API）"
    
    @staticmethod
    def get_gpu_info():
        """返回GPU信息 - 已废弃，使用云API不需要GPU"""
        return "不可用（使用云API）"
    
    @staticmethod
    def ensure_whisper():
        """确保Whisper模型可用 - 已废弃，使用云API不需要Whisper"""
        logger.info("使用云API，不再需要Whisper模型")
        return False
    
    @staticmethod
    def ensure_ffmpeg():
        """
        确保FFmpeg可用
        
        Returns:
            bool: FFmpeg是否可用
        """
        # 检查是否已安装
        if EnvironmentManager.check_ffmpeg():
            return True
            
        # 尝试安装FFmpeg
        logger.info("尝试安装FFmpeg...")
        if platform.system() == 'Windows':
            success = EnvironmentManager._install_ffmpeg_windows()
        elif platform.system() == 'Darwin':  # macOS
            success = EnvironmentManager._install_ffmpeg_macos()
        elif platform.system() == 'Linux':
            success = EnvironmentManager._install_ffmpeg_linux()
        else:
            logger.error(f"不支持的操作系统: {platform.system()}")
            return False
            
        # 安装后再次检查
        return EnvironmentManager.check_ffmpeg() if success else False
    
    @staticmethod
    def check_ffmpeg():
        """
        检查FFmpeg是否已安装
        
        Returns:
            bool: FFmpeg是否可用
        """
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                logger.info(f"✅ FFmpeg已安装: {version_line}")
                return True
            else:
                logger.warning("❌ FFmpeg似乎已安装但返回错误")
                return False
        except FileNotFoundError:
            logger.warning("❌ FFmpeg未安装或不在PATH中")
            return False
        except Exception as e:
            logger.error(f"❌ 检查FFmpeg时出错: {str(e)}")
            return False
    
    @staticmethod
    def check_cuda():
        """
        检查CUDA是否可用和版本信息
        
        Returns:
            str or None: CUDA版本或None（如果无法检测）
        """
        logger.info("===== 检查CUDA环境 =====")
        
        # 检查NVIDIA驱动
        try:
            nvidia_output = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if nvidia_output.returncode == 0:
                logger.info("✅ NVIDIA驱动已安装")
                # 提取CUDA版本
                import re
                cuda_version_match = re.search(r'CUDA Version: (\d+\.\d+)', nvidia_output.stdout)
                if cuda_version_match:
                    cuda_version = cuda_version_match.group(1)
                    logger.info(f"✅ 检测到CUDA版本: {cuda_version}")
                    return cuda_version
                else:
                    logger.warning("⚠️ 无法从nvidia-smi输出中确定CUDA版本")
            else:
                logger.error("❌ nvidia-smi命令失败，NVIDIA驱动可能未正确安装")
                logger.debug(f"错误输出: {nvidia_output.stderr}")
        except FileNotFoundError:
            logger.warning("❌ nvidia-smi未找到，NVIDIA驱动可能未安装")
        except Exception as e:
            logger.error(f"❌ 检查NVIDIA驱动时出错: {str(e)}")
        
        # 尝试从环境变量中获取CUDA版本
        cuda_path = os.environ.get('CUDA_PATH', '')
        if cuda_path:
            logger.info(f"CUDA_PATH环境变量: {cuda_path}")
            # 尝试从路径中提取版本
            import re
            version_match = re.search(r'v(\d+\.\d+)', cuda_path)
            if version_match:
                cuda_version = version_match.group(1)
                logger.info(f"从环境变量推断CUDA版本: {cuda_version}")
                return cuda_version
        
        # 如果都失败了，检查nvcc
        try:
            nvcc_output = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
            if nvcc_output.returncode == 0:
                logger.info("✅ NVCC已安装")
                # 提取CUDA版本
                import re
                cuda_version_match = re.search(r'release (\d+\.\d+)', nvcc_output.stdout)
                if cuda_version_match:
                    cuda_version = cuda_version_match.group(1)
                    logger.info(f"✅ 从NVCC检测到CUDA版本: {cuda_version}")
                    return cuda_version
        except:
            pass
        
        logger.warning("⚠️ 无法确定CUDA版本，将使用兼容性最好的版本")
        return None
    
    @staticmethod
    def install_pytorch():
        """
        安装适合当前环境的PyTorch版本
        
        Returns:
            bool: 安装是否成功
        """
        logger.info("===== PyTorch CUDA安装助手 =====")
        logger.info(f"Python版本: {platform.python_version()}")
        logger.info(f"操作系统: {platform.system()} {platform.release()}")
        
        # 检查CUDA版本
        cuda_version = EnvironmentManager.check_cuda()
        
        # 卸载现有PyTorch
        EnvironmentManager._uninstall_pytorch()
        
        # 安装PyTorch
        install_success = EnvironmentManager._install_pytorch_with_cuda(cuda_version)
        
        if install_success:
            # 验证安装
            has_cuda = EnvironmentManager._verify_pytorch_cuda()
            if has_cuda:
                logger.info("✅ PyTorch已成功安装并支持CUDA")
                return True
            else:
                logger.warning("⚠️ PyTorch已安装但CUDA支持可能有问题")
                return False
        else:
            logger.error("❌ PyTorch安装失败")
            return False
    
    @staticmethod
    def _uninstall_pytorch():
        """
        卸载当前安装的PyTorch
        
        Returns:
            bool: 卸载是否成功
        """
        logger.info("===== 卸载现有PyTorch =====")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torch', 'torchvision', 'torchaudio'])
            logger.info("✅ 现有PyTorch包已卸载")
            return True
        except Exception as e:
            logger.error(f"❌ 卸载PyTorch时出错: {str(e)}")
            return False
    
    @staticmethod
    def _install_pytorch_with_cuda(cuda_version=None):
        """
        安装支持CUDA的PyTorch版本
        
        Args:
            cuda_version (str, optional): CUDA版本. Defaults to None.
        
        Returns:
            bool: 安装是否成功
        """
        logger.info("===== 安装CUDA版PyTorch =====")
        
        # 根据CUDA版本选择兼容的PyTorch版本
        if cuda_version:
            cuda_major = cuda_version.split('.')[0]
            cuda_minor = cuda_version.split('.')[1] if '.' in cuda_version else '0'
            
            cuda_short = f"{cuda_major}{cuda_minor}"
            if int(cuda_major) >= 12:
                # CUDA 12.x
                cuda_for_torch = "cu121"  # PyTorch当前支持CUDA 12.1
                logger.info(f"CUDA {cuda_version} 检测到，使用PyTorch CUDA 12.1兼容包")
            elif int(cuda_major) == 11:
                # CUDA 11.x
                if int(cuda_minor) >= 8:
                    cuda_for_torch = "cu118"
                    logger.info(f"CUDA {cuda_version} 检测到，使用PyTorch CUDA 11.8兼容包")
                elif int(cuda_minor) >= 6:
                    cuda_for_torch = "cu117"
                    logger.info(f"CUDA {cuda_version} 检测到，使用PyTorch CUDA 11.7兼容包")
                else:
                    cuda_for_torch = "cu116"
                    logger.info(f"CUDA {cuda_version} 检测到，使用PyTorch CUDA 11.6兼容包")
            elif int(cuda_major) == 10:
                # CUDA 10.x
                cuda_for_torch = "cu102"
                logger.info(f"CUDA {cuda_version} 检测到，使用PyTorch CUDA 10.2兼容包")
            else:
                # 使用CPU版本
                cuda_for_torch = None
                logger.warning(f"不支持的CUDA版本: {cuda_version}，将使用CPU版本")
        else:
            # 如果无法检测到CUDA版本，尝试使用CUDA 11.8版本，这是目前较新且兼容性较好的版本
            cuda_for_torch = "cu118"
            logger.info("无法确定CUDA版本，使用PyTorch CUDA 11.8兼容包（兼容性好）")
        
        try:
            if cuda_for_torch:
                # 安装CUDA版PyTorch
                url = f"https://download.pytorch.org/whl/{cuda_for_torch}"
                cmd = [
                    sys.executable, "-m", "pip", "install",
                    "torch", "torchvision", "torchaudio",
                    "--index-url", url
                ]
                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ CUDA版PyTorch安装成功")
                    return True
                else:
                    logger.error(f"❌ 安装失败: {result.stderr}")
                    return False
            else:
                # 安装CPU版PyTorch
                cmd = [
                    sys.executable, "-m", "pip", "install",
                    "torch", "torchvision", "torchaudio"
                ]
                logger.info(f"执行命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info("✅ CPU版PyTorch安装成功")
                    return True
                else:
                    logger.error(f"❌ 安装失败: {result.stderr}")
                    return False
        
        except Exception as e:
            logger.error(f"❌ 安装PyTorch时出错: {str(e)}")
            return False
    
    @staticmethod
    def _verify_pytorch_cuda():
        """
        验证PyTorch是否可以使用CUDA
        
        Returns:
            bool: 验证是否成功
        """
        logger.info("===== 验证PyTorch CUDA支持 =====")
        
        try:
            # 创建临时文件
            temp_dir = os.path.dirname(os.path.abspath(__file__))
            temp_file = os.path.join(temp_dir, "verify_cuda.py")
            
            # 写入测试代码
            with open(temp_file, "w") as f:
                f.write("""
import torch
print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA是否可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA版本: {torch.version.cuda}")
    print(f"GPU数量: {torch.cuda.device_count()}")
    print(f"当前GPU: {torch.cuda.current_device()}")
    print(f"GPU型号: {torch.cuda.get_device_name(0)}")
""")
            
            # 运行测试代码
            result = subprocess.run([sys.executable, temp_file], capture_output=True, text=True)
            logger.info(result.stdout)
            
            # 清理临时文件
            try:
                os.remove(temp_file)
            except:
                pass
            
            # 检查是否成功
            return "CUDA是否可用: True" in result.stdout
        
        except Exception as e:
            logger.error(f"❌ 验证PyTorch CUDA支持时出错: {str(e)}")
            return False
    
    @staticmethod
    def install_ffmpeg():
        """
        根据操作系统选择合适的FFmpeg安装方法
        
        Returns:
            bool: 安装是否成功
        """
        # 检测操作系统
        if sys.platform.startswith('win'):
            return EnvironmentManager._install_ffmpeg_windows()
        elif sys.platform.startswith('darwin'):
            return EnvironmentManager._install_ffmpeg_macos()
        elif sys.platform.startswith('linux'):
            return EnvironmentManager._install_ffmpeg_linux()
        else:
            logger.error(f"不支持的操作系统: {sys.platform}")
            return False
    
    @staticmethod
    def _install_ffmpeg_windows():
        """
        下载并安装FFmpeg到Windows系统
        
        Returns:
            bool: 安装是否成功
        """
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "ffmpeg.zip")
        
        try:
            logger.info("正在下载FFmpeg...")
            # 下载FFmpeg
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            urlretrieve(url, zip_path)
            
            logger.info("正在解压FFmpeg...")
            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 查找解压后的目录
            extracted_dir = None
            for item in os.listdir(temp_dir):
                if item.startswith("ffmpeg-master") and os.path.isdir(os.path.join(temp_dir, item)):
                    extracted_dir = os.path.join(temp_dir, item)
                    break
            
            if not extracted_dir:
                logger.error("未找到解压后的FFmpeg目录")
                return False
            
            # 获取用户主目录
            user_home = os.path.expanduser("~")
            ffmpeg_dir = os.path.join(user_home, "ffmpeg")
            
            # 如果已存在，先移除
            if os.path.exists(ffmpeg_dir):
                shutil.rmtree(ffmpeg_dir)
            
            # 创建ffmpeg目录
            os.makedirs(ffmpeg_dir, exist_ok=True)
            
            # 复制bin目录
            shutil.copytree(os.path.join(extracted_dir, "bin"), os.path.join(ffmpeg_dir, "bin"))
            
            # 将FFmpeg添加到环境变量
            # 注意：这只会在当前程序运行期间生效
            bin_path = os.path.join(ffmpeg_dir, "bin")
            os.environ["PATH"] = bin_path + os.pathsep + os.environ["PATH"]
            
            # 尝试持久化添加到环境变量（仅Windows）
            try:
                if os.name == 'nt':
                    logger.info("正在将FFmpeg添加到系统路径...")
                    # 在Windows上使用setx添加到系统路径
                    process = subprocess.run(
                        ["setx", "PATH", f"%PATH%;{bin_path}"],
                        capture_output=True,
                        text=True
                    )
                    if process.returncode == 0:
                        logger.info("FFmpeg已添加到系统路径")
                    else:
                        logger.warning(f"警告：无法添加FFmpeg到系统路径: {process.stderr}")
            except Exception as e:
                logger.error(f"添加到环境变量时出错: {str(e)}")
            
            logger.info(f"FFmpeg已安装到: {ffmpeg_dir}")
            logger.info("您可能需要重启应用程序以使用新安装的FFmpeg")
            return True
        
        except Exception as e:
            logger.error(f"安装FFmpeg时出错: {str(e)}")
            return False
        
        finally:
            # 清理临时目录
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    @staticmethod
    def _install_ffmpeg_macos():
        """
        下载并安装FFmpeg到macOS系统
        
        Returns:
            bool: 安装是否成功
        """
        try:
            # 在macOS上，使用Homebrew安装FFmpeg（如果有）
            logger.info("尝试使用Homebrew安装FFmpeg...")
            
            # 检查是否已安装Homebrew
            brew_check = subprocess.run(["which", "brew"], capture_output=True, text=True)
            
            if brew_check.returncode == 0:
                # 使用Homebrew安装
                process = subprocess.run(["brew", "install", "ffmpeg"], check=False)
                if process.returncode == 0:
                    logger.info("已使用Homebrew成功安装FFmpeg")
                    return True
                else:
                    logger.warning("使用Homebrew安装FFmpeg失败")
            else:
                logger.info("未检测到Homebrew，尝试手动安装...")
            
            # 手动安装（如果Homebrew不可用）
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            
            # 下载FFmpeg
            logger.info("正在下载FFmpeg...")
            url = "https://evermeet.cx/ffmpeg/getrelease/zip"
            zip_path = os.path.join(temp_dir, "ffmpeg.zip")
            urlretrieve(url, zip_path)
            
            # 解压
            logger.info("正在解压FFmpeg...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 获取用户主目录下的bin目录
            user_home = os.path.expanduser("~")
            bin_dir = os.path.join(user_home, "bin")
            os.makedirs(bin_dir, exist_ok=True)
            
            # 复制FFmpeg可执行文件
            ffmpeg_exec = os.path.join(temp_dir, "ffmpeg")
            if os.path.exists(ffmpeg_exec):
                shutil.copy(ffmpeg_exec, bin_dir)
                os.chmod(os.path.join(bin_dir, "ffmpeg"), 0o755)
                
                # 添加到PATH（仅当前会话）
                os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
                
                # 建议用户更新.bashrc或.zshrc
                shell_file = ".zshrc" if os.path.exists(os.path.join(user_home, ".zshrc")) else ".bashrc"
                logger.info(f"FFmpeg已安装到: {bin_dir}")
                logger.info(f"请考虑在{shell_file}中添加以下行以永久添加到PATH:")
                logger.info(f"export PATH=\"{bin_dir}:$PATH\"")
                
                return True
            else:
                logger.error("未找到FFmpeg可执行文件")
                return False
                
        except Exception as e:
            logger.error(f"安装FFmpeg时出错: {str(e)}")
            return False
    
    @staticmethod
    def _install_ffmpeg_linux():
        """
        在Linux系统上安装FFmpeg
        
        Returns:
            bool: 安装是否成功
        """
        try:
            # 检测Linux发行版
            logger.info("检测Linux发行版...")
            
            # 检查apt（Debian/Ubuntu）
            apt_check = subprocess.run(["which", "apt"], capture_output=True, text=True)
            if apt_check.returncode == 0:
                logger.info("检测到apt包管理器，使用apt安装FFmpeg...")
                subprocess.run(["sudo", "apt", "update"], check=False)
                process = subprocess.run(["sudo", "apt", "install", "-y", "ffmpeg"], check=False)
                if process.returncode == 0:
                    logger.info("已使用apt成功安装FFmpeg")
                    return True
            
            # 检查dnf（Fedora）
            dnf_check = subprocess.run(["which", "dnf"], capture_output=True, text=True)
            if dnf_check.returncode == 0:
                logger.info("检测到dnf包管理器，使用dnf安装FFmpeg...")
                process = subprocess.run(["sudo", "dnf", "install", "-y", "ffmpeg"], check=False)
                if process.returncode == 0:
                    logger.info("已使用dnf成功安装FFmpeg")
                    return True
            
            # 检查yum（CentOS/RHEL）
            yum_check = subprocess.run(["which", "yum"], capture_output=True, text=True)
            if yum_check.returncode == 0:
                logger.info("检测到yum包管理器，使用yum安装FFmpeg...")
                process = subprocess.run(["sudo", "yum", "install", "-y", "ffmpeg"], check=False)
                if process.returncode == 0:
                    logger.info("已使用yum成功安装FFmpeg")
                    return True
            
            # 检查pacman（Arch Linux）
            pacman_check = subprocess.run(["which", "pacman"], capture_output=True, text=True)
            if pacman_check.returncode == 0:
                logger.info("检测到pacman包管理器，使用pacman安装FFmpeg...")
                process = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"], check=False)
                if process.returncode == 0:
                    logger.info("已使用pacman成功安装FFmpeg")
                    return True
            
            logger.warning("未能使用包管理器安装FFmpeg，请尝试手动安装")
            return False
        
        except Exception as e:
            logger.error(f"安装FFmpeg时出错: {str(e)}")
            return False
    
    @staticmethod
    def setup_environment():
        """
        设置完整运行环境，检查并安装所有必要组件
        
        Returns:
            tuple: (ffmpeg_ready, pytorch_ready, whisper_ready) 表示各组件是否就绪
        """
        logger.info("===== 环境配置助手 =====")
        
        # 1. 检查FFmpeg
        ffmpeg_ready = EnvironmentManager.check_ffmpeg()
        if not ffmpeg_ready:
            logger.warning("FFmpeg未安装，尝试安装...")
            ffmpeg_ready = EnvironmentManager.install_ffmpeg()
        
        # 2. 检查PyTorch和GPU
        pytorch_ready = EnvironmentManager.check_pytorch()
        if not pytorch_ready:
            gpu_available = EnvironmentManager.check_gpu()
            if gpu_available:
                logger.info("检测到GPU，但PyTorch未正确配置，尝试安装...")
                pytorch_ready = EnvironmentManager.install_pytorch()
            else:
                logger.info("未检测到GPU，将安装CPU版PyTorch...")
                pytorch_ready = EnvironmentManager.install_pytorch()
        
        # 3. 检查Whisper
        whisper_ready = EnvironmentManager.check_whisper()
        if not whisper_ready:
            logger.warning("Whisper未安装，尝试安装...")
            whisper_ready = EnvironmentManager.ensure_whisper()
        
        return (ffmpeg_ready, pytorch_ready, whisper_ready)

if __name__ == "__main__":
    # 当作为独立脚本运行时，执行完整环境设置
    LoggingConfig.setup_logging(log_level=logging.INFO)
    ffmpeg_ready, pytorch_ready, whisper_ready = EnvironmentManager.setup_environment()
    
    if ffmpeg_ready and pytorch_ready and whisper_ready:
        logger.info("✅ 环境配置完成！所有组件已就绪")
        sys.exit(0)
    else:
        status_messages = []
        if not ffmpeg_ready:
            status_messages.append("FFmpeg配置失败")
        if not pytorch_ready:
            status_messages.append("PyTorch配置失败")
        if not whisper_ready:
            status_messages.append("Whisper配置失败")
        
        logger.warning(f"⚠️ 环境配置部分完成: {', '.join(status_messages)}")
        sys.exit(1) 