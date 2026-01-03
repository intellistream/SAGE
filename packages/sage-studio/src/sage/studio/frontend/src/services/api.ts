/**
 * SAGE Studio API Client
 *
 * 与 Phase 1 后端 API 通信的服务层
 */

import axios from 'axios'
import type { Node } from 'reactflow'

// API 基础 URL
// 开发模式: 使用 Vite 代理 /api -> localhost:8889
// 生产模式: 直接请求 Gateway（同域或通过环境变量配置）
const getApiBaseUrl = (): string => {
    // 如果有环境变量配置，优先使用
    if (import.meta.env.VITE_API_BASE_URL) {
        return import.meta.env.VITE_API_BASE_URL
    }
    // 生产模式下，假设 Gateway 与前端同域（通过反向代理）
    // 或者前端与 Gateway 在同一台机器上
    if (import.meta.env.PROD) {
        // 使用相对路径，依赖反向代理或同域部署
        // 如果前端和 Gateway 分离，需要配置 VITE_API_BASE_URL
        return '/api'
    }
    // 开发模式使用代理
    return '/api'
}

const API_BASE_URL = getApiBaseUrl()

// Helper function to get auth token for fetch requests
function getAuthToken(): string | null {
    try {
        const storage = localStorage.getItem('sage-auth-storage')
        if (storage) {
            const { state } = JSON.parse(storage)
            return state?.token || null
        }
    } catch (e) {
        // Ignore parsing errors
    }
    return null
}

// Helper function to get headers with auth token for fetch requests
function getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
    }
    const token = getAuthToken()
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }
    return headers
}

// Axios 实例
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 120000, // 120秒，适应 LLM 调用和 RAG 流程
    headers: {
        'Content-Type': 'application/json',
    },
})

// Auth Interceptor
apiClient.interceptors.request.use((config) => {
    const token = getAuthToken()
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            window.dispatchEvent(new CustomEvent('auth:unauthorized'))
        }
        return Promise.reject(error)
    }
)

// ==================== 类型定义 ====================

// Auth Types
export interface User {
    id: number
    username: string
    created_at: string
    is_guest?: boolean
}

export interface LoginCredentials {
    username: string
    password: string
}

export interface RegisterCredentials {
    username: string
    password: string
}

export interface TokenResponse {
    access_token: string
    token_type: string
}

// 参数配置接口
export interface ParameterConfig {
    name: string
    label: string
    type: 'text' | 'textarea' | 'number' | 'select' | 'password' | 'json'
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

// Auth API
export const login = async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const params = new URLSearchParams()
    params.append('username', credentials.username)
    params.append('password', credentials.password)
    const response = await apiClient.post<TokenResponse>('/auth/login', params, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
    return response.data
}

export const loginGuest = async (): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/guest')
    return response.data
}

export const logout = async (): Promise<void> => {
    await apiClient.post('/auth/logout')
}

export const register = async (credentials: RegisterCredentials): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', credentials)
    return response.data
}

export const getCurrentUser = async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
}

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

// ==================== Chat API (OpenAI-compatible) ====================

export interface ChatMessageDTO {
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: string
    metadata?: Record<string, any>
}

export interface ChatSessionSummary {
    id: string
    title: string
    created_at: string
    last_active: string
    message_count: number
}

export interface ChatSessionDetail extends ChatSessionSummary {
    messages: ChatMessageDTO[]
    metadata?: Record<string, any>
}

export interface PipelineRecommendation {
    success: boolean
    visual_pipeline: {
        name: string
        description: string
        nodes: Node[]
        connections: Array<{
            id: string
            source: string
            target: string
            type?: string
            animated?: boolean
        }>
    }
    raw_plan?: any
    message: string
    error?: string
}

// ==================== Multi-Agent SSE 类型定义 ====================

/**
 * Agent 步骤类型 (与 Task 5 文档对齐)
 */
export type AgentStepType = 'reasoning' | 'tool_call' | 'tool_result' | 'response'

/**
 * Agent 步骤状态
 */
export type AgentStepStatus = 'pending' | 'running' | 'completed' | 'failed'

/**
 * Agent 步骤数据结构 (Multi-Agent 架构核心类型)
 *
 * 用于表示 AgentOrchestrator 返回的每个推理/工具调用步骤
 */
