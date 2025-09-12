/**
 * Studio前端环境配置
 * 统一管理API地址和其他配置项
 */
export const environment = {
  production: false,
  
  // API配置
  api: {
    // Web UI后端API地址
    baseUrl: 'http://localhost:8080',
    // 各模块API路径
    paths: {
      operators: '/api/operators',
      pipelines: '/api/pipelines', 
      jobs: '/api/jobs',
      info: '/api/info',
      health: '/health'
    }
  },

  // 开发配置
  dev: {
    enableMockData: true,  // 是否启用Mock数据
    enableDebugLogs: true, // 是否启用调试日志
  },

  // 超时配置
  timeout: {
    api: 30000,      // API调用超时时间（毫秒）
    upload: 120000   // 文件上传超时时间（毫秒）
  }
};
