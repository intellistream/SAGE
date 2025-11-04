/**
 * SAGE Studio API Client
 *
 * 与 Phase 1 后端 API 通信的服务层
 */

import axios from 'axios'

// API 基础 URL (由 Vite 代理到 localhost:8080)
const API_BASE_URL = '/api'

// Axios 实例
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// ==================== 类型定义 ====================

// 参数配置接口
export interface ParameterConfig {
    name: string
    label: string
    type: 'text' | 'textarea' | 'number' | 'select' | 'password'
    required?: boolean
    defaultValue?: any
    placeholder?: string
    description?: string
    options?: string[]
    min?: number
    max?: number
    step?: number
}

export interface NodeDefinition {
    id: number
    name: string
    description: string
    code: string
    isCustom: boolean
    parameters?: ParameterConfig[]  // 节点参数配置
}

export interface FlowConfig {
    name: string
    description?: string
    nodes: Array<{
        id: string
        type: string
        position: { x: number; y: number }
        data: any
    }>
    edges: Array<{
        id: string
        source: string
        target: string
        sourceHandle?: string
        targetHandle?: string
    }>
}

export interface Job {
    jobId: string
    name: string
    isRunning: boolean
    nthreads: string
    cpu: string
    ram: string
    startTime: string
    duration: string
    nevents: number
    minProcessTime: number
    maxProcessTime: number
    meanProcessTime: number
    latency: number
    throughput: number
    ncore: number
    periodicalThroughput: number[]
    periodicalLatency: number[]
    totalTimeBreakdown: {
        totalTime: number
        serializeTime: number
        persistTime: number
        streamProcessTime: number
        overheadTime: number
    }
    schedulerTimeBreakdown: {
        overheadTime: number
        streamTime: number
        totalTime: number
        txnTime: number
    }
    operators: Array<{
        id: number
        name: string
        numOfInstances: number
        downstream: number[]
        [key: string]: any
    }>
}

export interface JobStatus {
    job_id: string
    status: 'idle' | 'running' | 'stopped' | 'error'
    use_ray: boolean
    isRunning: boolean
}

export interface JobLogs {
    offset: number
    lines: string[]
}

// ==================== API 方法 ====================

/**
 * 健康检查
 */
export async function healthCheck(): Promise<{ status: string; service: string }> {
    const response = await apiClient.get('/health')
    return response.data
}

/**
 * 获取所有可用节点定义
 */
export async function getNodes(): Promise<NodeDefinition[]> {
    const response = await apiClient.get('/operators')
    return response.data
}

/**
 * 获取节点列表（分页）
 */
export async function getNodesList(
    page: number = 1,
    size: number = 10,
    search: string = ''
): Promise<{ items: NodeDefinition[]; total: number }> {
    const response = await apiClient.get('/operators/list', {
        params: { page, size, search },
    })
    return response.data
}

/**
 * 提交流程配置
 */
export async function submitFlow(flowConfig: FlowConfig): Promise<{
    status: string
    message: string
    pipeline_id: string
    file_path: string
}> {
    const response = await apiClient.post('/pipeline/submit', flowConfig)
    return response.data
}

/**
 * 获取所有作业
 */
export async function getAllJobs(): Promise<Job[]> {
    const response = await apiClient.get('/jobs/all')
    return response.data
}

/**
 * 获取作业详情
 */
export async function getJobDetail(jobId: string): Promise<Job> {
    const response = await apiClient.get(`/jobInfo/get/${jobId}`)
    return response.data
}

/**
 * 获取作业状态
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await apiClient.get(`/signal/status/${jobId}`)
    return response.data
}

/**
 * 启动作业
 */
export async function startJob(jobId: string): Promise<{
    status: string
    message: string
}> {
    const response = await apiClient.post(`/signal/start/${jobId}`)
    return response.data
}

/**
 * 停止作业
 */
export async function stopJob(
    jobId: string,
    duration: string = '00:00:00'
): Promise<{
    status: string
    message: string
}> {
    const response = await apiClient.post(`/signal/stop/${jobId}/${duration}`)
    return response.data
}

/**
 * 获取作业日志（增量）
 */
export async function getJobLogs(
    jobId: string,
    offset: number = 0
): Promise<JobLogs> {
    const response = await apiClient.get(`/signal/sink/${jobId}`, {
        params: { offset },
    })
    return response.data
}

/**
 * 获取管道配置
 */
export async function getPipelineConfig(pipelineId: string): Promise<{
    config: string
}> {
    const response = await apiClient.get(`/jobInfo/config/${pipelineId}`)
    return response.data
}

/**
 * 更新管道配置
 */
export async function updatePipelineConfig(
    pipelineId: string,
    config: string
): Promise<{
    status: string
    message: string
    file_path: string
}> {
    const response = await apiClient.put(`/jobInfo/config/update/${pipelineId}`, {
        config,
    })
    return response.data
}

/**
 * Playground 执行接口
 */
export async function executePlayground(params: {
    flowId: string
    input: string
    sessionId: string
    stream?: boolean
}): Promise<{
    output: string
    status: string
    agentSteps?: Array<{
        step: number
        type: 'reasoning' | 'tool_call' | 'response'
        content: string
        timestamp: string
        duration?: number
        toolName?: string
        toolInput?: any
        toolOutput?: any
    }>
}> {
    const response = await apiClient.post('/playground/execute', params)
    return response.data
}

// ==================== 节点输出 ====================

/**
 * 获取节点的输出数据
 */
export async function getNodeOutput(flowId: string, nodeId: string): Promise<{
    data: any
    type: 'json' | 'text' | 'error'
    timestamp: string
}> {
    const response = await apiClient.get(`/node/${flowId}/${nodeId}/output`)
    return response.data
}

// ==================== Flow 导入/导出 ====================

/**
 * 导出 Flow 为 JSON
 */
export async function exportFlow(flowId: string): Promise<Blob> {
    const response = await apiClient.get(`/flows/${flowId}/export`, {
        responseType: 'blob',
    })
    return response.data
}

/**
 * 导入 Flow
 */
export async function importFlow(file: File): Promise<{ flowId: string; name: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await apiClient.post('/flows/import', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    })
    return response.data
}

// ==================== 环境变量 ====================

/**
 * 获取所有环境变量
 */
export async function getEnvVars(): Promise<Record<string, string>> {
    const response = await apiClient.get('/env')
    return response.data
}

/**
 * 更新环境变量
 */
export async function updateEnvVars(vars: Record<string, string>): Promise<void> {
    await apiClient.put('/env', vars)
}

// ==================== 日志 ====================

/**
 * 获取流程执行日志（增量获取）
 */
export async function getLogs(flowId: string, lastId: number = 0): Promise<{
    logs: Array<{
        id: number
        timestamp: string
        level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG'
        message: string
        nodeId?: string
    }>
    last_id: number
}> {
    const response = await apiClient.get(`/logs/${flowId}`, {
        params: { last_id: lastId }
    })
    return response.data
}

// ==================== 错误处理 ====================

// 添加响应拦截器处理错误
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response) {
            // 服务器返回错误状态码
            console.error('API Error:', error.response.data)
            throw new Error(error.response.data.detail || '请求失败')
        } else if (error.request) {
            // 请求已发送但没有收到响应
            console.error('Network Error:', error.request)
            throw new Error('网络错误：无法连接到服务器')
        } else {
            // 其他错误
            console.error('Error:', error.message)
            throw error
        }
    }
)

export default apiClient