export interface AgentStep {
    id: string
    type: AgentStepType
    content: string
    status: AgentStepStatus
    timestamp: number  // Unix timestamp (ms)
    metadata?: {
        tool_name?: string      // 工具名称 (type='tool_call' 时)
        tool_input?: unknown    // 工具输入参数
        tool_output?: unknown   // 工具输出结果 (type='tool_result' 时)
        confidence?: number     // 置信度 (0-1)
        duration_ms?: number    // 执行耗时 (ms)
        agent_name?: string     // 执行该步骤的 Agent 名称
        error_message?: string  // 错误信息
        [key: string]: unknown
    }
}

/**
 * SSE 事件类型枚举 (与后端 AgentOrchestrator 协议对齐)
 */
export type SSEEventType =
    | 'step'              // Agent 步骤事件
    | 'step_update'       // 步骤状态更新
    | 'step_content'      // 步骤内容追加（流式）
    | 'message'           // 最终消息内容块
    | 'reasoning_end'     // 推理阶段结束
    | 'error'             // 错误事件
    | 'done'              // 完成

/**
 * SSE 步骤事件 (新增 Agent 步骤)
 */
export interface SSEStepEvent {
    type: 'step'
    data: AgentStep
}

/**
 * SSE 步骤更新事件
 */
export interface SSEStepUpdateEvent {
    type: 'step_update'
    step_id: string
    updates: Partial<Pick<AgentStep, 'content' | 'status'> & {
        duration_ms?: number
    }>
}

/**
 * SSE 步骤内容追加事件 (流式内容)
 */
export interface SSEStepContentEvent {
    type: 'step_content'
    step_id: string
    content: string
}

/**
 * SSE 消息内容事件 (最终回复)
 */
export interface SSEMessageEvent {
    type: 'message'
    content: string
}

/**
 * SSE 错误事件
 */
export interface SSEErrorEvent {
    type: 'error'
    error: {
        code: string
        message: string
        details?: unknown
    }
}

/**
 * 所有 SSE 事件联合类型
 */
export type SSEEvent =
    | SSEStepEvent
    | SSEStepUpdateEvent
    | SSEStepContentEvent
    | SSEMessageEvent
    | SSEErrorEvent
    | { type: 'reasoning_end' }
    | { type: 'done' }

// ==================== 旧版推理步骤类型 (兼容) ====================

/**
 * 推理步骤事件类型 (旧版，保持向后兼容)
 */
export interface ReasoningStepEvent {
    type: 'reasoning_step'
    step: {
        id: string
        type: 'thinking' | 'retrieval' | 'workflow' | 'analysis' | 'conclusion' | 'tool_call'
        title: string
        content: string
        status: 'pending' | 'running' | 'completed' | 'error'
        timestamp: string
        duration?: number
        metadata?: Record<string, unknown>
    }
}

/**
 * 推理步骤更新事件 (旧版)
 */
export interface ReasoningStepUpdateEvent {
    type: 'reasoning_step_update'
    step_id: string
    updates: {
        content?: string
        status?: 'pending' | 'running' | 'completed' | 'error'
        duration?: number
    }
}

/**
 * 推理内容追加事件 (旧版)
 */
export interface ReasoningContentEvent {
    type: 'reasoning_content'
    step_id: string
    content: string
}

/**
 * 推理阶段结束事件 (旧版)
 */
export interface ReasoningEndEvent {
    type: 'reasoning_end'
}

// ==================== 回调接口定义 ====================

/**
 * 聊天消息回调集合 (旧版，保持兼容)
 */
export interface ChatMessageCallbacks {
    onChunk: (chunk: string) => void
    onError: (error: Error) => void
    onComplete: () => void
    onReasoningStep?: (step: ReasoningStepEvent['step']) => void
    onReasoningStepUpdate?: (stepId: string, updates: ReasoningStepUpdateEvent['updates']) => void
    onReasoningContent?: (stepId: string, content: string) => void
    onReasoningEnd?: () => void
}

/**
 * Multi-Agent 聊天回调集合 (新版，Task 5 规范)
 *
 * 用于处理 AgentOrchestrator 返回的流式事件
 */
export interface MultiAgentChatCallbacks {
    /** 收到新的 Agent 步骤 */
    onStep: (step: AgentStep) => void
    /** 步骤状态更新 */
    onStepUpdate?: (stepId: string, updates: SSEStepUpdateEvent['updates']) => void
    /** 步骤内容追加（流式） */
    onStepContent?: (stepId: string, content: string) => void
    /** 收到最终回复内容块 */
    onContent: (chunk: string) => void
    /** 推理阶段结束 */
    onReasoningEnd?: () => void
    /** 发生错误 */
    onError: (error: Error) => void
    /** 全部完成 */
    onComplete: () => void
}

