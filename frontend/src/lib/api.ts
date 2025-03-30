import axios from 'axios';

// 获取API基础URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5002/api';

// 创建API客户端
const api = axios.create({
  baseURL: API_BASE_URL, // 使用环境变量中的API地址
  headers: {
    'Content-Type': 'application/json',
  },
});

// 配置请求拦截器，自动添加认证令牌
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 定义API返回的类型
export interface SystemStatus {
  status: string;
  components: {
    ffmpeg: boolean;
    // whisper: boolean; // 不再需要检测Whisper
    // gpu: boolean;     // 不再需要检测GPU
  };
  // torch_version: string; // 不再需要Torch版本
  // gpu_info: string;      // 不再需要GPU信息
}

export interface UploadResponse {
  task_id: string;
  filename: string;
  size_mb: number;
}

export interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
}

export interface AnalyzeResponse {
  task_id: string;
  status: string;
  message: string;
  segments: Segment[];
  text: string;
}

export interface OutputFile {
  id: number;
  name: string;
  path: string;
  size: number;
  size_formatted: string;
  download_url: string;
}

export interface SplitResponse {
  task_id: string;
  status: string;
  message: string;
  files: OutputFile[];
}

export interface TaskStatus {
  id: string;
  filename: string;
  size_mb: number;
  status: string;
  progress: number;
  message: string;
  created_at: number;
  segments_count?: number;
  files_info?: OutputFile[];
  user_id?: string;
}

// 用户相关类型
export interface User {
  id: string;
  username: string;
  email: string;
  created_at: number;
  last_login: number | null;
  balance: number;
  total_charged: number;
  total_consumed: number;
}

export interface AuthResponse {
  status: string;
  message: string;
  user?: User;
  token?: string;
}

// 模型定价信息接口
export interface ModelPricing {
  estimated_cost: number;
  details: {
    base_fee: number;
    duration_fee: number;
    file_size_fee: number;
    file_size_mb: number;
    audio_duration_minutes: number;
    model_size: string;
  };
}

// 成本估算接口
export interface CostEstimation {
  user_id: string;
  file_size_mb: number;
  model_size: string;
  audio_duration_minutes: number;
  estimated_cost: number;
  details: {
    base_fee: number;
    duration_fee: number;
    file_size_fee: number;
    file_size_mb: number;
    audio_duration_minutes: number;
    model_size: string;
  };
  task_id?: string;
}

// 余额检查结果接口
export interface BalanceCheckResult {
  is_sufficient: boolean;
  current_balance: number;
  estimated_cost: number;
  details: {
    base_fee: number;
    duration_fee: number;
    file_size_fee: number;
    file_size_mb: number;
    audio_duration_minutes: number;
    model_size: string;
  };
  task_id?: string;
}

// 获取所有模型的定价信息
async function getModelsPricing(fileSizeMb: number, audioDurationMinutes?: number): Promise<Record<string, ModelPricing>> {
  // 构建查询参数
  const params = new URLSearchParams();
  params.append('file_size_mb', fileSizeMb.toString());
  
  // 如果提供了音频时长，添加到参数中
  if (audioDurationMinutes !== undefined) {
    params.append('audio_duration_minutes', audioDurationMinutes.toString());
  }
  
  const response = await api.get(`/pricing/models?${params.toString()}`);
  return response.data;
}

// 获取特定模型的定价估算
async function estimateCost(options: {taskId?: string, fileSizeMb?: number, modelSize: string, audioDurationMinutes?: number}): Promise<CostEstimation> {
  const { taskId, fileSizeMb, modelSize, audioDurationMinutes } = options;
  
  // 必须提供taskId或fileSizeMb
  if (!taskId && fileSizeMb === undefined) {
    throw new Error('必须提供taskId或fileSizeMb');
  }
  
  const data: any = {
    model_size: modelSize
  };
  
  // 添加task_id
  if (taskId) {
    data.task_id = taskId;
  }
  
  // 添加file_size_mb
  if (fileSizeMb !== undefined) {
    data.file_size_mb = fileSizeMb;
  }
  
  // 如果提供了音频时长，添加到参数中
  if (audioDurationMinutes !== undefined) {
    data.audio_duration_minutes = audioDurationMinutes;
  }
  
  const response = await api.post('/pricing/estimate', data);
  return response.data;
}

