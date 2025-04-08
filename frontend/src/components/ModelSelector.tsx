'use client';

import { useState, useEffect } from 'react';
import { FiCpu, FiSave, FiSettings, FiChevronDown, FiChevronUp, FiDollarSign } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import apiService from '@/lib/api';

export function ModelSelector() {
  // 使用应用状态
  const {
    currentTask,
    setIsAnalyzing,
    setCurrentStep,
    setSegments
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
  
  // 处理音频分析 - 简化版，使用API服务不需要模型选择
  const handleAnalyze = async () => {
    if (!currentTask) return;
    
    try {
      setIsAnalyzing(true);
      setError(null);
      
      // 直接调用分析API - 服务器端会检查余额
      const response = await apiService.analyzeAudio(currentTask.id);
      
      // 更新分段数据
      setSegments(response.segments);
      
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
        setCurrentStep(3);
      }, 1000);
      
    } catch (error: any) {
      console.error('分析失败:', error);
      
      // 检查是否为余额不足错误 (HTTP 402)
      if (error.response && error.response.status === 402) {
        const data = error.response.data;
        setError(`余额不足，当前余额 ${data.current_balance.toFixed(0)} 点，需要 ${data.estimated_cost.toFixed(0)} 点。请先充值。`);
      }
      // 检查是否为任务不存在错误
      else if (error.response && error.response.status === 400 && 
          error.response.data && error.response.data.error === "无效的任务ID") {
        setError('任务已过期或不存在，请返回上传页面重新上传文件');
      } else if (error.code === 'ERR_NETWORK') {
        setError('网络连接失败，请检查网络连接并重试');
      } else {
        setError('音频分析失败，请重试。');
      }
      
      // 将当前任务标记为分析失败，但保留其他信息
      if (currentTask) {
        const updatedTask = {
          ...currentTask,
          status: 'failed',
          message: '分析失败',
          failedAtStep: 'uploaded', // 标记失败的步骤
          lastSuccessfulStep: 'uploaded', // 记录最后成功的步骤
          errorDetails: error.message || '音频分析失败'
        };
        useAppStore.getState().setCurrentTask(updatedTask);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  // 渲染简化的模型选择器
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-xl font-medium">开始音频分析</h2>
      </div>
      
      <div className="card-body">
        <p className="mb-4">点击下方按钮开始音频内容分析，分析完成后可以查看结果并分割音频。</p>
        
        {currentTask.estimated_cost !== undefined && (
          <div className="bg-primary-50 border border-primary-100 rounded p-3 mb-4 flex items-center">
            <FiDollarSign className="text-primary-500 mr-2" />
            <div>
              <p className="text-gray-700">
                <span className="font-medium">预估费用: </span>
                <span className="text-primary-600 font-semibold">{currentTask.estimated_cost.toFixed(0)} 点数</span>
              </p>
              <p className="text-xs text-gray-500">分析完成后将从您的账户中扣除</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-500 p-3 rounded mb-4">
            {error}
          </div>
        )}
        
        {/* 重试按钮 - 仅在任务失败且当前步骤是上传后的分析步骤时显示 */}
        {currentTask?.status === 'failed' && currentTask?.lastSuccessfulStep === 'uploaded' && (
          <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 p-3 rounded mb-4">
            <p className="mb-2">上次分析失败，您可以重试。</p>
            <button
              onClick={handleAnalyze}
              className="bg-yellow-500 hover:bg-yellow-600 text-white font-medium py-2 px-4 rounded-md"
            >
              重试分析
            </button>
          </div>
        )}
        
        <button
          type="button"
          onClick={handleAnalyze}
          className="btn btn-primary w-full flex justify-center items-center"
          disabled={!currentTask || useAppStore.getState().uiState.isAnalyzing}
        >
          {useAppStore.getState().uiState.isAnalyzing ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              处理中...
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
  );
}

/* 原始复杂ModelSelector组件已注释掉
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
    modelsPricing,
    setModelsPricing,
  } = useAppStore();
  
  // 本地状态
  const [error, setError] = useState<string | null>(null);
  const [isLoadingPricing, setIsLoadingPricing] = useState(false);
  
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
  
  // 加载定价信息
  useEffect(() => {
    if (currentTask && currentTask.id) {
      loadPricingInfo();
    }
  }, [currentTask]);
  
  // 获取定价信息
  const loadPricingInfo = async () => {
    try {
      setIsLoadingPricing(true);
      
      // 使用任务的实际文件大小
      const fileSizeMb = currentTask.size_mb || 0;
      
      const pricingData = await apiService.getModelsPricing(fileSizeMb);
      setModelsPricing(pricingData);
    } catch (error) {
      console.error('获取定价信息失败:', error);
    } finally {
      setIsLoadingPricing(false);
    }
  };
  
  // 处理音频分析
  const handleAnalyze = async () => {
    if (!currentTask) return;
    
    try {
      setIsAnalyzing(true);
      setError(null);
      
      // 使用任务的实际文件大小
      const fileSizeMb = currentTask.size_mb || 0;
      
      // 检查余额是否足够
      const balanceCheck = await apiService.checkBalance(fileSizeMb, settings.modelSize);
      
      if (!balanceCheck.is_sufficient) {
        setError(`余额不足，当前余额 ${balanceCheck.current_balance.toFixed(0)} 点，需要 ${balanceCheck.estimated_cost.toFixed(0)} 点。请先充值。`);
        setIsAnalyzing(false);
        return;
      }
      
      // 调用分析API
      const response = await apiService.analyzeAudio(currentTask.id, settings.modelSize);
      
      // 更新分段数据
      setSegments(response.segments);
      
      // 转到下一步
      setTimeout(() => {
        setCurrentStep(3);
      }, 1000);
      
    } catch (error: any) {
      console.error('分析失败:', error);
      // 检查是否为任务不存在错误
      if (error.response && error.response.status === 400 && 
          error.response.data && error.response.data.error === "无效的任务ID") {
        setError('任务已过期或不存在，请返回上传页面重新上传文件');
      } else if (error.code === 'ERR_NETWORK') {
        setError('网络连接失败，请检查网络连接并重试');
      } else {
        setError('音频分析失败，请重试。');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };
  
  // 获取模型定价信息
  const getModelPricing = (size: string) => {
    if (!modelsPricing || !modelsPricing[size]) {
      return null;
    }
    return modelsPricing[size];
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
            更大的模型识别更准确，但处理速度更慢和消耗更多点数
          </p>
          
          {currentTask && currentTask.size_mb > 0 && (
            <p className="text-sm text-primary-600 mb-4">
              当前文件大小: {currentTask.size_mb.toFixed(2)} MB
            </p>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {['tiny', 'base', 'small', 'medium', 'large'].map((size) => {
              const pricing = getModelPricing(size);
              return (
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
                  
                  {pricing && pricing.estimated_cost !== undefined && (
                    <div className="mt-2 flex items-center text-xs">
                      <FiDollarSign className="mr-1 text-green-500" />
                      <span className="text-green-600 font-medium">
                        {pricing.estimated_cost.toFixed(0)} 点
                      </span>
                    </div>
                  )}
                  
                  {isLoadingPricing && !pricing && (
                    <div className="mt-2 text-xs text-gray-400">加载中...</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
        
        {settings.modelSize && modelsPricing && modelsPricing[settings.modelSize] && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg mt-4">
            <h3 className="text-sm font-medium text-green-800 flex items-center">
              <FiDollarSign className="mr-1" />
              费用明细 
              {currentTask && currentTask.size_mb !== undefined && (
                <span className="ml-2 text-xs font-normal text-green-600">
                  (文件大小: {currentTask.size_mb.toFixed(2)} MB)
                </span>
              )}
            </h3>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-green-700">
              <div>基础费用:</div>
              <div className="text-right">{modelsPricing[settings.modelSize]?.details?.base_price?.toFixed(0) || '0'} 点</div>
              
              <div>文件大小费用:</div>
              <div className="text-right">{modelsPricing[settings.modelSize]?.details?.file_size_cost?.toFixed(0) || '0'} 点</div>
              
              <div>处理时长费用:</div>
              <div className="text-right">{modelsPricing[settings.modelSize]?.details?.duration_cost?.toFixed(0) || '0'} 点</div>
              
              <div className="border-t border-green-200 pt-1 font-medium">总计:</div>
              <div className="border-t border-green-200 pt-1 text-right font-medium">
                {modelsPricing[settings.modelSize]?.estimated_cost?.toFixed(0) || '0'} 点
              </div>
            </div>
          </div>
        )}
        
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
                开始分析 {modelsPricing && modelsPricing[settings.modelSize]?.estimated_cost !== undefined ? `(${modelsPricing[settings.modelSize].estimated_cost.toFixed(0)}点)` : ''}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
*/ 