/**
 * 发送聊天消息（SSE 流式响应）
 * 支持推理步骤事件 (兼容旧版回调)
 *
 * @param message - 用户消息内容
 * @param sessionId - 会话 ID
 * @param onChunk - 收到内容块的回调
 * @param onError - 错误回调
 * @param onComplete - 完成回调
 * @param callbacks - 可选的扩展回调（旧版推理步骤）
 */
export async function sendChatMessage(
    message: string,
    sessionId: string,
    onChunk: (chunk: string) => void,
    onError: (error: Error) => void,
    onComplete: () => void,
    callbacks?: Partial<ChatMessageCallbacks>,
    model?: string
): Promise<void> {
    try {
        const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                model: model,
                messages: [{ role: 'user', content: message }],
                session_id: sessionId,
                stream: true,
            }),
        })

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error('ReadableStream not supported')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
            const { done, value } = await reader.read()

            if (done) {
                onComplete()
                break
            }

            // 解码数据块
            buffer += decoder.decode(value, { stream: true })

            // 处理 SSE 数据
            const lines = buffer.split('\n')
            buffer = lines.pop() || '' // 保留不完整的行

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.substring(6).trim()

                    if (data === '[DONE]') {
                        onComplete()
                        return
                    }

                    try {
                        const parsed = JSON.parse(data)

                        // 处理推理步骤事件 (旧版)
                        if (parsed.type === 'reasoning_step' && callbacks?.onReasoningStep) {
                            callbacks.onReasoningStep(parsed.step)
                            continue
                        }

                        // 处理推理步骤更新事件 (旧版)
                        if (parsed.type === 'reasoning_step_update' && callbacks?.onReasoningStepUpdate) {
                            callbacks.onReasoningStepUpdate(parsed.step_id, parsed.updates)
                            continue
                        }

                        // 处理推理内容追加事件 (旧版)
                        if (parsed.type === 'reasoning_content' && callbacks?.onReasoningContent) {
                            callbacks.onReasoningContent(parsed.step_id, parsed.content)
                            continue
                        }

                        // 处理推理结束事件 (旧版)
                        if (parsed.type === 'reasoning_end' && callbacks?.onReasoningEnd) {
                            callbacks.onReasoningEnd()
                            continue
                        }

                        // 处理标准 OpenAI 格式的内容
                        const content = parsed.choices?.[0]?.delta?.content
                        if (content) {
                            onChunk(content)
                        }
                    } catch {
                        console.warn('Failed to parse SSE data:', data)
                    }
                }
            }
        }
    } catch (error) {
        onError(error instanceof Error ? error : new Error(String(error)))
    }
}

// ==================== Multi-Agent SSE 解析器 ====================

/**
 * SSE 行解析器
 * 支持带 event: 前缀的标准 SSE 格式和纯 data: 格式
 */
interface SSELineParseResult {
    eventType: string | null
    data: string | null
}

/**
 * 解析 SSE 行
 */
function parseSSELines(lines: string[]): SSELineParseResult[] {
    const results: SSELineParseResult[] = []
    let currentEvent: string | null = null
    let currentData: string[] = []

    for (const line of lines) {
        if (line.startsWith('event: ')) {
            // 新事件类型
            currentEvent = line.substring(7).trim()
        } else if (line.startsWith('data: ')) {
            // 数据行
            currentData.push(line.substring(6))
        } else if (line === '' && (currentEvent || currentData.length > 0)) {
            // 空行表示事件结束
            results.push({
                eventType: currentEvent,
                data: currentData.join('\n').trim() || null
            })
            currentEvent = null
            currentData = []
        }
    }

    // 处理可能的未完成事件（没有空行结尾）
    if (currentData.length > 0) {
        results.push({
            eventType: currentEvent,
            data: currentData.join('\n').trim() || null
        })
    }

    return results
}

/**
 * 发送聊天消息到 Multi-Agent 后端（SSE 流式响应）
 *
 * 支持 Task 5 规范的新 SSE 事件格式：
 * - event: step + data: AgentStep JSON
 * - event: step_update + data: {step_id, updates}
 * - event: step_content + data: {step_id, content}
 * - event: message + data: 内容块
 * - event: reasoning_end
 * - event: error + data: 错误信息
 * - data: [DONE]
 *
 * 同时兼容旧版纯 data: 格式
 *
 * @param message - 用户消息内容
 * @param sessionId - 会话 ID
 * @param callbacks - Multi-Agent 回调集合
 * @param options - 可选配置
 */
