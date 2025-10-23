// Runtime configuration for local development
// This file will be overwritten during CI/CD deployment
window.SAGE_RUNTIME_CONFIG = window.SAGE_RUNTIME_CONFIG || {};

// For local development, token can be set here temporarily
// WARNING: Do not commit real tokens to git!
window.SAGE_RUNTIME_CONFIG.gistToken = '';

// For production, this will be replaced by GitHub Actions
console.log('📋 本地开发配置已加载，Token 需要手动配置或通过界面设置');
