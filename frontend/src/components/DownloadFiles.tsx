'use client';

import { useState } from 'react';
import { FiDownload, FiCircle, FiCheckCircle, FiFile, FiTrash2, FiPackage } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import apiService, {OutputFile, Segment} from '@/lib/api';

export function DownloadFiles() {
  // 使用应用状态
  const { 
    currentTask, 
    outputFiles,
    setCurrentStep,
    resetState,
    selectOutputFile,
    unselectOutputFile,
    selectedOutputFiles,
    clearSelectedOutputfiles
  } = useAppStore();
  
  // 本地状态
  const [cleaningUp, setCleaningUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectAll, setSelectAll] = useState(false);

  // 没有任务或输出文件则显示错误
  if (!currentTask || outputFiles.length === 0) {
    return (
      <div className="card">
        <div className="card-body">
          <p className="text-red-600">请先完成音频分割</p>
          <button
            type="button"
            onClick={() => setCurrentStep(1)}
            className="mt-4 btn-secondary"
          >
            返回上传页面
          </button>
        </div>
      </div>
    );
  }
  
  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // 清理文件名中的特殊字符
  const sanitizeFileName = (fileName: string) => {
    // 替换不允许在文件名中的字符
    return fileName.replace(/[<>:"\/\\|?*]/g, '_');
  };

  // 处理单个文件下载
  const handleDownload = (url: string, fileName: string) => {
    const cleanFileName = sanitizeFileName(fileName);
    const link = document.createElement('a');
    link.href = url;
    link.download = cleanFileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 处理全部文件下载
  const handleDownloadAll = () => {
    // 为避免浏览器阻止多个下载，间隔下载文件
    // outputFiles.forEach((file, index) => {
    selectedOutputFiles.forEach((file, index) => {
      setTimeout(() => {
        handleDownload(file.download_url, file.name);
      }, index * 800); // 每800毫秒下载一个文件
    });
  };

  // 处理清理资源
  const handleCleanup = async () => {
    if (!currentTask) return;
    
    try {
      setCleaningUp(true);
      setError(null);
      
      // 调用清理API
      await apiService.cleanupTask(currentTask.id);
      
      // 重置状态
      resetState();
      
      // 返回第一步
      setCurrentStep(1);
      
    } catch (error) {
      console.error('清理失败:', error);
      setError('清理资源失败，请重试。');
    } finally {
      setCleaningUp(false);
    }
  };

  // 处理单个选择
  const handleSelect = (file: OutputFile) => {
    // console.log("selectedOutputFiles size1 is ", selectedOutputFiles.length)
    // console.log("file", file);
    if (selectedOutputFiles.some(s => s.id === file.id)) {
      // console.log("file", file);
      unselectOutputFile(file.id);
      // console.log("after un selectedOutputFiles size is ", selectedOutputFiles.length)
      // selectedOutputFiles.forEach(f => {console.log(f.name)});
    } else {
      // console.log("file", file);
      selectOutputFile(file);
      // console.log("after handleSelect selectedOutputFiles size is ", selectedOutputFiles.length)
      // selectedOutputFiles.forEach(f => {console.log(f.name)});
    }
  };

  // 处理全选/全不选
  const handleSelectAll = () => {
    if (!selectAll) {
      // 取消全选
      clearSelectedOutputfiles();
    } else {
      // 全选
      console.log("handleSelectAll selectedOutputFiles size is ", selectedOutputFiles.length)
      outputFiles.forEach(file => {
        if (!selectedOutputFiles.some(s => s.id === file.id)) {
          console.log("selectAll ", file)
          selectOutputFile(file);
        }
      });
      console.log("selectAll selectedOutputFiles.length is", selectedOutputFiles.length);
      // selectedOutputFiles.forEach(file => {
      //   selectOutputFile(file);
      // });
    }
    setSelectAll(!selectAll);
  };
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-xl font-medium">下载分割文件</h2>
      </div>
      
      <div className="card-body space-y-6">
        <div className="flex justify-between items-center mb-4">
          <p className="text-sm text-gray-600">
            音频分割完成，共生成 {outputFiles.length} 个文件
          </p>
          <button
            onClick={handleDownloadAll}
            className="btn-primary flex items-center text-sm"
          >
            <FiPackage className="mr-1" />
            一键全部下载
          </button>
        </div>

        <p>
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
        </p>
        
        <ul className="divide-y divide-gray-200">
          {outputFiles.map((file) => (
            <li key={file.id} className="py-4 flex justify-between items-center">
              <div className="flex items-center">
                <button
                    type="button"
                    onClick={() => handleSelect(file)}
                    className="text-gray-400 hover:text-primary-600"
                >
                  {selectedOutputFiles.some(s => s.id === file.id) ? (
                      <FiCheckCircle className="w-5 h-5 text-primary-600" />
                  ) : (
                      <FiCircle className="w-5 h-5" />
                  )}
                </button>
                <FiFile className="w-6 h-6 text-primary-500 mr-3" />
                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-gray-500">{file.size_formatted}</p>
                </div>
              </div>
              
              <button
                onClick={() => handleDownload(file.download_url, file.name)}
                className="btn-secondary flex items-center text-sm"
              >
                <FiDownload className="mr-1" />
                下载
              </button>
            </li>
          ))}
        </ul>
        
        {error && (
          <div className="p-3 bg-red-50 text-red-700 rounded">
            {error}
          </div>
        )}
        
        <div className="flex justify-between mt-6">
          <button
            type="button"
            onClick={() => setCurrentStep(3)}
            className="btn-secondary"
          >
            返回
          </button>
          
          <button
            type="button"
            onClick={handleCleanup}
            disabled={cleaningUp}
            className={`btn-danger flex items-center ${cleaningUp ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {cleaningUp ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                清理中...
              </>
            ) : (
              <>
                <FiTrash2 className="mr-2" />
                完成并清理
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}