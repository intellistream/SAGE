/**
 * ReasoningAccordion Component - 展示 AI 的思考过程
 *
 * 功能：
 * - 在推理过程中实时流式展示思考步骤
 * - 推理结束后自动折叠，用户可点击展开查看
 * - 支持多种步骤类型：思考、检索、工作流生成等
 */

import { useState, useEffect } from 'react'
import {
    ChevronDown,
    ChevronRight,
    Brain,
    Search,
    Workflow,
    CheckCircle,
    Loader,
    Lightbulb,
    FileText,
    Wrench,
    MessageSquare,
    AlertCircle,
} from 'lucide-react'

/**
 * 推理步骤类型
 * - thinking: 思考推理过程
 * - retrieval: 检索文档/知识库
 * - workflow: 生成工作流
 * - analysis: 分析内容
 * - conclusion: 得出结论
 * - tool_call: 调用工具（包含工具名和输入参数）
 * - tool_result: 工具返回结果
 * - response: 最终响应生成
 */
export type ReasoningStepType =
    | 'thinking'      // 思考中
    | 'retrieval'     // 检索文档
    | 'workflow'      // 生成工作流
    | 'analysis'      // 分析
    | 'conclusion'    // 得出结论
    | 'tool_call'     // 工具调用
    | 'tool_result'   // 工具返回结果
    | 'response'      // 最终响应

/**
 * 推理步骤状态
 */
export type ReasoningStepStatus = 'pending' | 'running' | 'completed' | 'error'

/**
 * 工具调用元数据
 */
export interface ToolCallMetadata {
    tool_name: string           // 工具名称
    tool_input?: unknown        // 工具输入参数（JSON）
    tool_output?: unknown       // 工具输出结果（JSON）
    confidence?: number         // 置信度 (0-1)
    error_message?: string      // 错误信息（如果有）
}

/**
 * 单个推理步骤
 */
export interface ReasoningStep {
    id: string
    type: ReasoningStepType
    title: string
    content: string
    status: ReasoningStepStatus
    timestamp: string
    duration?: number  // 耗时（毫秒）
    metadata?: ToolCallMetadata & Record<string, unknown>
}

interface ReasoningAccordionProps {
    steps: ReasoningStep[]
    isStreaming: boolean
    defaultExpanded?: boolean
    className?: string
}

/**
 * 获取步骤类型的图标
 */
function getStepIcon(type: ReasoningStepType, status: ReasoningStepStatus) {
    // 错误状态显示警告图标
    if (status === 'error') {
        return <AlertCircle size={14} className="text-red-500" />
    }

    if (status === 'running') {
        return <Loader size={14} className="animate-spin text-blue-500" />
    }

    switch (type) {
        case 'thinking':
            return <Brain size={14} className="text-purple-500" />
        case 'retrieval':
            return <Search size={14} className="text-green-500" />
        case 'workflow':
            return <Workflow size={14} className="text-orange-500" />
        case 'analysis':
            return <Lightbulb size={14} className="text-yellow-500" />
        case 'conclusion':
            return <CheckCircle size={14} className="text-green-600" />
        case 'tool_call':
            return <Wrench size={14} className="text-blue-500" />
        case 'tool_result':
            return <FileText size={14} className="text-teal-500" />
        case 'response':
            return <MessageSquare size={14} className="text-indigo-500" />
        default:
            return <Brain size={14} className="text-gray-500" />
    }
}

/**
 * 获取步骤类型的中文名称
 */
function getStepTypeName(type: ReasoningStepType): string {
    switch (type) {
        case 'thinking':
            return '思考'
        case 'retrieval':
            return '检索'
        case 'workflow':
            return '工作流'
        case 'analysis':
            return '分析'
        case 'conclusion':
            return '结论'
        case 'tool_call':
            return '工具调用'
        case 'tool_result':
            return '工具返回'
        case 'response':
            return '生成响应'
        default:
            return '处理'
    }
}

/**
 * 格式化耗时
 */
function formatDuration(ms: number): string {
    if (ms < 1000) {
        return `${ms}ms`
    }
    return `${(ms / 1000).toFixed(1)}s`
}

/**
 * 格式化 JSON 数据为可展示的字符串
 */
function formatJsonContent(data: unknown): string {
    if (data === undefined || data === null) {
        return ''
    }
    try {
        return JSON.stringify(data, null, 2)
    } catch {
        return String(data)
    }
}

