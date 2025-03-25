'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FileUploader } from '@/components/FileUploader';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useAppStore } from '@/lib/store';

export default function UploadPage() {
  const router = useRouter();
  const { currentTask, setCurrentStep } = useAppStore((state) => ({
    currentTask: state.currentTask,
    setCurrentStep: state.setCurrentStep
  }));

  // 确保当前步骤设置为1（上传步骤）
  useEffect(() => {
    setCurrentStep(1);
  }, [setCurrentStep]);

  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">上传音频文件</h1>
          <button
            onClick={() => router.push('/')}
            className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
          >
            返回首页
          </button>
        </div>

        <p className="text-gray-700 dark:text-gray-300">
          上传音频或视频文件以开始处理。支持的格式包括MP3、WAV、OGG、FLAC、M4A、MP4、AVI、MKV、MOV等。
        </p>

        <FileUploader />
        
        {currentTask && (
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <p className="text-blue-800 dark:text-blue-300 font-medium">
              当前任务: {currentTask.filename} ({currentTask.status})
            </p>
            {currentTask.status === 'uploaded' && (
              <button
                onClick={() => router.push(`/tasks/${currentTask.id}`)}
                className="mt-2 text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
              >
                继续处理此文件
              </button>
            )}
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
} 