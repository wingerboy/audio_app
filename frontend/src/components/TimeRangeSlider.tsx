import React, { useState, useEffect } from 'react';
import { Segment } from '@/lib/api';
import { formatTime } from '@/lib/utils';

interface TimeRangeSliderProps {
  audioDuration: number; // 音频总时长（秒）
  segments: Segment[]; // 所有分段
  onSelectionChange: (selectedSegments: Segment[]) => void; // 选择变更回调
}

export function TimeRangeSlider({ audioDuration, segments, onSelectionChange }: TimeRangeSliderProps) {
  const [rangeStart, setRangeStart] = useState(0);
  const [rangeEnd, setRangeEnd] = useState(audioDuration);
  
  // 当音频时长改变时，重置结束位置
  useEffect(() => {
    setRangeEnd(audioDuration);
  }, [audioDuration]);
  
  // 当滑块停止移动时更新选中的分段
  const updateSelection = () => {
    if (!segments || segments.length === 0) return;
    
    const selectedSegments = segments.filter(segment => {
      // 只要分段的开始时间在选定范围内，就选中该分段
      return segment.start >= rangeStart && segment.start <= rangeEnd;
    });
    
    if (selectedSegments.length > 0) {
      onSelectionChange(selectedSegments);
    }
  };
  
  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newStart = Number(e.target.value);
    setRangeStart(Math.min(newStart, rangeEnd - 0.1));
  };
  
  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEnd = Number(e.target.value);
    setRangeEnd(Math.max(newEnd, rangeStart + 0.1));
  };
  
  return (
    <div className="flex items-center space-x-2">
      <span className="text-xs font-mono whitespace-nowrap">{formatTime(rangeStart)}</span>
      <div className="relative h-6 w-32 flex-shrink-0">
        <div className="absolute inset-0 flex items-center">
          <div className="h-1 w-full bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div 
            className="absolute h-1 bg-primary-500 rounded"
            style={{
              left: `${(rangeStart / audioDuration) * 100}%`,
              width: `${((rangeEnd - rangeStart) / audioDuration) * 100}%`
            }}
          ></div>
        </div>
        <input
          type="range"
          min={0}
          max={audioDuration}
          step={0.1}
          value={rangeStart}
          onChange={handleStartChange}
          onMouseUp={updateSelection}
          onTouchEnd={updateSelection}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
        />
        <div 
          className="absolute w-3 h-3 bg-primary-600 rounded-full border border-white"
          style={{ left: `calc(${(rangeStart / audioDuration) * 100}% - 2px)`, top: '50%', transform: 'translateY(-50%)' }}
        ></div>
      </div>
      <div className="relative h-6 w-32 flex-shrink-0">
        <div className="absolute inset-0 flex items-center">
          <div className="h-1 w-full bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
        <input
          type="range"
          min={0}
          max={audioDuration}
          step={0.1}
          value={rangeEnd}
          onChange={handleEndChange}
          onMouseUp={updateSelection}
          onTouchEnd={updateSelection}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
        />
        <div 
          className="absolute w-3 h-3 bg-primary-600 rounded-full border border-white"
          style={{ left: `calc(${(rangeEnd / audioDuration) * 100}% - 2px)`, top: '50%', transform: 'translateY(-50%)' }}
        ></div>
      </div>
      <span className="text-xs font-mono whitespace-nowrap">{formatTime(rangeEnd)}</span>
      <button
        onClick={updateSelection}
        className="text-xs bg-primary-100 text-primary-700 hover:bg-primary-200 px-2 py-1 rounded"
      >
        选择
      </button>
    </div>
  );
} 