/**
 * JSON 代码块组件 - 用于展示工具输入/输出
 */
function JsonCodeBlock({
    label,
    data,
    variant = 'default'
}: {
    label: string
    data: unknown
    variant?: 'default' | 'success' | 'error'
}) {
    const [copied, setCopied] = useState(false)

    if (data === undefined || data === null) {
        return null
    }

    const content = formatJsonContent(data)
    if (!content) return null

    const handleCopy = async (e: React.MouseEvent) => {
        e.stopPropagation()
        try {
            await navigator.clipboard.writeText(content)
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
        } catch {
            // Clipboard API not available
        }
    }

    const variantStyles = {
        default: 'bg-slate-800 border-slate-700',
        success: 'bg-emerald-900/50 border-emerald-700',
        error: 'bg-red-900/50 border-red-700',
    }

    return (
        <div className="mt-2">
            <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-500">{label}</span>
                <button
                    onClick={handleCopy}
                    className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-100 transition-colors"
                >
                    {copied ? '已复制' : '复制'}
                </button>
            </div>
            <pre className={`
                text-xs p-2 rounded-md border overflow-x-auto max-h-48 overflow-y-auto
                ${variantStyles[variant]}
            `}>
                <code className="text-gray-200 font-mono whitespace-pre">
                    {content}
                </code>
            </pre>
        </div>
    )
}

/**
 * 工具调用详情组件 - 展示工具名称、输入参数和输出结果
 */
function ToolCallDetails({
    step,
    expanded
}: {
    step: ReasoningStep
    expanded: boolean
}) {
    const [showDetails, setShowDetails] = useState(false)
    const metadata = step.metadata

    if (!metadata) return null

    const { tool_name, tool_input, tool_output, error_message, confidence } = metadata
    const isToolStep = step.type === 'tool_call' || step.type === 'tool_result'

    if (!isToolStep) return null

    // 判断是否有可展示的 JSON 数据
    const hasJsonData = tool_input !== undefined || tool_output !== undefined

    return (
        <div className="mt-1 ml-5">
            {/* 工具名称标签 */}
            {tool_name && (
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        <Wrench size={10} className="mr-1" />
                        {tool_name}
                    </span>
                    {confidence !== undefined && (
                        <span className="text-xs text-gray-400">
                            置信度: {(confidence * 100).toFixed(0)}%
                        </span>
                    )}
                    {hasJsonData && expanded && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation()
                                setShowDetails(!showDetails)
                            }}
                            className="text-xs text-blue-500 hover:text-blue-700 hover:underline"
                        >
                            {showDetails ? '收起 JSON' : '查看 JSON'}
                        </button>
                    )}
                </div>
            )}

            {/* 错误信息 */}
            {error_message && (
                <div className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
                    <AlertCircle size={12} className="inline mr-1" />
                    {error_message}
                </div>
            )}

            {/* 详细的 JSON 数据 */}
            {showDetails && expanded && (
                <div className="space-y-2 mt-2">
                    {tool_input !== undefined && (
                        <JsonCodeBlock
                            label="输入参数"
                            data={tool_input}
                            variant="default"
                        />
                    )}
                    {tool_output !== undefined && (
                        <JsonCodeBlock
                            label="返回结果"
                            data={tool_output}
                            variant={error_message ? 'error' : 'success'}
                        />
                    )}
                </div>
            )}
        </div>
    )
}

/**
 * 单个步骤组件
 */
