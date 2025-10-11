/**
 * Studio前端生产环境配置
 */
export const environment = {
  production: true,
  
  // API配置
  api: {
    // 生产环境Web UI后端API地址
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

  // 生产配置
  dev: {
    enableMockData: false,  // 生产环境不启用Mock数据
    enableDebugLogs: false, // 生产环境不启用调试日志
  },

  // 超时配置
  timeout: {
    api: 30000,      // API调用超时时间（毫秒）
    upload: 120000   // 文件上传超时时间（毫秒）
  }
};