export async function sendChatMessageWithAgent(
    message: string,
    sessionId: string,
    callbacks: MultiAgentChatCallbacks,
    options?: {
        model?: string
        enableReasoning?: boolean
        systemPrompt?: string
    }
): Promise<void> {
    const { onStep, onStepUpdate, onStepContent, onContent, onReasoningEnd, onError, onComplete } = callbacks

    try {
        const response = await fetch(`${API_BASE_URL}/v1/chat/completions`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                model: options?.model,
                messages: [
                    ...(options?.systemPrompt ? [{ role: 'system', content: options.systemPrompt }] : []),
                    { role: 'user', content: message }
                ],
                session_id: sessionId,
                stream: true,
                // Multi-Agent 特定选项
                enable_reasoning: options?.enableReasoning ?? true,
            }),
        })

        if (!response.ok) {
            const errorText = await response.text()
            throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`)
        }

        const reader = response.body?.getReader()
        if (!reader) {
            throw new Error('ReadableStream not supported')
        }

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
            const { done, value } = await reader.read()

            if (done) {
                onComplete()
                break
            }

            // 解码数据块
            buffer += decoder.decode(value, { stream: true })

            // 按行分割
            const lines = buffer.split('\n')
            buffer = lines.pop() || '' // 保留最后一个可能不完整的行

            // 解析 SSE 事件
            const events = parseSSELines(lines)

            for (const { eventType, data } of events) {
                if (!data) continue

                // 检查完成标记
                if (data === '[DONE]') {
                    onComplete()
                    return
                }

                try {
                    // 根据事件类型处理
                    if (eventType === 'step' || (!eventType && data.includes('"type":"step"'))) {
                        // Agent 步骤事件
                        const parsed = JSON.parse(data)
                        const stepData = parsed.data || parsed
                        onStep(stepData as AgentStep)
                    } else if (eventType === 'step_update' || (!eventType && data.includes('"type":"step_update"'))) {
                        // 步骤更新事件
                        const parsed = JSON.parse(data)
                        if (onStepUpdate) {
                            onStepUpdate(parsed.step_id, parsed.updates)
                        }
                    } else if (eventType === 'step_content' || (!eventType && data.includes('"type":"step_content"'))) {
                        // 步骤内容追加
                        const parsed = JSON.parse(data)
                        if (onStepContent) {
                            onStepContent(parsed.step_id, parsed.content)
                        }
                    } else if (eventType === 'message' || (!eventType && data.includes('"type":"message"'))) {
                        // 最终消息内容
                        const parsed = JSON.parse(data)
                        onContent(parsed.content || parsed)
                    } else if (eventType === 'reasoning_end' || (!eventType && data.includes('"type":"reasoning_end"'))) {
                        // 推理结束
                        if (onReasoningEnd) {
                            onReasoningEnd()
                        }
                    } else if (eventType === 'error' || (!eventType && data.includes('"type":"error"'))) {
                        // 错误事件
                        const parsed = JSON.parse(data)
                        const errorInfo = parsed.error || parsed
                        throw new Error(errorInfo.message || JSON.stringify(errorInfo))
                    } else {
                        // 尝试解析为 OpenAI 兼容格式 (fallback)
                        const parsed = JSON.parse(data)

                        // 旧版推理步骤事件兼容
                        if (parsed.type === 'reasoning_step') {
                            // 转换为新格式
                            const step = parsed.step
                            onStep({
                                id: step.id,
                                type: mapLegacyStepType(step.type),
                                content: step.content,
                                status: mapLegacyStatus(step.status),
                                timestamp: new Date(step.timestamp).getTime(),
                                metadata: {
                                    ...step.metadata,
                                    legacy_title: step.title,
                                    duration_ms: step.duration
                                }
                            })
                            continue
                        }

                        // 旧版推理内容追加
                        if (parsed.type === 'reasoning_content') {
                            if (onStepContent) {
                                onStepContent(parsed.step_id, parsed.content)
                            }
                            continue
                        }

                        // 旧版推理步骤更新
                        if (parsed.type === 'reasoning_step_update') {
                            if (onStepUpdate) {
                                onStepUpdate(parsed.step_id, {
                                    ...parsed.updates,
                                    duration_ms: parsed.updates.duration
                                })
                            }
                            continue
                        }

                        // 旧版推理结束
                        if (parsed.type === 'reasoning_end') {
                            if (onReasoningEnd) {
                                onReasoningEnd()
                            }
                            continue
                        }

                        // OpenAI 标准格式
                        const content = parsed.choices?.[0]?.delta?.content
                        if (content) {
                            onContent(content)
                        }
                    }
                } catch (parseError) {
                    // JSON 解析失败，可能是纯文本内容
                    console.warn('Failed to parse SSE data:', data, parseError)
                }
            }
        }
    } catch (error) {
        onError(error instanceof Error ? error : new Error(String(error)))
    }
}

/**
 * 将旧版步骤类型映射到新类型
 */
function mapLegacyStepType(legacyType: string): AgentStepType {
    switch (legacyType) {
        case 'thinking':
        case 'analysis':
        case 'conclusion':
            return 'reasoning'
        case 'retrieval':
        case 'workflow':
            return 'tool_call'
        case 'tool_call':
            return 'tool_call'
        default:
            return 'reasoning'
    }
}

/**
 * 将旧版状态映射到新状态
 */
function mapLegacyStatus(legacyStatus: string): AgentStepStatus {
    switch (legacyStatus) {
        case 'pending':
            return 'pending'
        case 'running':
            return 'running'
        case 'completed':
            return 'completed'
        case 'error':
            return 'failed'
        default:
            return 'pending'
    }
}

/**
 * 获取所有聊天会话
 */
export async function getChatSessions(): Promise<ChatSessionSummary[]> {
    const response = await apiClient.get('/chat/sessions')
    // Gateway 返回 {sessions: [...], stats: {...}}
    return response.data.sessions || response.data
}

export async function createChatSession(title?: string): Promise<ChatSessionDetail> {
    const response = await apiClient.post('/chat/sessions', { title })
    return response.data
}

export async function getChatSessionDetail(sessionId: string): Promise<ChatSessionDetail> {
    const response = await apiClient.get(`/chat/sessions/${sessionId}`)
    return response.data
}

export async function clearChatSession(sessionId: string): Promise<void> {
    await apiClient.post(`/chat/sessions/${sessionId}/clear`)
}

export async function updateChatSessionTitle(sessionId: string, title: string): Promise<ChatSessionSummary> {
    const response = await apiClient.patch(`/chat/sessions/${sessionId}/title`, { title })
    return response.data
}

/**
 * 删除聊天会话
 */
export async function deleteChatSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/chat/sessions/${sessionId}`)
}

