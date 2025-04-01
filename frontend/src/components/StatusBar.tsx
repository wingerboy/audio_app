'use client';

import React from 'react';
import { TaskStatus } from '@/lib/api';

interface StatusBarProps {
  task: TaskStatus;
}

type TaskStatusType = 'uploaded' | 'processing' | 'analyzed' | 'splitting' | 'completed' | 'failed';

interface StatusConfig {
  color: string;
  text: string;
}

export function StatusBar({ task }: StatusBarProps) {
  // 文件状态对应的图标和颜色
  const statusConfig: Record<TaskStatusType, StatusConfig> = {
    uploaded: {
      color: 'bg-blue-500',
      text: '已上传',
    },
    processing: {
      color: 'bg-yellow-500',
      text: '处理中',
    },
    analyzed: {
      color: 'bg-green-500',
      text: '分析完成',
    },
    splitting: {
      color: 'bg-yellow-500',
      text: '分割中',
    },
    completed: {
      color: 'bg-green-500',
      text: '完成',
    },
    failed: {
      color: 'bg-red-500',
      text: '失败',
    },
  };
  
  // 获取当前状态配置
  const currentStatus = statusConfig[task.status as TaskStatusType] || {
    color: 'bg-gray-500',
    text: '未知状态',
  };
  
  return (
    <div className="mb-8 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div className="flex items-center mb-2 md:mb-0">
          <div className={`w-3 h-3 rounded-full mr-2 ${currentStatus.color}`}></div>
          <span className="font-medium text-gray-800">{task.filename}</span>
          <span className="ml-2 text-sm text-gray-500">({task.size_mb.toFixed(2)} MB)</span>
          {task.audio_duration_minutes && (
            <span className="ml-2 text-sm text-gray-500">
              ({Math.floor(task.audio_duration_minutes)}分{Math.floor((task.audio_duration_minutes % 1) * 60)}秒)
            </span>
          )}
        </div>
        
        <div className="flex items-center">
          <span className="text-sm text-gray-600 mr-4">{currentStatus.text}</span>
          {task.status === 'processing' || task.status === 'splitting' ? (
            <div className="w-full max-w-xs">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`${currentStatus.color} h-2 rounded-full`}
                  style={{ width: `${task.progress}%` }}
                ></div>
              </div>
              <div className="text-xs text-gray-500 mt-1 text-right">
                {task.progress}%
              </div>
            </div>
          ) : null}
        </div>
      </div>
      
      {task.message && (
        <div className="mt-2 text-sm text-gray-600">
          {task.message}
        </div>
      )}
    </div>
  );
} 