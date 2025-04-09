'use client';

import { useCallback, useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiFile, FiCheckCircle, FiAlertCircle } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import apiService from '@/lib/api';
import { AxiosProgressEvent } from 'axios';

export function FileUploader() {
  // 使用全局状态
  const { 
    setCurrentTask, 
    setCurrentStep,
  } = useAppStore();
  
  // 本地状态
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [realProgress, setRealProgress] = useState(0);
  const [uploadStartTime, setUploadStartTime] = useState<number | null>(null);
  
  // 引用值，用于取消虚拟进度的定时器
  const virtualProgressTimer = useRef<NodeJS.Timeout | null>(null);
  const uploadPromise = useRef<Promise<any> | null>(null);
  
  // 清理函数
  const clearVirtualProgress = () => {
    if (virtualProgressTimer.current) {
      clearInterval(virtualProgressTimer.current);
      virtualProgressTimer.current = null;
    }
  };
  
  // 当组件卸载时清理定时器
  useEffect(() => {
    return () => clearVirtualProgress();
  }, []);
  
  // 启动虚拟进度更新
  const startVirtualProgress = (fileSizeMB: number) => {
    setUploadStartTime(Date.now());
    
    // 清除之前的定时器
    clearVirtualProgress();
    
    // 根据文件大小调整速度
    const totalTime = Math.max(2000, fileSizeMB * 100); // 文件越大，总时间越长
    const interval = Math.max(100, Math.min(500, fileSizeMB * 5)); // 更新间隔
    const incrementStep = 1; // 每次增加的百分比
    
    // 计算进度曲线：开始快，中间变慢，接近结束前略微加快
    virtualProgressTimer.current = setInterval(() => {
      setUploadProgress(prevProgress => {
        // 如果有真实进度并且真实进度大于虚拟进度，则使用真实进度
        if (realProgress > prevProgress) {
          return realProgress;
        }
        
        // 当进度接近 95% 时，放慢速度，等待真实上传完成
        if (prevProgress >= 95) {
          clearVirtualProgress(); // 停止虚拟进度更新
          return prevProgress;
        }
        
        // 进度在不同阶段有不同的速度
        let newIncrement = incrementStep;
        if (prevProgress < 30) {
          // 开始阶段快一些
          newIncrement = incrementStep * 1.5;
        } else if (prevProgress > 70) {
          // 接近结束前略微减速
          newIncrement = incrementStep * 0.7;
        }
        
        return Math.min(95, prevProgress + newIncrement);
      });
    }, interval);
  };
  
  // 处理真实上传进度
  const handleRealProgress = (event: AxiosProgressEvent) => {
    if (!event.total) return;
    const percent = Math.round((event.loaded * 100) / event.total);
    setRealProgress(percent);
    
    // 如果真实进度大于当前显示的进度，更新显示的进度
    if (percent > uploadProgress) {
      setUploadProgress(percent);
    }
  };
  
  // 完成上传
  const completeUpload = () => {
    // 上传完成，进度设置为100%
    setUploadProgress(100);
    clearVirtualProgress();
    
    // 计算上传用时
    if (uploadStartTime) {
      const uploadTime = (Date.now() - uploadStartTime) / 1000;
      console.log(`Upload completed in ${uploadTime.toFixed(2)} seconds`);
    }
  };
  
  // 处理文件上传
  const handleUpload = useCallback(async (file: File) => {
    try {
      setUploading(true);
      setUploadError(null);
      setUploadProgress(0);
      setRealProgress(0);
      
      // 启动虚拟进度显示
      const fileSizeMB = file.size / (1024 * 1024);
      startVirtualProgress(fileSizeMB);
      
      // 上传文件
      uploadPromise.current = apiService.uploadFile(file, handleRealProgress);
      const response = await uploadPromise.current;
      
      // 完成上传，设置进度为100%
      completeUpload();
      
      // 更新任务状态
      const taskStatus = await apiService.getTaskStatus(response.task_id);
      setCurrentTask(taskStatus);
      
      // 转到下一步
      setTimeout(() => {
        setCurrentStep(2);
      }, 1000);
      
    } catch (error) {
      console.error('文件上传失败:', error);
      setUploadError('文件上传失败，请重试。');
      clearVirtualProgress();
    } finally {
      setUploading(false);
      uploadPromise.current = null;
    }
  }, [setCurrentTask, setCurrentStep]);
  
  // 配置文件上传区域
  const { 
    getRootProps, 
    getInputProps, 
    isDragActive, 
    acceptedFiles,
    fileRejections
  } = useDropzone({
    accept: {
      'audio/*': ['.mp3', '.wav', '.ogg', '.flac', '.m4a'],
      'video/*': ['.mp4', '.avi', '.mkv', '.mov']
    },
    maxSize: 1024 * 1024 * 500, // 500MB
    maxFiles: 1,
    disabled: uploading,
    onDropAccepted: (files) => {
      if (files.length > 0) {
        handleUpload(files[0]);
      }
    }
  });
  
  // 获取选择的文件
  const file = acceptedFiles.length > 0 ? acceptedFiles[0] : null;
  
  // 格式化文件大小
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-xl font-medium text-gray-900 dark:text-white">上传文件</h2>
      </div>
      
      <div className="card-body">
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragActive 
              ? 'border-primary-400 bg-primary-50 dark:border-primary-500 dark:bg-primary-900/20' 
              : 'border-gray-300 dark:border-gray-600 hover:border-primary-300 dark:hover:border-primary-600'
          } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <input {...getInputProps()} />
          
          <div className="flex flex-col items-center justify-center space-y-4">
            {!file && !uploading && (
              <>
                <FiUpload className="w-12 h-12 text-gray-400 dark:text-gray-300" />
                <p className="text-lg text-gray-800 dark:text-gray-200">
                  拖放文件到此处，或<span className="text-primary-600 dark:text-primary-400 font-medium">点击选择文件</span>
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  支持的格式: MP3, WAV, OGG, FLAC, M4A, MP4, AVI, MKV, MOV (最大 500MB)
                </p>
              </>
            )}
            
            {file && !uploading && (
              <div className="flex items-center space-x-3">
                <FiFile className="w-8 h-8 text-primary-500 dark:text-primary-400" />
                <div className="text-left">
                  <p className="font-medium text-gray-800 dark:text-gray-200">{file.name}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{formatFileSize(file.size)}</p>
                </div>
                <FiCheckCircle className="w-6 h-6 text-green-500 dark:text-green-400" />
              </div>
            )}
            
            {uploading && (
              <div className="w-full max-w-md">
                <p className="mb-2 font-medium text-gray-800 dark:text-gray-200">正在上传...</p>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-primary-600 dark:bg-primary-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <div className="flex justify-between mt-1">
                  <p className="text-sm text-gray-600 dark:text-gray-400">{uploadProgress}%</p>
                  {uploadProgress < 100 && (
                    <p className="text-sm text-gray-500 dark:text-gray-500">处理中，请稍候...</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        
        {uploadError && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded flex items-center border border-red-200 dark:border-red-800">
            <FiAlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}
        
        {fileRejections.length > 0 && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded flex items-center border border-red-200 dark:border-red-800">
            <FiAlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
            <div>
              <p className="font-medium">文件无法上传：</p>
              <ul className="text-sm list-disc list-inside">
                {fileRejections.map(({ file, errors }) => (
                  <li key={file.name}>
                    {file.name} - {errors.map(e => e.message).join(', ')}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 