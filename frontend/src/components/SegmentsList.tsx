'use client';

import { useState, useEffect, useRef } from 'react';
import { FiCheckCircle, FiCircle, FiEdit, FiSearch, FiClock, FiFilter, FiX } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import { Segment } from '@/lib/api';

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
  
  // 计算最长片段的持续时间
  const maxSegmentDuration = Math.ceil(
    segments.reduce((max, segment) => {
      const duration = segment.end - segment.start;
      return duration > max ? duration : max;
    }, 0)
  );
  
  // 本地状态
  const [filterQuery, setFilterQuery] = useState('');
  const [selectAll, setSelectAll] = useState(false);
  // 过滤模式: 'filter'=过滤关键词, 'select'=选择包含关键词的片段
  const [filterMode, setFilterMode] = useState<'filter' | 'select'>('filter');
  // 添加时间区间过滤状态 - 默认范围是0到最长片段的时长
  const [minDuration, setMinDuration] = useState<number>(0);
  const [maxDuration, setMaxDuration] = useState<number>(maxSegmentDuration || 20);
  // 添加被剔除片段的状态
  const [rejectedSegments, setRejectedSegments] = useState<Segment[]>([]);
  // 添加当前活动Tab状态
  const [activeTab, setActiveTab] = useState<'all' | 'selected' | 'rejected'>('all');
  
  // 滑块引用
  const minSliderRef = useRef<HTMLDivElement>(null);
  const maxSliderRef = useRef<HTMLDivElement>(null);
  const sliderTrackRef = useRef<HTMLDivElement>(null);
  
  // 当任务状态变化时重置选择状态
  useEffect(() => {
    // 当进入分割音频步骤时，清空已选择和已剔除的片段
    if (currentTask?.status === 'completed') {
      clearSelectedSegments();
      setRejectedSegments([]);
      setActiveTab('all');
    }
  }, [currentTask, clearSelectedSegments]);
  
  // 当segments变化时更新maxDuration
  useEffect(() => {
    const newMaxDuration = Math.ceil(
      segments.reduce((max, segment) => {
        const duration = segment.end - segment.start;
        return duration > max ? duration : max;
      }, 0)
    );
    
    if (newMaxDuration > 0) {
      // 只有当计算出的最大持续时间大于0时才更新
      setMaxDuration(newMaxDuration);
      // 如果当前minDuration比newMaxDuration大，重置minDuration
      if (minDuration > newMaxDuration) {
        setMinDuration(0);
      }
    }
  }, [segments, minDuration]);
  
  // 设置滑块拖动事件
  useEffect(() => {
    const handleMinDrag = (e: MouseEvent) => {
      if (!sliderTrackRef.current) return;
      const track = sliderTrackRef.current;
      const rect = track.getBoundingClientRect();
      const percentage = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const newValue = Math.round(percentage * maxSegmentDuration);
      
      // 确保最小值不大于最大值
      if (newValue <= maxDuration) {
        setMinDuration(newValue);
      }
    };
    
    const handleMaxDrag = (e: MouseEvent) => {
      if (!sliderTrackRef.current) return;
      const track = sliderTrackRef.current;
      const rect = track.getBoundingClientRect();
      const percentage = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const newValue = Math.round(percentage * maxSegmentDuration);
      
      // 确保最大值不小于最小值
      if (newValue >= minDuration) {
        setMaxDuration(newValue);
      }
    };
    
    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMinDrag);
      document.removeEventListener('mousemove', handleMaxDrag);
      document.removeEventListener('mouseup', handleMouseUp);
    };
    
    // 创建独立的事件处理器，分别处理最小值和最大值滑块
    const setupMinDragEvents = (e: MouseEvent) => {
      e.preventDefault();
      document.addEventListener('mousemove', handleMinDrag);
      document.addEventListener('mouseup', handleMouseUp);
    };
    
    const setupMaxDragEvents = (e: MouseEvent) => {
      e.preventDefault();
      document.addEventListener('mousemove', handleMaxDrag);
      document.addEventListener('mouseup', handleMouseUp);
    };
    
    const minSlider = minSliderRef.current;
    const maxSlider = maxSliderRef.current;
    
    if (minSlider) {
      minSlider.addEventListener('mousedown', setupMinDragEvents);
    }
    
    if (maxSlider) {
      maxSlider.addEventListener('mousedown', setupMaxDragEvents);
    }
    
    return () => {
      if (minSlider) {
        minSlider.removeEventListener('mousedown', setupMinDragEvents);
      }
      if (maxSlider) {
        maxSlider.removeEventListener('mousedown', setupMaxDragEvents);
      }
      document.removeEventListener('mousemove', handleMinDrag);
      document.removeEventListener('mousemove', handleMaxDrag);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [minDuration, maxDuration, maxSegmentDuration]);
  
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
  
  // 基于关键词过滤或选择分段
  const applyKeywordFilter = () => {
    if (!filterQuery.trim()) return segments;
    
    // 分割过滤关键词（支持中英文逗号）
    const filterWords = filterQuery.split(/[,，]/).map(word => word.trim()).filter(word => word);
    
    if (filterMode === 'filter') {
      // 过滤模式：如果段落中包含任何一个过滤词，则过滤掉该段落
      return segments.filter(segment => 
        !filterWords.some(word => segment.text.toLowerCase().includes(word.toLowerCase()))
      );
    } else {
      // 选择模式：如果段落中包含任何一个关键词，则选择该段落
      const matchedSegments = segments.filter(segment => 
        filterWords.some(word => segment.text.toLowerCase().includes(word.toLowerCase()))
      );
      
      // 自动选择匹配的段落
      matchedSegments.forEach(segment => {
        if (!selectedSegments.some(s => s.id === segment.id) && 
            !rejectedSegments.some(s => s.id === segment.id)) {
          selectSegment(segment);
        }
      });
      
      // 返回匹配的段落
      return matchedSegments;
    }
  };
  
  // 应用关键词过滤/选择
  const keywordFilteredSegments = applyKeywordFilter();
  
  // 应用时长过滤
  const durationFilteredSegments = keywordFilteredSegments.filter(segment => {
    const duration = segment.end - segment.start;
    return duration >= minDuration && duration <= maxDuration;
  });
  
  // 根据当前标签页决定显示哪些分段
  const displaySegments = (() => {
    switch (activeTab) {
      case 'selected':
        return durationFilteredSegments.filter(segment => 
          selectedSegments.some(s => s.id === segment.id)
        );
      case 'rejected':
        // 对被剔除的段落也应用关键词和时长过滤
        return rejectedSegments.filter(segment => {
          // 应用时长过滤
          const duration = segment.end - segment.start;
          const durationMatches = duration >= minDuration && duration <= maxDuration;
          
          // 应用关键词过滤
          let keywordMatches = true;
          if (filterQuery.trim()) {
            const filterWords = filterQuery.split(/[,，]/).map(word => word.trim()).filter(word => word);
            if (filterMode === 'filter') {
              // 过滤模式
              keywordMatches = !filterWords.some(word => 
                segment.text.toLowerCase().includes(word.toLowerCase())
              );
            } else {
              // 选择模式
              keywordMatches = filterWords.some(word => 
                segment.text.toLowerCase().includes(word.toLowerCase())
              );
            }
          }
          
          return durationMatches && keywordMatches;
        });
      default: // 'all'
        return durationFilteredSegments;
    }
  })();
  
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
      // 全选当前显示的段落，同时确保不在rejected列表中的段落才能被选择
      displaySegments.forEach(segment => {
        if (!selectedSegments.some(s => s.id === segment.id) && 
            !rejectedSegments.some(s => s.id === segment.id)) {
          selectSegment(segment);
        }
      });
    }
    setSelectAll(!selectAll);
  };
  
  // 处理单个选择
  const handleSelect = (segment: Segment) => {
    // 检查段落是否已在剔除列表中
    const isRejected = rejectedSegments.some(s => s.id === segment.id);
    
    // 如果已剔除，先从剔除列表中移除
    if (isRejected) {
      setRejectedSegments(rejectedSegments.filter(s => s.id !== segment.id));
    }
    
    // 然后处理选择/取消选择
    if (selectedSegments.some(s => s.id === segment.id)) {
      unselectSegment(segment.id);
    } else {
      selectSegment(segment);
    }
  };
  
  // 处理拒绝/剔除段落
  const handleReject = (segment: Segment) => {
    if (!rejectedSegments.some(s => s.id === segment.id)) {
      // 添加到剔除列表
      setRejectedSegments([...rejectedSegments, segment]);
      
      // 如果该段落已选择，则取消选择
      if (selectedSegments.some(s => s.id === segment.id)) {
        unselectSegment(segment.id);
      }
    }
  };
  
  // 恢复已拒绝的段落
  const handleRestore = (segment: Segment) => {
    setRejectedSegments(rejectedSegments.filter(s => s.id !== segment.id));
  };
  
  // 处理最小持续时间变化
  const handleMinDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (value < maxDuration) {
      setMinDuration(value);
    }
  };
  
  // 处理最大持续时间变化
  const handleMaxDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    if (value > minDuration) {
      setMaxDuration(value);
    }
  };
  
  // 获取各个标签页的分段数量
  const getFilteredCounts = () => {
    // 过滤后的全部片段
    const allFiltered = durationFilteredSegments.length;
    
    // 过滤后的已选择片段
    const selectedFiltered = durationFilteredSegments.filter(segment => 
      selectedSegments.some(s => s.id === segment.id)
    ).length;
    
    // 过滤后的已剔除片段
    const rejectedFiltered = rejectedSegments.filter(segment => {
      const duration = segment.end - segment.start;
      const durationMatches = duration >= minDuration && duration <= maxDuration;
      
      let keywordMatches = true;
      if (filterQuery.trim()) {
        const filterWords = filterQuery.split(/[,，]/).map(word => word.trim()).filter(word => word);
        if (filterMode === 'filter') {
          keywordMatches = !filterWords.some(word => 
            segment.text.toLowerCase().includes(word.toLowerCase())
          );
        } else {
          keywordMatches = filterWords.some(word => 
            segment.text.toLowerCase().includes(word.toLowerCase())
          );
        }
      }
      
      return durationMatches && keywordMatches;
    }).length;
    
    return {
      all: allFiltered,
      selected: selectedFiltered,
      rejected: rejectedFiltered,
      totalAll: segments.length,
      totalSelected: selectedSegments.length,
      totalRejected: rejectedSegments.length
    };
  };
  
  const filteredCounts = getFilteredCounts();
  
  // 获取标签页信息
  const getTabInfo = (tab: 'all' | 'selected' | 'rejected') => {
    switch (tab) {
      case 'all':
        return { 
          icon: <FiCircle className="text-gray-500" />, 
          text: `全部 (${filteredCounts.all}/${filteredCounts.totalAll})` 
        };
      case 'selected':
        return { 
          icon: <FiCheckCircle className="text-green-500" />, 
          text: `已选择 (${filteredCounts.selected}/${filteredCounts.totalSelected})` 
        };
      case 'rejected':
        return { 
          icon: <FiX className="text-red-500" />, 
          text: `已剔除 (${filteredCounts.rejected}/${filteredCounts.totalRejected})` 
        };
    }
  };
  
  // 检查段落状态
  const getSegmentStatus = (segment: Segment) => {
    if (selectedSegments.some(s => s.id === segment.id)) {
      return 'selected';
    }
    if (rejectedSegments.some(s => s.id === segment.id)) {
      return 'rejected';
    }
    return 'none';
  };
  
  return (
    <div className="card mb-8">
      <div className="card-header">
        <h2 className="text-xl font-medium">音频内容分段</h2>
      </div>
      
      <div className="card-body">
        {/* 过滤和控制区域 - 调整为使用Grid布局 */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 mb-4 items-center">
          {/* 过滤模式选择器 - 占1列 */}
          <div className="md:col-span-2">
            <select 
              value={filterMode}
              onChange={(e) => setFilterMode(e.target.value as 'filter' | 'select')}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="filter">过滤模式</option>
              <option value="select">选择模式</option>
            </select>
          </div>
          
          {/* 搜索框 - 占5列 */}
          <div className="md:col-span-5">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <FiFilter className="text-gray-400" />
              </div>
              <input
                type="text"
                placeholder={
                  filterMode === 'filter' 
                    ? "过滤内容(多个关键词用逗号分隔)..." 
                    : "选择包含关键词的段落(多个关键词用逗号分隔)..."
                }
                value={filterQuery}
                onChange={e => setFilterQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          
          {/* 时间区间筛选 - 占4列 */}
          <div className="md:col-span-4">
            <div className="flex items-center">
              <FiClock className="text-gray-500 mr-1 flex-shrink-0" />
              <span className="text-sm text-gray-700 whitespace-nowrap mr-2">时长: {minDuration}s-{maxDuration}s</span>
              <div className="relative w-full h-10 flex items-center" ref={sliderTrackRef}>
                {/* 背景轨道 */}
                <div className="absolute left-0 right-0 h-3 bg-gray-200 rounded-full"></div>
                
                {/* 选中区域 */}
                <div 
                  className="absolute h-3 bg-primary-500 rounded-full"
                  style={{ 
                    left: `${(minDuration / maxSegmentDuration) * 100}%`, 
                    right: `${100 - ((maxDuration / maxSegmentDuration) * 100)}%` 
                  }}
                ></div>
                
                {/* 最小值滑块指示器 */}
                <div 
                  ref={minSliderRef}
                  className="absolute w-6 h-6 bg-white border-2 border-primary-600 rounded-full shadow-md transform -translate-x-1/2 z-10 cursor-grab hover:scale-110 transition-transform"
                  style={{ 
                    left: `${(minDuration / maxSegmentDuration) * 100}%`, 
                    top: '50%',
                    marginTop: '-12px'
                  }}
                ></div>
                
                {/* 最大值滑块指示器 */}
                <div 
                  ref={maxSliderRef}
                  className="absolute w-6 h-6 bg-white border-2 border-primary-600 rounded-full shadow-md transform -translate-x-1/2 z-10 cursor-grab hover:scale-110 transition-transform"
                  style={{ 
                    left: `${(maxDuration / maxSegmentDuration) * 100}%`, 
                    top: '50%',
                    marginTop: '-12px'
                  }}
                ></div>
              </div>
            </div>
          </div>
          
          {/* 分段信息 - 占1列 */}
          <div className="md:col-span-1 text-right">
            <p className="text-sm text-gray-600 whitespace-nowrap">
              {displaySegments.length}/{
                activeTab === 'all' ? segments.length :
                activeTab === 'selected' ? selectedSegments.length :
                rejectedSegments.length
              }
            </p>
          </div>
        </div>
        
        {/* 标签导航 */}
        <div className="flex border-b border-gray-200 mb-4">
          {(['all', 'selected', 'rejected'] as const).map(tab => {
            const tabInfo = getTabInfo(tab);
            return (
              <button
                key={tab}
                className={`flex items-center py-3 px-4 border-b-2 text-sm font-medium ${
                  activeTab === tab 
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
                onClick={() => setActiveTab(tab)}
              >
                {tabInfo.icon}
                <span className="ml-2">{tabInfo.text}</span>
              </button>
            );
          })}
          
          {/* 全选按钮移到标签导航行 */}
          {activeTab !== 'rejected' && (
            <div className="ml-auto self-center mr-2">
              <button
                type="button"
                onClick={handleSelectAll}
                className="flex items-center text-sm text-gray-600 hover:text-primary-600 h-10 px-3 border border-gray-300 rounded-md"
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
          )}
        </div>
        
        <div className="overflow-hidden border border-gray-200 rounded-lg">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
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
              {displaySegments.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                    没有找到匹配的内容
                  </td>
                </tr>
              ) : (
                displaySegments.map(segment => {
                  const status = getSegmentStatus(segment);
                  
                  return (
                    <tr 
                      key={segment.id}
                      className={
                        status === 'selected' ? 'bg-primary-50' :
                        status === 'rejected' ? 'bg-red-50' : undefined
                      }
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {activeTab !== 'rejected' ? (
                            <>
                              <button
                                type="button"
                                onClick={() => handleSelect(segment)}
                                className="text-gray-400 hover:text-primary-600"
                                title={status === 'selected' ? "取消选择" : "选择"}
                              >
                                {status === 'selected' ? (
                                  <FiCheckCircle className="w-5 h-5 text-primary-600" />
                                ) : (
                                  <FiCircle className="w-5 h-5" />
                                )}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleReject(segment)}
                                className={`hover:text-red-600 ${status === 'rejected' ? 'text-red-600' : 'text-gray-400'}`}
                                title="剔除"
                              >
                                <FiX className="w-5 h-5" />
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleRestore(segment)}
                              className="text-gray-400 hover:text-green-600"
                              title="恢复"
                            >
                              <FiCheckCircle className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatTime(segment.start)} - {formatTime(segment.end)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatTime(segment.end - segment.start)}
                      </td>
                      <td className={`px-6 py-4 text-sm ${status === 'rejected' ? 'text-red-500 line-through' : 'text-gray-900'}`}>
                        {segment.text}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
} 