'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export default function HomePage() {
  const { isAuthenticated, isAuthInitialized } = useAppStore((state) => ({
    isAuthenticated: state.auth.isAuthenticated,
    isAuthInitialized: state.isAuthInitialized
  }));

  // 如果认证状态还在初始化，显示加载状态
  if (!isAuthInitialized) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner size="md" />
      </div>
    );
  }

  // 根据认证状态显示不同内容
  return isAuthenticated ? (
    <ProtectedRoute>
      <MainAppContent />
    </ProtectedRoute>
  ) : (
    <WelcomePage />
  );
}

// 欢迎页面 - 未认证用户
function WelcomePage() {
  const router = useRouter();

  const handleGetStarted = () => {
    router.push('/auth');
  };

  return (
    <div className="py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h1 className="text-4xl font-extrabold text-gray-900 sm:text-5xl">
          音频分割和转写工具
        </h1>
        <p className="mt-4 text-xl text-gray-500">
          简单高效的音频处理解决方案
        </p>
        <div className="mt-10">
          <button
            onClick={handleGetStarted}
            className="px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 md:text-lg"
          >
            开始使用
          </button>
        </div>
        
        <div className="mt-16 grid grid-cols-1 gap-8 md:grid-cols-3">
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900">语音识别转写</h2>
            <p className="mt-2 text-gray-500">
              使用先进的AI语音识别技术将语音内容转换为文本
            </p>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900">智能分割</h2>
            <p className="mt-2 text-gray-500">
              根据内容和语义自动将长音频分割成合适的段落
            </p>
          </div>
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900">批量处理</h2>
            <p className="mt-2 text-gray-500">
              同时处理多个音频文件，提高工作效率
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// 主应用内容 - 已认证用户
function MainAppContent() {
  const router = useRouter();
  const { currentTask, setCurrentTask } = useAppStore((state) => ({
    currentTask: state.currentTask,
    setCurrentTask: state.setCurrentTask
  }));
  const { systemStatus, setSystemStatus } = useAppStore((state) => ({
    systemStatus: state.systemStatus,
    setSystemStatus: state.setSystemStatus
  }));

  useEffect(() => {
    const checkSystemStatus = async () => {
      try {
        const status = await apiService.getStatus();
        setSystemStatus(status);
      } catch (error) {
        console.error('获取系统状态失败', error);
      }
    };

    checkSystemStatus();
  }, [setSystemStatus]);

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">音频处理控制台</h1>
      
      {systemStatus && (
        <div className="mb-6 p-4 bg-white rounded-lg shadow">
          <h2 className="text-lg font-medium mb-2">系统状态</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${systemStatus.components.ffmpeg ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span>FFmpeg: {systemStatus.components.ffmpeg ? '可用' : '不可用'}</span>
            </div>
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${systemStatus.components.whisper ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span>Whisper: {systemStatus.components.whisper ? '可用' : '不可用'}</span>
            </div>
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${systemStatus.components.gpu ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span>GPU支持: {systemStatus.components.gpu ? '可用' : '不可用'}</span>
            </div>
          </div>
          {systemStatus.components.gpu && (
            <div className="mt-2 text-sm text-gray-600">
              {systemStatus.gpu_info}
            </div>
          )}
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-medium mb-4">开始新任务</h2>
          <p className="mb-4 text-gray-600">上传音频文件以开始处理</p>
          <button
            onClick={() => router.push('/upload')}
            className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none"
          >
            上传音频
          </button>
        </div>
        
        {currentTask && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-medium mb-4">继续上次任务</h2>
            <p className="mb-2 text-gray-600">
              文件: {currentTask.filename}
            </p>
            <p className="mb-4 text-gray-600">
              状态: {currentTask.status}
            </p>
            <button
              onClick={() => router.push(`/tasks/${currentTask.id}`)}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none"
            >
              继续处理
            </button>
          </div>
        )}
      </div>
    </div>
  );
} 