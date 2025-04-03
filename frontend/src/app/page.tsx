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
        <h1 className="text-4xl font-extrabold text-gray-900 dark:text-white sm:text-5xl">
          音频分割和转写工具
        </h1>
        <p className="mt-4 text-xl text-gray-700 dark:text-gray-300">
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
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">语音识别转写</h2>
            <p className="mt-2 text-gray-700 dark:text-gray-300">
              使用先进的AI语音识别技术将语音内容转换为文本
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">智能分割</h2>
            <p className="mt-2 text-gray-700 dark:text-gray-300">
              根据内容和语义自动将长音频分割成合适的段落
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 border border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">批量处理</h2>
            <p className="mt-2 text-gray-700 dark:text-gray-300">
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
      <h1 className="text-2xl font-semibold mb-4 text-gray-900 dark:text-white">音频处理控制台</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-medium mb-4 text-gray-900 dark:text-white">开始新任务</h2>
          <p className="mb-4 text-gray-700 dark:text-gray-300">上传音频文件以开始处理</p>
          <button
            onClick={() => router.push('/upload')}
            className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none font-medium"
          >
            上传音频
          </button>
        </div>
        
        {currentTask && (
          <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-medium mb-4 text-gray-900 dark:text-white">继续上次任务</h2>
            <p className="mb-2 text-gray-700 dark:text-gray-300">
              文件: <span className="font-medium">{currentTask.filename}</span>
            </p>
            <p className="mb-4 text-gray-700 dark:text-gray-300">
              状态: <span className={`px-2 py-1 rounded text-xs font-medium ${
                currentTask.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100' :
                currentTask.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100' :
                'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100'
              }`}>{currentTask.status}</span>
            </p>
            <button
              onClick={() => router.push(`/tasks/${currentTask.id}`)}
              className="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none font-medium"
            >
              继续处理
            </button>
          </div>
        )}
      </div>
    </div>
  );
} 