export async function convertChatSessionToPipeline(sessionId: string): Promise<PipelineRecommendation> {
    const response = await apiClient.post('/chat/generate-workflow', {
        user_input: '根据我们的对话历史生成工作流',
        session_id: sessionId,
        enable_optimization: false,
    })
    return response.data
}

// ==================== 文件上传 API ====================

export interface FileMetadata {
    file_id: string
    filename: string
    original_name: string
    file_type: string
    size_bytes: number
    upload_time: string  // ISO format
    path: string
    indexed: boolean
}

export const uploadFile = async (file: File): Promise<FileMetadata> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<FileMetadata>('/uploads', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    })
    return response.data
}

export const listFiles = async (): Promise<FileMetadata[]> => {
    const response = await apiClient.get<FileMetadata[]>('/uploads')
    return response.data
}

export const deleteFile = async (fileId: string): Promise<void> => {
    await apiClient.delete(`/uploads/${fileId}`)
}

// ==================== 记忆 API ====================

export interface MemoryConfig {
    enabled: boolean
    backends: string[]
    short_term: { max_items: number }
    long_term: { enabled: boolean }
}

export interface MemoryStats {
    short_term_count: number
    long_term_count: number
    available: boolean
}

export const getMemoryConfig = async (): Promise<MemoryConfig> => {
    const response = await apiClient.get<MemoryConfig>('/studio/memory/config')
    return response.data
}

export const getMemoryStats = async (sessionId: string): Promise<MemoryStats> => {
    const response = await apiClient.get<MemoryStats>('/chat/memory/stats', {
        params: { session_id: sessionId },
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

// ==================== LLM 状态 API ====================

export interface LLMStatus {
    running: boolean
    healthy: boolean
    service_type: 'local_vllm' | 'remote_api' | 'not_configured' | 'unknown' | 'error'
    model_name: string
    base_url: string
    is_local: boolean
    details?: {
        model_id: string
        max_model_len: number
        owned_by: string
    }
    available_models?: Array<{
        name: string
        base_url: string
        is_local: boolean
        description?: string
        healthy?: boolean
    }>
    error?: string
}

export async function getLLMStatus(): Promise<LLMStatus> {
    const response = await apiClient.get('/llm/status')
    return response.data
}

export async function selectLLMModel(modelName: string, baseUrl: string): Promise<void> {
    await apiClient.post('/llm/select', { model_name: modelName, base_url: baseUrl })
}

export default apiClient