// 检查用户余额是否足够进行音频分析
async function checkBalance(options: {taskId?: string, fileSizeMb?: number, modelSize: string, audioDurationMinutes?: number}): Promise<BalanceCheckResult> {
  const { taskId, fileSizeMb, modelSize, audioDurationMinutes } = options;
  
  // 必须提供taskId或fileSizeMb
  if (!taskId && fileSizeMb === undefined) {
    throw new Error('必须提供taskId或fileSizeMb');
  }
  
  const data: any = {
    model_size: modelSize
  };
  
  // 添加task_id
  if (taskId) {
    data.task_id = taskId;
  }
  
  // 添加file_size_mb
  if (fileSizeMb !== undefined) {
    data.file_size_mb = fileSizeMb;
  }
  
  // 如果提供了音频时长，添加到参数中
  if (audioDurationMinutes !== undefined) {
    data.audio_duration_minutes = audioDurationMinutes;
  }
  
  const response = await api.post('/balance/check_analyze', data);
  return response.data;
}

// API方法
export const apiService = {
  // 设置认证令牌
  setAuthToken: (token: string) => {
    localStorage.setItem('auth_token', token);
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  },
  
  // 清除认证令牌
  clearAuthToken: () => {
    localStorage.removeItem('auth_token');
    delete api.defaults.headers.common['Authorization'];
  },
  
  // 用户认证方法
  register: async (username: string, email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/register', {
      username,
      email,
      password
    });
    return response.data;
  },
  
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', {
      email,
      password
    });
    return response.data;
  },
  
  getCurrentUser: async (): Promise<User | null> => {
    try {
      const response = await api.get('/auth/me');
      return response.data.user;
    } catch (error) {
      console.error('获取当前用户信息失败', error);
      return null;
    }
  },
  
  updateUser: async (updateData: Partial<User>): Promise<AuthResponse> => {
    const response = await api.put('/auth/update', updateData);
    return response.data;
  },
  
  // 检查系统状态
  getStatus: async (): Promise<SystemStatus> => {
    const response = await api.get('/status');
    return response.data;
  },

  // 上传文件
  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        // 可以在这里实现进度回调
        console.log(`Upload progress: ${Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))}%`);
      },
    });
    
    return response.data;
  },

  // 分析音频内容
  analyzeAudio: async (taskId: string): Promise<AnalyzeResponse> => {
    const response = await api.post('/analyze', {
      task_id: taskId
    });
    return response.data;
  },

  // 分割音频
  splitAudio: async (
    taskId: string, 
    segments: Segment[], 
    outputFormat: string = 'mp3', 
    outputQuality: string = 'medium'
  ): Promise<SplitResponse> => {
    const response = await api.post('/split', {
      task_id: taskId,
      segments,
      output_format: outputFormat,
      output_quality: outputQuality,
    });
    return response.data;
  },

  // 获取任务状态
  getTaskStatus: async (taskId: string): Promise<TaskStatus> => {
    const response = await api.get(`/tasks/${taskId}`);
    return response.data;
  },

  // 获取下载URL
  getDownloadUrl: (taskId: string, fileIndex: number): string => {
    return `${api.defaults.baseURL}/download/${taskId}/${fileIndex}`;
  },

  // 清理任务资源
  cleanupTask: async (taskId: string): Promise<{ status: string; message: string }> => {
    const response = await api.delete(`/cleanup/${taskId}`);
    return response.data;
  },

  getModelsPricing,
  estimateCost,
  checkBalance,
};

export default apiService; 