function StepItem({ step, isLast }: { step: ReasoningStep; isLast: boolean }) {
    const [expanded, setExpanded] = useState(step.status === 'running')
    const isToolStep = step.type === 'tool_call' || step.type === 'tool_result'
    const hasExpandableContent = step.content || (isToolStep && step.metadata)

    // 当步骤正在运行时自动展开
    useEffect(() => {
        if (step.status === 'running') {
            setExpanded(true)
        }
    }, [step.status])

    // 根据步骤类型和状态获取背景样式
    const getStepBgStyle = () => {
        if (step.status === 'error') {
            return 'bg-red-50 border-l-2 border-red-400'
        }
        if (isToolStep && step.status === 'completed') {
            return step.type === 'tool_result' ? 'bg-emerald-50/50' : 'bg-blue-50/50'
        }
        return ''
    }

    return (
        <div className={`relative ${!isLast ? 'pb-2' : ''}`}>
            {/* 连接线 */}
            {!isLast && (
                <div className="absolute left-[7px] top-6 bottom-0 w-px bg-gray-200" />
            )}

            {/* 步骤头部 */}
            <div
                className={`
                    flex items-center gap-2 cursor-pointer rounded px-1 py-0.5 -ml-1
                    transition-colors duration-150
                    hover:bg-gray-50
                    ${getStepBgStyle()}
                `}
                onClick={() => hasExpandableContent && setExpanded(!expanded)}
            >
                {getStepIcon(step.type, step.status)}
                <span className="text-xs font-medium text-gray-600">
                    {step.title || getStepTypeName(step.type)}
                </span>
                {/* 工具名称快速预览（未展开时显示） */}
                {isToolStep && step.metadata?.tool_name && !expanded && (
                    <span className="text-xs text-blue-500 font-mono">
                        [{step.metadata.tool_name}]
                    </span>
                )}
                {step.duration && step.status === 'completed' && (
                    <span className="text-xs text-gray-400">
                        {formatDuration(step.duration)}
                    </span>
                )}
                {hasExpandableContent && (
                    <span className="text-gray-400 ml-auto">
                        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </span>
                )}
            </div>

            {/* 步骤内容 */}
            {expanded && step.content && (
                <div className={`
                    ml-5 mt-1 text-xs text-gray-600 rounded p-2 whitespace-pre-wrap
                    ${isToolStep ? 'bg-gray-100/70' : 'bg-gray-50'}
                `}>
                    {step.content}
                    {step.status === 'running' && (
                        <span className="inline-block w-1.5 h-3 ml-0.5 bg-gray-400 animate-pulse" />
                    )}
                </div>
            )}

            {/* 工具调用详情 */}
            {isToolStep && (
                <ToolCallDetails step={step} expanded={expanded} />
            )}
        </div>
    )
}

/**
 * 推理过程手风琴组件
 */
export default function ReasoningAccordion({
    steps,
    isStreaming,
    defaultExpanded,
    className = '',
}: ReasoningAccordionProps) {
    // 流式传输时默认展开，结束后默认折叠
    const [expanded, setExpanded] = useState(defaultExpanded ?? isStreaming)

    // 当流式传输结束时，自动折叠
    useEffect(() => {
        if (!isStreaming && steps.length > 0) {
            // 延迟折叠，让用户看到最后的状态
            const timer = setTimeout(() => {
                setExpanded(false)
            }, 500)
            return () => clearTimeout(timer)
        }
    }, [isStreaming, steps.length])

    // 当开始流式传输时，自动展开
    useEffect(() => {
        if (isStreaming) {
            setExpanded(true)
        }
    }, [isStreaming])

    if (steps.length === 0) {
        return null
    }

    // 计算总耗时
    const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0)
    const completedSteps = steps.filter(s => s.status === 'completed').length

    return (
        <div className={`mb-3 ${className}`}>
            {/* 手风琴头部 */}
            <div
                className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer
                    transition-colors duration-200
                    ${expanded
                        ? 'bg-purple-50 border border-purple-200'
                        : 'bg-gray-50 border border-gray-200 hover:bg-gray-100'
                    }
                `}
                onClick={() => setExpanded(!expanded)}
            >
                {/* 图标 */}
                <div className={`
                    flex items-center justify-center w-5 h-5 rounded-full
                    ${isStreaming ? 'bg-purple-100' : 'bg-gray-100'}
                `}>
                    {isStreaming ? (
                        <Loader size={12} className="animate-spin text-purple-600" />
                    ) : (
                        <Brain size={12} className="text-gray-500" />
                    )}
                </div>

                {/* 标题 */}
                <span className="text-sm font-medium text-gray-700">
                    {isStreaming ? '思考中...' : '思考过程'}
                </span>

                {/* 统计信息 */}
                {!isStreaming && (
                    <span className="text-xs text-gray-400">
                        {completedSteps} 步骤
                        {totalDuration > 0 && ` · ${formatDuration(totalDuration)}`}
                    </span>
                )}

                {/* 展开/折叠图标 */}
                <span className="ml-auto text-gray-400">
                    {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>
            </div>

            {/* 手风琴内容 */}
            {expanded && (
                <div className="mt-2 ml-2 pl-3 border-l-2 border-purple-200 space-y-1">
                    {steps.map((step, index) => (
                        <StepItem
                            key={step.id}
                            step={step}
                            isLast={index === steps.length - 1}
                        />
                    ))}
                </div>
            )}
        </div>
    )
}
