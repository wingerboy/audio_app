'use client';

import { useEffect, useState } from 'react';
import { useAppStore } from '@/lib/store';
import apiService, { SystemStatus } from '@/lib/api';
import { FileUploader } from '@/components/FileUploader';
import { ModelSelector } from '@/components/ModelSelector';
import { SegmentsList } from '@/components/SegmentsList';
import { AudioSplitter } from '@/components/AudioSplitter';
import { DownloadFiles } from '@/components/DownloadFiles';
import { StatusBar } from '@/components/StatusBar';

export default function Home() {
  // 使用应用状态
  const { 
    systemStatus, 
    setSystemStatus,
    currentTask,
    uiState,
    setCurrentStep
  } = useAppStore();
  
  // 本地状态
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // 获取系统状态
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        setLoading(true);
        const status = await apiService.getStatus();
        setSystemStatus(status);
        setError(null);
      } catch (err) {
        console.error('获取系统状态失败:', err);
        setError('无法连接到后端服务，请确保API服务正在运行。');
      } finally {
        setLoading(false);
      }
    };
    
    fetchSystemStatus();
  }, [setSystemStatus]);
  
  // 渲染系统状态
  const renderSystemStatus = () => {
    if (loading) {
      return <div className="text-center py-4">正在检查系统状态...</div>;
    }
    
    if (error) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-md p-4 text-red-700">
          <p className="font-medium">错误</p>
          <p>{error}</p>
        </div>
      );
    }
    
    if (!systemStatus) {
      return null;
    }
    
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="card">
          <div className="card-body">
            <h3 className="font-medium text-gray-700 mb-2">FFmpeg</h3>
            {systemStatus.components.ffmpeg ? (
              <div className="text-green-600">✓ 可用</div>
            ) : (
              <div className="text-red-600">✗ 不可用</div>
            )}
          </div>
        </div>
        
        <div className="card">
          <div className="card-body">
            <h3 className="font-medium text-gray-700 mb-2">Whisper</h3>
            {systemStatus.components.whisper ? (
              <div className="text-green-600">✓ 可用</div>
            ) : (
              <div className="text-red-600">✗ 不可用</div>
            )}
          </div>
        </div>
        
        <div className="card">
          <div className="card-body">
            <h3 className="font-medium text-gray-700 mb-2">GPU</h3>
            {systemStatus.components.gpu ? (
              <div className="text-green-600">✓ 可用 ({systemStatus.gpu_info})</div>
            ) : (
              <div className="text-yellow-600">⚠ 不可用 (将使用CPU)</div>
            )}
          </div>
        </div>
      </div>
    );
  };
  
  // 渲染主要内容
  const renderContent = () => {
    // 如果系统组件不可用，显示错误
    if (
      systemStatus && 
      (!systemStatus.components.ffmpeg || !systemStatus.components.whisper)
    ) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-md p-6 text-center">
          <h2 className="text-xl font-medium text-red-700 mb-4">系统配置不完整</h2>
          <p className="mb-4">
            应用程序需要FFmpeg和Whisper组件才能正常工作。请检查服务器配置。
          </p>
        </div>
      );
    }
    
    // 步骤导航
    const steps = [
      { id: 1, name: '上传文件' },
      { id: 2, name: '分析内容' },
      { id: 3, name: '分割音频' },
      { id: 4, name: '下载文件' },
    ];
    
    return (
      <div className="space-y-8">
        {/* 步骤导航 */}
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
        
        {/* 状态栏 */}
        {currentTask && <StatusBar task={currentTask} />}
        
        {/* 步骤内容 */}
        {uiState.currentStep === 1 && <FileUploader />}
        {uiState.currentStep === 2 && <ModelSelector />}
        {uiState.currentStep === 3 && <SegmentsList />}
        {uiState.currentStep === 4 && <DownloadFiles />}
        
        {/* 分割功能 */}
        {uiState.currentStep === 3 && <AudioSplitter />}
      </div>
    );
  };
  
  return (
    <div>
      {/* 系统状态 */}
      {renderSystemStatus()}
      
      {/* 主要内容 */}
      {!loading && renderContent()}
    </div>
  );
} 