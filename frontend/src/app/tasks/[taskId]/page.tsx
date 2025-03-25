'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { apiService } from '@/lib/api';
import { ModelSelector } from '@/components/ModelSelector';
import { SegmentsList } from '@/components/SegmentsList';
import { AudioSplitter } from '@/components/AudioSplitter';
import { DownloadFiles } from '@/components/DownloadFiles';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { LoadingSpinner } from '@/components/LoadingSpinner';

// 步骤定义
const STEPS = {
  ANALYZE: 2,
  SEGMENTS: 3,
  DOWNLOAD: 4,
};

export default function TaskDetailPage({ params }: { params: { taskId: string } }) {
  const router = useRouter();
  const taskId = params.taskId;
  
  // 全局状态
  const { currentTask, setCurrentTask, setCurrentStep, uiState } = useAppStore((state) => ({
    currentTask: state.currentTask,
    setCurrentTask: state.setCurrentTask,
    setCurrentStep: state.setCurrentStep,
    uiState: state.uiState
  }));
  
  // 本地状态
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 获取任务详情
  useEffect(() => {
    const fetchTaskDetails = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const taskDetails = await apiService.getTaskStatus(taskId);
        setCurrentTask(taskDetails);
        
        // 根据任务状态设置当前步骤
        if (taskDetails.status === 'uploaded') {
          setCurrentStep(STEPS.ANALYZE);
        } else if (taskDetails.status === 'analyzed') {
          setCurrentStep(STEPS.SEGMENTS);
        } else if (taskDetails.status === 'completed') {
          setCurrentStep(STEPS.DOWNLOAD);
        }
        
      } catch (error) {
        console.error('获取任务详情失败:', error);
        setError('无法加载任务详情，请返回首页重试。');
      } finally {
        setLoading(false);
      }
    };
    
    fetchTaskDetails();
    
    // 定期刷新任务状态
    const intervalId = setInterval(async () => {
      try {
        const updatedTask = await apiService.getTaskStatus(taskId);
        setCurrentTask(updatedTask);
      } catch (error) {
        console.error('刷新任务状态失败:', error);
      }
    }, 5000); // 每5秒刷新一次
    
    return () => {
      clearInterval(intervalId);
    };
  }, [taskId, setCurrentTask, setCurrentStep]);
  
  // 渲染步骤
  const renderStepContent = () => {
    if (!currentTask) {
      return null;
    }
    
    switch (uiState.currentStep) {
      case STEPS.ANALYZE:
        return <ModelSelector />;
      case STEPS.SEGMENTS:
        return (
          <>
            <SegmentsList />
            <AudioSplitter />
          </>
        );
      case STEPS.DOWNLOAD:
        return <DownloadFiles />;
      default:
        return null;
    }
  };
  
  // 步骤导航
  const renderStepNavigation = () => {
    const steps = [
      { id: 1, name: '上传文件' },
      { id: 2, name: '分析内容' },
      { id: 3, name: '分割音频' },
      { id: 4, name: '下载文件' },
    ];
    
    return (
      <div className="mb-8">
        <nav className="flex justify-between">
          {steps.map((step) => (
            <button
              key={step.id}
              onClick={() => {
                // 只允许向后导航，或者在任务完成后导航到下载页面
                if (
                  step.id <= uiState.currentStep || 
                  (step.id === 4 && currentTask?.status === 'completed')
                ) {
                  setCurrentStep(step.id);
                }
              }}
              className={`flex flex-col items-center ${
                step.id === uiState.currentStep
                  ? 'text-primary-600 font-medium'
                  : step.id < uiState.currentStep || (step.id === 4 && currentTask?.status === 'completed')
                  ? 'text-gray-600 cursor-pointer hover:text-primary-500'
                  : 'text-gray-400 cursor-not-allowed'
              }`}
              disabled={step.id > uiState.currentStep && !(step.id === 4 && currentTask?.status === 'completed')}
            >
              <span
                className={`w-10 h-10 flex items-center justify-center rounded-full mb-2 ${
                  step.id === uiState.currentStep
                    ? 'bg-primary-600 text-white'
                    : step.id < uiState.currentStep || (step.id === 4 && currentTask?.status === 'completed')
                    ? 'bg-gray-200 text-gray-700'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {step.id}
              </span>
              <span>{step.name}</span>
            </button>
          ))}
        </nav>
      </div>
    );
  };
  
  return (
    <ProtectedRoute>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">音频处理任务</h1>
          <button
            onClick={() => router.push('/')}
            className="text-primary-600 hover:text-primary-700"
          >
            返回首页
          </button>
        </div>
        
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <LoadingSpinner size="lg" />
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-700">
            <p className="font-medium">错误</p>
            <p>{error}</p>
            <button
              onClick={() => router.push('/')}
              className="mt-4 text-primary-600 hover:text-primary-700 font-medium"
            >
              返回首页
            </button>
          </div>
        ) : (
          <>
            {currentTask && (
              <div className="bg-white p-4 rounded-lg shadow mb-6">
                <h2 className="text-lg font-medium mb-2">任务信息</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">文件名</p>
                    <p className="font-medium">{currentTask.filename}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">大小</p>
                    <p className="font-medium">{currentTask.size_mb.toFixed(2)} MB</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">状态</p>
                    <p className="font-medium">{currentTask.status}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">创建时间</p>
                    <p className="font-medium">
                      {new Date(currentTask.created_at * 1000).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* 步骤导航 */}
            {renderStepNavigation()}
            
            {/* 步骤内容 */}
            {renderStepContent()}
          </>
        )}
      </div>
    </ProtectedRoute>
  );
} 