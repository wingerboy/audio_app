import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { 
  Segment, 
  TaskStatus, 
  OutputFile, 
  SystemStatus,
  User
} from './api';
import { apiService } from './api';

// 用户类型定义
export interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  user: User | null;
}

// 添加模型定价信息类型
interface PricingDetail {
  base_price: number;
  file_size_cost: number;
  duration_cost: number;
  file_size_mb: number;
  estimated_minutes: number;
  model_size: string;
  api_type: string;
}

interface PricingInfo {
  estimated_cost: number;
  details: PricingDetail;
}

interface ModelsPricing {
  [key: string]: PricingInfo;
}

// 应用状态类型定义
export interface AppState {
  // 认证状态
  auth: AuthState;
  isAuthInitialized: boolean;
  
  // 系统状态
  systemStatus: SystemStatus | null;
  setSystemStatus: (status: SystemStatus) => void;
  
  // 当前任务
  currentTask: TaskStatus | null;
  setCurrentTask: (task: TaskStatus | null) => void;
  
  // 分析结果
  segments: Segment[];
  setSegments: (segments: Segment[]) => void;
  
  // 用户选择的段落
  selectedSegments: Segment[];
  selectSegment: (segment: Segment) => void;
  unselectSegment: (segmentId: number) => void;
  clearSelectedSegments: () => void;
  
  // 输出文件
  outputFiles: OutputFile[];
  selectedOutputFiles: OutputFile[];
  selectOutputFile: (file: OutputFile) => void;
  unselectOutputFile: (fileId: number) => void;
  clearSelectedOutputFiles: () => void;
  setOutputFiles: (files: OutputFile[]) => void;
  
  // 设置
  settings: {
    modelSize: string;
    outputFormat: string;
    outputQuality: string;
    minSegment: number;
    maxSegment: number;
    preserveSentences: boolean;
  };
  updateSettings: (settings: Partial<AppState['settings']>) => void;
  
  // UI状态
  uiState: {
    currentStep: number;
    isAnalyzing: boolean;
    isSplitting: boolean;
    showAdvanced: boolean;
  };
  setCurrentStep: (step: number) => void;
  setIsAnalyzing: (isAnalyzing: boolean) => void;
  setIsSplitting: (isSplitting: boolean) => void;
  toggleShowAdvanced: () => void;
  
  // 重置状态
  resetState: () => void;
  
  // 处理进度状态
  taskProgress: {
    isProcessing: boolean;
    progress: number;
  };
  setProcessingStatus: (status: boolean) => void;
  updateProgress: (progress: number) => void;
  
  // 认证相关方法
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUserInfo: (user: User) => void;
  setAuthInitialized: (value: boolean) => void;
  
  // 定价相关
  modelsPricing: ModelsPricing | null;
  setModelsPricing: (pricing: ModelsPricing | null) => void;
  
  // 开发测试用：设置当前用户为管理员
  setCurrentUserAsAdmin: () => void;
}

// 创建状态存储
export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // 认证状态初始化
      auth: {
        isAuthenticated: false,
        token: null,
        user: null,
      },
      isAuthInitialized: false,
      
      // 系统状态
      systemStatus: null,
      setSystemStatus: (status) => set({ systemStatus: status }),
      
      // 当前任务
      currentTask: null,
      setCurrentTask: (task) => set({ currentTask: task }),
      
      // 分析结果
      segments: [],
      setSegments: (segments) => set({ segments }),
      
      // 用户选择的段落
      selectedSegments: [],
      selectSegment: (segment) => set((state) => ({ 
        selectedSegments: [...state.selectedSegments, segment] 
      })),
      unselectSegment: (segmentId) => set((state) => ({ 
        selectedSegments: state.selectedSegments.filter((s) => s.id !== segmentId) 
      })),
      clearSelectedSegments: () => set({ selectedSegments: [] }),
      
      // 输出文件
      outputFiles: [],
      setOutputFiles: (files) => set({ outputFiles: files }),
      selectedOutputFiles: [],
      selectOutputFile: (file) => set((state) => ({
        selectedOutputFiles: [...state.selectedOutputFiles, file]
      })),
      unselectOutputFile: (fileId) => set((state) => ({
        selectedOutputFiles: state.selectedOutputFiles.filter(f => f.id !== fileId)
      })),
      clearSelectedOutputFiles: () => set({ selectedOutputFiles: [] }),
      
      // 设置
      settings: {
        modelSize: 'base',
        outputFormat: 'mp3',
        outputQuality: 'medium',
        minSegment: 5,
        maxSegment: 60,
        preserveSentences: true,
      },
      updateSettings: (settings) => set((state) => ({ 
        settings: { ...state.settings, ...settings } 
      })),
      
      // UI状态
      uiState: {
        currentStep: 1,
        isAnalyzing: false,
        isSplitting: false,
        showAdvanced: false,
      },
      setCurrentStep: (step) => set((state) => ({ 
        uiState: { ...state.uiState, currentStep: step } 
      })),
      setIsAnalyzing: (isAnalyzing) => set((state) => ({ 
        uiState: { ...state.uiState, isAnalyzing } 
      })),
      setIsSplitting: (isSplitting) => set((state) => ({ 
        uiState: { ...state.uiState, isSplitting } 
      })),
      toggleShowAdvanced: () => set((state) => ({ 
        uiState: { ...state.uiState, showAdvanced: !state.uiState.showAdvanced } 
      })),
      
      // 重置状态
      resetState: () => set((state) => ({
        currentTask: null,
        segments: [],
        selectedSegments: [],
        outputFiles: [],
        selectedOutputFiles: [],
        uiState: {
          ...state.uiState,
          currentStep: 1,
          isAnalyzing: false,
          isSplitting: false,
        }
      })),
      
      // 处理进度状态
      taskProgress: {
        isProcessing: false,
        progress: 0,
      },
      
      // 认证相关方法
      login: (token, user) => {
        // 保存token到localStorage
        localStorage.setItem('auth_token', token);
        
        // 更新状态
        set({
          auth: {
            isAuthenticated: true,
            token,
            user,
          },
        });
        
        // 设置API请求头中的token
        apiService.setAuthToken(token);
      },
      
      logout: () => {
        // 从localStorage中移除token
        localStorage.removeItem('auth_token');
        
        // 更新状态
        set({
          auth: {
            isAuthenticated: false,
            token: null,
            user: null,
          },
        });
        
        // 清除API请求头中的token
        apiService.clearAuthToken();
      },
      
      updateUserInfo: (user) => {
        set((state) => ({
          auth: {
            ...state.auth,
            user,
          },
        }));
      },
      
      // 开发测试用：设置当前用户为管理员
      setCurrentUserAsAdmin: () => {
        set((state) => {
          if (state.auth.user) {
            return {
              auth: {
                ...state.auth,
                user: {
                  ...state.auth.user,
                  is_admin: true
                }
              }
            };
          }
          return state;
        });
      },
      
      setAuthInitialized: (value) => {
        set({ isAuthInitialized: value });
      },
      
      // 进度相关方法
      setProcessingStatus: (status) => {
        set((state) => ({
          taskProgress: { ...state.taskProgress, isProcessing: status },
        }));
      },
      
      updateProgress: (progress) => {
        set((state) => ({
          taskProgress: { ...state.taskProgress, progress },
        }));
      },
      
      // 定价相关
      modelsPricing: null,
      setModelsPricing: (pricing) => set({ modelsPricing: pricing }),
    }),
    {
      name: 'audio-splitter-storage',
      partialize: (state) => ({
        settings: state.settings,
        auth: state.auth, // 持久化认证信息
      }),
    }
  )
);