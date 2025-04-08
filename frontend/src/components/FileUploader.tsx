'use client';

import { useCallback, useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiFile, FiCheckCircle, FiAlertCircle } from 'react-icons/fi';
import { useAppStore } from '@/lib/store';
import apiService from '@/lib/api';

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
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // 开始模拟进度更新
  const startFakeProgress = useCallback(() => {
    // 清除可能存在的旧计时器
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }
    
    setUploadProgress(0);
    
    // 创建新的进度更新计时器
    progressIntervalRef.current = setInterval(() => {
      setUploadProgress((prevProgress) => {
        // 模拟非线性进度，开始快，接近100%时变慢
        if (prevProgress >= 95) {
          // 在95%以上时，进度变化很小
          return prevProgress + (Math.random() * 0.3);
        } else if (prevProgress >= 80) {
          // 80%-95%之间，进度变化较小
          return prevProgress + (Math.random() * 0.7);
        } else if (prevProgress >= 60) {
          // 60%-80%之间，正常速度
          return prevProgress + (Math.random() * 1.5);
        } else {
          // 0-60%之间，快速增长
          return prevProgress + (Math.random() * 3);
        }
      });
    }, 200);
  }, []);
  
  // 结束模拟进度更新
  const stopFakeProgress = useCallback((success: boolean) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    
    // 如果成功，直接设置为100%，否则保持当前进度
    if (success) {
      setUploadProgress(100);
    }
  }, []);
  
  // 清理定时器
  useEffect(() => {
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);
  
  // 处理文件上传
  const handleUpload = useCallback(async (file: File) => {
    try {
      setUploading(true);
      setUploadError(null);
      
      // 开始模拟进度
      startFakeProgress();
      
      // 上传文件
      const response = await apiService.uploadFile(file);
      
      // 完成进度
      stopFakeProgress(true);
      
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
      stopFakeProgress(false);
    } finally {
      setUploading(false);
    }
  }, [setCurrentTask, setCurrentStep, startFakeProgress, stopFakeProgress]);
  
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
                <p className="mb-2 font-medium text-gray-800 dark:text-gray-200">
                  正在上传 {file?.name}...
                </p>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-primary-600 dark:bg-primary-500 h-2.5 rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${Math.min(uploadProgress, 100)}%` }}
                  ></div>
                </div>
                <div className="mt-2 flex justify-between items-center text-sm text-gray-600 dark:text-gray-400">
                  <span>{Math.min(Math.round(uploadProgress), 100)}%</span>
                  <span>{formatFileSize(file?.size || 0)}</span>
                </div>
                <p className="mt-3 text-xs text-gray-500 dark:text-gray-500">
                  {uploadProgress < 30 ? "准备文件..." : 
                   uploadProgress < 60 ? "上传中..." : 
                   uploadProgress < 90 ? "处理文件..." : "即将完成..."}
                </p>
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