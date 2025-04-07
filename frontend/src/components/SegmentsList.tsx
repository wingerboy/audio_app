'use client';

import { useState, useEffect } from 'react';
import { FiCheckCircle, FiCircle, FiEdit, FiSearch, FiFilter, FiCheckSquare, FiClock, FiXCircle, FiCheck, FiX } from 'react-icons/fi';
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
  
  // 本地状态
  const [filterQuery, setFilterQuery] = useState('');
  const [selectAll, setSelectAll] = useState(false);
  // 添加过滤模式状态：默认是"filter"(过滤)，另一个选项是"include"(包含)
  const [filterMode, setFilterMode] = useState<'filter' | 'include'>('filter');
  // 添加时间区间过滤状态
  const [minDuration, setMinDuration] = useState<number>(1);
  const [maxDuration, setMaxDuration] = useState<number>(20);
  // 添加被剔除片段的状态
  const [rejectedSegments, setRejectedSegments] = useState<Segment[]>([]);
  // 添加当前活动Tab状态
  const [activeTab, setActiveTab] = useState<'all' | 'selected' | 'rejected'>('all');
  
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
  
  // 处理最小持续时间变化
  const handleMinDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    setMinDuration(Math.min(value, maxDuration - 1));
  };
  
  // 处理最大持续时间变化
  const handleMaxDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value);
    setMaxDuration(Math.max(value, minDuration + 1));
  };

  // 处理剔除片段
  const rejectSegment = (segment: Segment) => {
    // 首先从已选择的片段中移除（如果存在）
    if (selectedSegments.some(s => s.id === segment.id)) {
      unselectSegment(Number(segment.id));
    }
    // 然后加入到已剔除的片段中
    if (!rejectedSegments.some(s => s.id === segment.id)) {
      setRejectedSegments([...rejectedSegments, segment]);
    }
  };

  // 取消剔除片段
  const unrejectSegment = (segmentId: string | number) => {
    setRejectedSegments(rejectedSegments.filter(s => s.id !== segmentId));
  };

  // 处理选择片段（添加互斥逻辑）
  const handleSelectSegment = (segment: Segment) => {
    if (selectedSegments.some(s => s.id === segment.id)) {
      // 如果已经被选择，则取消选择
      unselectSegment(Number(segment.id));
    } else {
      // 如果在剔除列表中，先从剔除列表移除
      if (rejectedSegments.some(s => s.id === segment.id)) {
        unrejectSegment(segment.id);
      }
      // 然后添加到选择列表
      selectSegment(segment);
    }
  };

  // 处理剔除片段（确保互斥）
  const handleRejectSegment = (segment: Segment) => {
    if (rejectedSegments.some(s => s.id === segment.id)) {
      // 如果已经被剔除，则取消剔除
      unrejectSegment(segment.id);
    } else {
      // 执行剔除（函数内部会处理互斥逻辑）
      rejectSegment(segment);
    }
  };
  
  // 基于当前活动tab和过滤条件过滤分段
  const getFilteredSegments = () => {
    // 首先，根据活动tab筛选片段
    let tabFilteredSegments: Segment[] = [];
    
    if (activeTab === 'all') {
      // 全部：显示既不在已选择也不在已剔除的片段
      tabFilteredSegments = segments.filter(segment => 
        !selectedSegments.some(s => s.id === segment.id) && 
        !rejectedSegments.some(s => s.id === segment.id)
      );
    } else if (activeTab === 'selected') {
      // 已选择：只显示已选择的片段
      tabFilteredSegments = selectedSegments;
    } else { // activeTab === 'rejected'
      // 已剔除：只显示已剔除的片段
      tabFilteredSegments = rejectedSegments;
    }
    
    // 然后，应用其他过滤条件
    return tabFilteredSegments.filter(segment => {
      // 首先检查时间区间过滤
      const duration = segment.end - segment.start;
      // 如果不在时间区间内，直接过滤掉
      if (duration < minDuration || duration > maxDuration) {
        return false;
      }
      
      // 如果没有关键词过滤，则保留该片段
      if (!filterQuery.trim()) {
        return true;
      }
      
      // 分割过滤关键词（支持中英文逗号）
      const filterWords = filterQuery.split(/[,，]/).map(word => word.trim()).filter(word => word);
      
      if (filterMode === 'filter') {
        // 过滤模式：如果段落中包含任何一个过滤词，则过滤掉该段落
        return !filterWords.some(word => 
          segment.text.toLowerCase().includes(word.toLowerCase())
        );
      } else {
        // 包含模式：如果段落中包含任何一个关键词，则保留该段落
        return filterWords.some(word => 
          segment.text.toLowerCase().includes(word.toLowerCase())
        );
      }
    });
  };
  
  // 获取当前过滤后的片段
  const filteredSegments = getFilteredSegments();
  
  // 格式化时间
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };
  
  // 处理全选/全不选（基于当前Tab）
  const handleSelectAll = () => {
    if (selectAll) {
      // 取消全选
      if (activeTab === 'selected') {
        // 在已选择标签页中：取消所有已选择
        clearSelectedSegments();
      } else if (activeTab === 'rejected') {
        // 在已剔除标签页中：取消所有已剔除
        setRejectedSegments([]);
      } else {
        // 在全部标签页中：不做任何操作，因为已经没有选择或剔除的项目
      }
    } else {
      // 全选操作根据当前标签页执行不同操作
      if (activeTab === 'all') {
        // 在全部标签页中：将所有过滤后的片段标记为已选择
        filteredSegments.forEach(segment => {
          if (!selectedSegments.some(s => s.id === segment.id)) {
            selectSegment(segment);
          }
        });
      } else if (activeTab === 'rejected') {
        // 在已剔除标签页中：不做选择操作，避免冲突
      }
    }
    setSelectAll(!selectAll);
  };
  
  // 获取输入框占位符文本
  const getPlaceholderText = () => {
    return filterMode === 'filter' 
      ? "过滤内容(多个关键词用逗号分隔)..." 
      : "选择包含关键词的片段(逗号分隔)...";
  };

  // 获取Tab状态文字和图标
  const getTabInfo = (tabName: 'all' | 'selected' | 'rejected') => {
    switch(tabName) {
      case 'all':
        return { 
          text: `全部 (${segments.length - selectedSegments.length - rejectedSegments.length})`,
          icon: <FiCircle className={activeTab === 'all' ? 'text-primary-600' : 'text-gray-400'} />
        };
      case 'selected':
        return {
          text: `已选择 (${selectedSegments.length})`,
          icon: <FiCheck className={activeTab === 'selected' ? 'text-primary-600' : 'text-gray-400'} />
        };
      case 'rejected':
        return {
          text: `已剔除 (${rejectedSegments.length})`,
          icon: <FiX className={activeTab === 'rejected' ? 'text-primary-600' : 'text-gray-400'} />
        };
    }
  };
  
  return (
    <div className="card mb-8">
      <div className="card-header">
        <h2 className="text-xl font-medium">音频内容分段</h2>
      </div>
      
      <div className="card-body">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          {/* 1. 过滤模式 */}
          <div className="flex-shrink-0">
            <select
              className="px-3 py-2 h-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              value={filterMode}
              onChange={(e) => setFilterMode(e.target.value as 'filter' | 'include')}
            >
              <option value="filter">过滤模式</option>
              <option value="include">选择模式</option>
            </select>
          </div>
          
          {/* 2. 过滤内容 */}
          <div className="relative flex-grow min-w-[200px]">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              {filterMode === 'filter' ? (
                <FiFilter className="text-gray-400" />
              ) : (
                <FiCheckSquare className="text-gray-400" />
              )}
            </div>
            <input
              type="text"
              placeholder={getPlaceholderText()}
              value={filterQuery}
              onChange={e => setFilterQuery(e.target.value)}
              className="w-full h-10 pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>
          
          {/* 3. 时间区间筛选 */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="flex items-center">
              <FiClock className="text-gray-500 mr-1" />
              <span className="text-sm text-gray-700 whitespace-nowrap">时长: {minDuration}-{maxDuration}秒</span>
            </div>
            <div className="relative w-52 h-10 flex items-center px-2">
              {/* 背景轨道 */}
              <div className="absolute left-2 right-2 h-3 bg-gray-200 rounded-full"></div>
              
              {/* 选中区域 */}
              <div 
                className="absolute h-3 bg-primary-500 rounded-full"
                style={{ 
                  left: `${(minDuration - 1) / 19 * 100}%`, 
                  right: `${(20 - maxDuration) / 19 * 100}%` 
                }}
              ></div>
              
              {/* 最小值滑块 */}
              <input
                type="range"
                min="1"
                max="19"
                step="1"
                value={minDuration}
                onChange={handleMinDurationChange}
                className="absolute left-2 right-2 h-10 appearance-none bg-transparent pointer-events-none"
                style={{ 
                  // 使最小值滑块的上半部分可交互，下半部分不可交互
                  clipPath: 'inset(0 0 50% 0)',
                  // 移除WebKit默认样式
                  WebkitAppearance: 'none'
                }}
              />
              
              {/* 最大值滑块 */}
              <input
                type="range"
                min="2"
                max="20"
                step="1"
                value={maxDuration}
                onChange={handleMaxDurationChange}
                className="absolute left-2 right-2 h-10 appearance-none bg-transparent pointer-events-none"
                style={{ 
                  // 使最大值滑块的下半部分可交互，上半部分不可交互
                  clipPath: 'inset(50% 0 0 0)',
                  // 移除WebKit默认样式
                  WebkitAppearance: 'none'
                }}
              />
              
              {/* 最小值滑块指示器 */}
              <div 
                className="absolute w-6 h-6 bg-white border-2 border-primary-600 rounded-full shadow-md transform -translate-x-1/2 z-10 cursor-grab hover:scale-110 transition-transform"
                style={{ 
                  left: `${(minDuration - 1) / 19 * 100}%`, 
                  top: '50%',
                  marginTop: '-12px'
                }}
              >
                {/* 扩大拖动区域 */}
                <div 
                  className="absolute -left-4 -right-4 -top-4 -bottom-4 cursor-grab"
                  onMouseDown={(e) => {
                    // 阻止事件冒泡，确保下面的滑块不会同时触发
                    e.stopPropagation();
                    
                    // 设置指示器为活动状态的样式
                    const handle = e.currentTarget.parentNode as HTMLDivElement;
                    handle.classList.add('scale-110');
                    handle.classList.add('cursor-grabbing');
                    handle.classList.remove('cursor-grab');
                    
                    // 监听鼠标移动和释放事件
                    const handleMouseMove = (moveEvent: MouseEvent) => {
                      const slider = handle.parentNode as HTMLDivElement;
                      const rect = slider.getBoundingClientRect();
                      const offsetX = moveEvent.clientX - rect.left;
                      const width = rect.width;
                      const percentage = Math.max(0, Math.min(1, offsetX / width));
                      
                      // 计算新的minDuration值
                      const newValue = Math.max(1, Math.min(maxDuration - 1, Math.round(percentage * 19) + 1));
                      if (newValue !== minDuration) {
                        setMinDuration(newValue);
                      }
                    };
                    
                    const handleMouseUp = () => {
                      // 移除活动状态样式
                      handle.classList.remove('cursor-grabbing');
                      handle.classList.add('cursor-grab');
                      
                      // 移除事件监听器
                      window.removeEventListener('mousemove', handleMouseMove);
                      window.removeEventListener('mouseup', handleMouseUp);
                    };
                    
                    window.addEventListener('mousemove', handleMouseMove);
                    window.addEventListener('mouseup', handleMouseUp);
                  }}
                ></div>
              </div>
              
              {/* 最大值滑块指示器 */}
              <div 
                className="absolute w-6 h-6 bg-white border-2 border-primary-600 rounded-full shadow-md transform -translate-x-1/2 z-10 cursor-grab hover:scale-110 transition-transform"
                style={{ 
                  left: `${(maxDuration - 1) / 19 * 100}%`, 
                  top: '50%',
                  marginTop: '-12px'
                }}
              >
                {/* 扩大拖动区域 */}
                <div 
                  className="absolute -left-4 -right-4 -top-4 -bottom-4 cursor-grab"
                  onMouseDown={(e) => {
                    // 阻止事件冒泡
                    e.stopPropagation();
                    
                    // 设置指示器为活动状态的样式
                    const handle = e.currentTarget.parentNode as HTMLDivElement;
                    handle.classList.add('scale-110');
                    handle.classList.add('cursor-grabbing');
                    handle.classList.remove('cursor-grab');
                    
                    // 监听鼠标移动和释放事件
                    const handleMouseMove = (moveEvent: MouseEvent) => {
                      const slider = handle.parentNode as HTMLDivElement;
                      const rect = slider.getBoundingClientRect();
                      const offsetX = moveEvent.clientX - rect.left;
                      const width = rect.width;
                      const percentage = Math.max(0, Math.min(1, offsetX / width));
                      
                      // 计算新的maxDuration值
                      const newValue = Math.max(minDuration + 1, Math.min(20, Math.round(percentage * 19) + 1));
                      if (newValue !== maxDuration) {
                        setMaxDuration(newValue);
                      }
                    };
                    
                    const handleMouseUp = () => {
                      // 移除活动状态样式
                      handle.classList.remove('cursor-grabbing');
                      handle.classList.add('cursor-grab');
                      
                      // 移除事件监听器
                      window.removeEventListener('mousemove', handleMouseMove);
                      window.removeEventListener('mouseup', handleMouseUp);
                    };
                    
                    window.addEventListener('mousemove', handleMouseMove);
                    window.addEventListener('mouseup', handleMouseUp);
                  }}
                ></div>
              </div>
              
              {/* 刻度标记 */}
              <div className="absolute left-2 right-2 bottom-0 flex justify-between">
                <span className="text-[10px] text-gray-400">1s</span>
                <span className="text-[10px] text-gray-400">20s</span>
              </div>
            </div>
          </div>
          
          {/* 4. 分段信息 */}
          <div className="flex-shrink-0 ml-auto">
            <p className="text-sm text-gray-600 whitespace-nowrap">
              共 {segments.length} 个分段，显示 {filteredSegments.length} 个
            </p>
          </div>
        </div>
        
        {/* 标签导航 - 移动到过滤选项下方 */}
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
              {filteredSegments.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-4 text-center text-gray-500">
                    {activeTab === 'all' ? '全部片段已被处理或没有匹配的内容' :
                     activeTab === 'selected' ? '没有已选择的片段' :
                     '没有已剔除的片段'}
                  </td>
                </tr>
              ) : (
                filteredSegments.map(segment => (
                  <tr 
                    key={segment.id}
                    className={
                      selectedSegments.some(s => s.id === segment.id) 
                        ? 'bg-primary-50' 
                        : rejectedSegments.some(s => s.id === segment.id)
                          ? 'bg-red-50'
                          : undefined
                    }
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex space-x-2">
                        {/* 选择按钮 */}
                        <button
                          type="button"
                          onClick={() => handleSelectSegment(segment)}
                          className={`text-gray-400 hover:text-primary-600 ${
                            rejectedSegments.some(s => s.id === segment.id) ? 'opacity-50' : ''
                          }`}
                          title="选择"
                        >
                          {selectedSegments.some(s => s.id === segment.id) ? (
                            <FiCheckCircle className="w-5 h-5 text-primary-600" />
                          ) : (
                            <FiCircle className="w-5 h-5" />
                          )}
                        </button>
                        
                        {/* 剔除按钮 */}
                        <button
                          type="button"
                          onClick={() => handleRejectSegment(segment)}
                          className={`text-gray-400 hover:text-red-600 ${
                            selectedSegments.some(s => s.id === segment.id) ? 'opacity-50' : ''
                          }`}
                          title="剔除"
                        >
                          {rejectedSegments.some(s => s.id === segment.id) ? (
                            <FiXCircle className="w-5 h-5 text-red-600" />
                          ) : (
                            <FiXCircle className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatTime(segment.start)} - {formatTime(segment.end)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatTime(segment.end - segment.start)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
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