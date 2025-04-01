'use client';

import { useState } from 'react';
import { FiScissors, FiDownload } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import apiService from '@/lib/api';

export function AudioSplitter() {
  // 使用应用状态
  const { 
    currentTask, 
    segments,
    selectedSegments,
    settings,
    outputFiles,
    setOutputFiles,
    uiState,
    setIsSplitting,
    setCurrentStep
  } = useAppStore();
  
  // 本地状态
  const [error, setError] = useState<string | null>(null);
  
  // 没有任务或分段数据则显示错误
  if (!currentTask || segments.length === 0) {
    return (
      <div className="card">
        <div className="card-body">
          <p className="text-red-600">请先上传文件并分析音频内容</p>
        </div>
      </div>
    );
  }
  
  // 处理音频分割
  const handleSplit = async () => {
    // 如果没有选择分段，使用全部分段
    const segmentsToSplit = selectedSegments.length > 0 ? selectedSegments : segments;
    
    if (segmentsToSplit.length === 0) {
      setError('请至少选择一个分段');
      return;
    }
    
    try {
      setIsSplitting(true);
      setError(null);
      
      // 调用分割API
      const response = await apiService.splitAudio(
        currentTask.id,
        segmentsToSplit,
        settings.outputFormat,
        settings.outputQuality
      );
      
      // 更新输出文件
      setOutputFiles(response.files);
      
      // 如果响应中包含任务状态，则直接使用
      if (response.task_status) {
        useAppStore.getState().setCurrentTask(response.task_status);
      } else {
        // 否则手动获取最新的任务状态
        const updatedTask = await apiService.getTaskStatus(currentTask.id);
        useAppStore.getState().setCurrentTask(updatedTask);
      }
      
      // 转到下一步
      setTimeout(() => {
        setCurrentStep(4);
      }, 1000);
      
    } catch (error) {
      console.error('分割失败:', error);
      setError('音频分割失败，请重试。');
    } finally {
      setIsSplitting(false);
    }
  };
  
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-xl font-medium">分割音频</h2>
      </div>
      
      <div className="card-body space-y-6">
        <div>
          <p className="text-sm text-gray-600 mb-4">
            {selectedSegments.length > 0 
              ? `将分割 ${selectedSegments.length} 个选定的片段` 
              : `将分割全部 ${segments.length} 个片段`}
          </p>
          
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h3 className="text-lg font-medium mb-4">输出设置</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">
                  输出格式
                </p>
                <p className="text-gray-600">
                  {settings.outputFormat.toUpperCase()}
                </p>
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">
                  输出质量
                </p>
                <p className="text-gray-600">
                  {settings.outputQuality === 'low' && '低质量 (小文件)'}
                  {settings.outputQuality === 'medium' && '中等质量'}
                  {settings.outputQuality === 'high' && '高质量 (大文件)'}
                </p>
              </div>
              
              <div className="md:col-span-2">
                <p className="text-sm font-medium text-gray-700 mb-1">
                  保持句子完整性
                </p>
                <p className="text-gray-600">
                  {settings.preserveSentences ? '是' : '否'}
                </p>
              </div>
            </div>
          </div>
        </div>
        
        {error && (
          <div className="p-3 bg-red-50 text-red-700 rounded">
            {error}
          </div>
        )}
        
        <div className="flex justify-between mt-6">
          <button
            type="button"
            onClick={() => setCurrentStep(2)}
            className="btn-secondary"
          >
            返回
          </button>
          
          <button
            type="button"
            onClick={handleSplit}
            disabled={uiState.isSplitting}
            className={`btn-primary flex items-center ${uiState.isSplitting ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {uiState.isSplitting ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                处理中...
              </>
            ) : (
              <>
                <FiScissors className="mr-2" />
                开始分割
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
} 