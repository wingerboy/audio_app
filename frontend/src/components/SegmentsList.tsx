'use client';

import { useState } from 'react';
import { FiCheckCircle, FiCircle, FiEdit, FiSearch } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import { Segment } from '@/lib/api';
import { TimeRangeSlider } from './TimeRangeSlider';

export function SegmentsList() {
  // 使用应用状态
  const { 
    currentTask, 
    segments, 
    selectedSegments,
    selectSegment,
    unselectSegment,
    clearSelectedSegments
  } = useAppStore();
  
  // 本地状态
  const [searchQuery, setSearchQuery] = useState('');
  const [selectAll, setSelectAll] = useState(false);
  
  // 如果没有任务或分段数据，显示错误
  if (!currentTask || segments.length === 0) {
    return (
      <div className="card">
        <div className="card-body">
          <p className="text-red-600">请先上传文件并分析音频内容</p>
        </div>
      </div>
    );
  }
  
  // 过滤分段
  const filteredSegments = searchQuery.trim() 
    ? segments.filter(segment => 
        segment.text.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : segments;
  
  // 格式化时间
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };
  
  // 处理全选/全不选
  const handleSelectAll = () => {
    if (selectAll) {
      // 取消全选
      clearSelectedSegments();
    } else {
      // 全选
      filteredSegments.forEach(segment => {
        if (!selectedSegments.some(s => s.id === segment.id)) {
          selectSegment(segment);
        }
      });
    }
    setSelectAll(!selectAll);
  };
  
  // 处理单个选择
  const handleSelect = (segment: Segment) => {
    if (selectedSegments.some(s => s.id === segment.id)) {
      unselectSegment(segment.id);
    } else {
      selectSegment(segment);
    }
  };
  
  // 处理时间范围选择
  const handleTimeRangeSelection = (selectedByTime: Segment[]) => {
    // 先清除当前选择
    clearSelectedSegments();
    
    // 添加时间范围内的分段
    selectedByTime.forEach(segment => {
      selectSegment(segment);
    });
  };
  
  return (
    <div className="card mb-8">
      <div className="card-header">
        <h2 className="text-xl font-medium">音频内容分段</h2>
      </div>
      
      <div className="card-body">
        <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-4 space-y-3 md:space-y-0">
          <p className="text-sm text-gray-600">
            共 {segments.length} 个分段，已选择 {selectedSegments.length} 个
          </p>
          
          <div className="flex flex-col md:flex-row md:items-center space-y-2 md:space-y-0 md:space-x-4">
            <div className="flex items-center space-x-2">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <FiSearch className="text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="搜索内容..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
              
              {currentTask.audio_duration_seconds && (
                <div className="flex items-center bg-gray-50 dark:bg-gray-800 p-1 rounded-md border border-gray-200 dark:border-gray-700">
                  <span className="text-xs text-gray-500 dark:text-gray-400 mr-2 whitespace-nowrap">按时间选择:</span>
                  <TimeRangeSlider 
                    audioDuration={currentTask.audio_duration_seconds}
                    segments={segments}
                    onSelectionChange={handleTimeRangeSelection}
                  />
                </div>
              )}
            </div>
            
            <button
              type="button"
              onClick={handleSelectAll}
              className="flex items-center text-sm text-gray-600 hover:text-primary-600"
            >
              {selectAll ? (
                <>
                  <FiCircle className="mr-1" />
                  取消全选
                </>
              ) : (
                <>
                  <FiCheckCircle className="mr-1" />
                  全选
                </>
              )}
            </button>
          </div>
        </div>
        
        <div className="overflow-hidden border border-gray-200 rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  选择
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  时间
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  持续时间
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  内容
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredSegments.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                    没有找到匹配的内容
                  </td>
                </tr>
              ) : (
                filteredSegments.map(segment => (
                  <tr 
                    key={segment.id}
                    className={selectedSegments.some(s => s.id === segment.id) 
                      ? 'bg-primary-50' 
                      : undefined
                    }
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => handleSelect(segment)}
                        className="text-gray-400 hover:text-primary-600"
                      >
                        {selectedSegments.some(s => s.id === segment.id) ? (
                          <FiCheckCircle className="w-5 h-5 text-primary-600" />
                        ) : (
                          <FiCircle className="w-5 h-5" />
                        )}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatTime(segment.start)} - {formatTime(segment.end)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatTime(segment.end - segment.start)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-md truncate">
                      {segment.text}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
} 