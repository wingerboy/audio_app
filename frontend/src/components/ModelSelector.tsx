'use client';

import { useState } from 'react';
import { FiCpu, FiSave, FiSettings, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import apiService from '@/lib/api';

export function ModelSelector() {
  // 使用应用状态
  const {
    currentTask,
    settings,
    updateSettings,
    segments,
    setSegments,
    uiState,
    setIsAnalyzing,
    setCurrentStep,
    toggleShowAdvanced,
  } = useAppStore();
  
  // 本地状态
  const [error, setError] = useState<string | null>(null);
  
  // 没有任务则显示错误
  if (!currentTask) {
    return (
      <div className="card">
        <div className="card-body">
          <p className="text-red-600">请先上传文件</p>
        </div>
      </div>
    );
  }
  
  // 处理音频分析
  const handleAnalyze = async () => {
    if (!currentTask) return;
    
    try {
      setIsAnalyzing(true);
      setError(null);
      
      // 调用分析API
      const response = await apiService.analyzeAudio(currentTask.id, settings.modelSize);
      
      // 更新分段数据
      setSegments(response.segments);
      
      // 转到下一步
      setTimeout(() => {
        setCurrentStep(3);
      }, 1000);
      
    } catch (error) {
      console.error('分析失败:', error);
      setError('音频分析失败，请重试。');
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  // 渲染模型选择器
  return (
    <div className="card">
      <div className="card-header flex justify-between items-center">
        <h2 className="text-xl font-medium">选择AI模型</h2>
        <button
          type="button"
          onClick={toggleShowAdvanced}
          className="flex items-center text-sm text-gray-600 hover:text-primary-600"
        >
          <FiSettings className="mr-1" />
          {uiState.showAdvanced ? (
            <>
              <span>隐藏高级选项</span>
              <FiChevronUp className="ml-1" />
            </>
          ) : (
            <>
              <span>显示高级选项</span>
              <FiChevronDown className="ml-1" />
            </>
          )}
        </button>
      </div>
      
      <div className="card-body space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            选择模型大小
          </label>
          <p className="text-sm text-gray-500 mb-3">
            更大的模型识别更准确，但处理速度更慢
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {['tiny', 'base', 'small', 'medium', 'large'].map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => updateSettings({ modelSize: size })}
                className={`flex flex-col items-center justify-center p-4 border rounded-lg hover:border-primary-400 hover:bg-primary-50 transition-colors ${
                  settings.modelSize === size
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-300'
                }`}
              >
                <FiCpu 
                  className={`w-6 h-6 mb-2 ${
                    settings.modelSize === size ? 'text-primary-600' : 'text-gray-400'
                  }`} 
                />
                <span className="capitalize">{size}</span>
                <span className="text-xs text-gray-500 mt-1">
                  {size === 'tiny' && '速度最快'}
                  {size === 'base' && '平衡'}
                  {size === 'small' && '较准确'}
                  {size === 'medium' && '很准确'}
                  {size === 'large' && '最准确'}
                </span>
              </button>
            ))}
          </div>
        </div>
        
        {uiState.showAdvanced && (
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
            <h3 className="text-lg font-medium mb-4">高级选项</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  最小片段长度 (秒)
                </label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={settings.minSegment}
                  onChange={(e) => updateSettings({ minSegment: parseInt(e.target.value) })}
                  className="form-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  最大片段长度 (秒)
                </label>
                <input
                  type="number"
                  min="30"
                  max="300"
                  value={settings.maxSegment}
                  onChange={(e) => updateSettings({ maxSegment: parseInt(e.target.value) })}
                  className="form-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  输出格式
                </label>
                <select
                  value={settings.outputFormat}
                  onChange={(e) => updateSettings({ outputFormat: e.target.value })}
                  className="form-select"
                >
                  <option value="mp3">MP3</option>
                  <option value="wav">WAV</option>
                  <option value="ogg">OGG</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  输出质量
                </label>
                <select
                  value={settings.outputQuality}
                  onChange={(e) => updateSettings({ outputQuality: e.target.value })}
                  className="form-select"
                >
                  <option value="low">低质量 (小文件)</option>
                  <option value="medium">中等质量</option>
                  <option value="high">高质量 (大文件)</option>
                </select>
              </div>
              
              <div className="md:col-span-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.preserveSentences}
                    onChange={(e) => updateSettings({ preserveSentences: e.target.checked })}
                    className="form-checkbox"
                  />
                  <span className="ml-2 text-sm text-gray-700">保持句子完整性 (避免在句子中间分割)</span>
                </label>
              </div>
            </div>
          </div>
        )}
        
        {error && (
          <div className="p-3 bg-red-50 text-red-700 rounded">
            {error}
          </div>
        )}
        
        <div className="flex justify-between mt-6">
          <button
            type="button"
            onClick={() => setCurrentStep(1)}
            className="btn-secondary"
          >
            返回
          </button>
          
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={uiState.isAnalyzing}
            className={`btn-primary flex items-center ${uiState.isAnalyzing ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {uiState.isAnalyzing ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                分析中...
              </>
            ) : (
              <>
                <FiSave className="mr-2" />
                开始分析
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
} 