import axios from 'axios';
import { AxiosProgressEvent } from 'axios';

// 获取API基础URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5002/api';
// const API_BASE_URL = 'http://117.50.172.107:5002/api';
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
    try {
      // 首先尝试从localStorage获取token
      const token = localStorage.getItem('auth_token');
      
      // 如果localStorage中有token，使用它
      if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      } 
      // 如果localStorage中没有token，尝试从zustand store获取
      else {
        // 这里我们需要动态导入，因为在拦截器初始化时store可能还未创建
        const authState = require('./store').useAppStore.getState().auth;
        if (authState && authState.token) {
          config.headers['Authorization'] = `Bearer ${authState.token}`;
        }
      }
    } catch (error) {
      console.error('设置认证头失败:', error);
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
  audio_duration_seconds: number;
  audio_duration_minutes: number;
  estimated_costs?: {
    analyze: number;
    split: number;
  };
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
  task_status?: TaskStatus;
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
  task_status?: TaskStatus;
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
  audio_duration_seconds?: number;
  audio_duration_minutes?: number;
  estimated_cost?: number;
}

// 用户相关类型
export interface User {
  id: string;
  username: string;
  email: string;
  is_admin: boolean; // 为了向后兼容保留
  role: number; // 新增：角色ID
  role_name: string; // 新增：角色名称
  balance: number;
  total_charged: number;
  total_consumed: number;
  created_at: string;
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

// 添加ApiResponse接口定义
export interface ApiResponse<T = any> {
  status: string;
  message: string;
  data?: T;
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
// 注意：当调用 analyzeAudio 时，服务器会自动检查余额，所以不再需要单独调用此函数
// 此函数保留用于需要提前获取费用预估的场景
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
  
  const response = await api.post('/api/balance/check_analyze', data);
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
  uploadFile: async (file: File, onProgress?: (event: AxiosProgressEvent) => void): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        // 实现进度回调
        if (onProgress) {
          onProgress(progressEvent);
        }
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
    
    // 由于我们需要及时获取最新的任务状态，我们在此处添加一个获取操作
    try {
      const taskStatus = await api.get(`/tasks/${taskId}`);
      // 将任务状态添加到响应中
      response.data.task_status = taskStatus.data;
    } catch (error) {
      console.warn('获取最新任务状态失败:', error);
    }
    
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
    
    // 由于我们需要及时获取最新的任务状态，我们在此处添加一个获取操作
    try {
      const taskStatus = await api.get(`/tasks/${taskId}`);
      // 将任务状态添加到响应中
      response.data.task_status = taskStatus.data;
    } catch (error) {
      console.warn('获取最新任务状态失败:', error);
    }
    
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

  // 管理员充值接口
  adminCharge: async (email: string, amount: number): Promise<any> => {
    const response = await api.post('/balance/admin/charge', {
      email: email,
      amount: amount
    });
    return response.data;
  },

  // 代理划扣接口 - 将点数从代理账户划扣到普通用户账户
  agentCharge: async (email: string, amount: number): Promise<ApiResponse<{
    agent_balance: number, 
    user_balance: number, 
    amount: number,
    actual_received?: number
  }>> => {
    const response = await api.post('/balance/agent/charge', {
      email: email,
      amount: amount
    });
    return response.data;
  },

  // 获取余额信息
  getBalanceInfo: async (): Promise<any> => {
    const response = await api.get('/balance/info');
    return response.data;
  },
  
  // 获取当前用户的最后一个任务
  getUserLastTask: async (): Promise<TaskStatus | null> => {
    try {
      const response = await api.get('/user/last-task');
      return response.data;
    } catch (error) {
      console.error('获取用户最后一个任务失败', error);
      return null;
    }
  },
  
  // 下载所有文件的ZIP压缩包
  downloadFilesAsZip: async (taskId: string): Promise<string> => {
    const response = await api.get(`/download/${taskId}/zip`, { responseType: 'blob' });
    const blob = new Blob([response.data], { type: 'application/zip' });
    return URL.createObjectURL(blob);
  },

  // 更新用户角色 - 仅限管理员操作
  updateUserRole: async (userId: string, role: number): Promise<ApiResponse<{user: User}>> => {
    const response = await api.post('/admin/update-role', {
      user_id: userId,
      role
    });
    return response.data;
  },

  // 获取特殊用户列表 - 仅限管理员操作
  getSpecialUsers: async (): Promise<ApiResponse<{users: User[]}>> => {
    const response = await api.get('/admin/special-users');
    return response.data;
  },

  // 通过邮箱查找用户 - 仅限管理员操作
  findUserByEmail: async (email: string): Promise<ApiResponse<{user: User}>> => {
    const response = await api.post('/admin/find-user', {
      email
    });
    return response.data;
  },
};

export default apiService; 