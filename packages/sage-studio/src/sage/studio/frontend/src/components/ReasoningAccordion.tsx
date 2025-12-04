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
} from 'lucide-react'

/**
 * 推理步骤类型
 */
export type ReasoningStepType =
    | 'thinking'      // 思考中
    | 'retrieval'     // 检索文档
    | 'workflow'      // 生成工作流
    | 'analysis'      // 分析
    | 'conclusion'    // 得出结论
    | 'tool_call'     // 工具调用

/**
 * 推理步骤状态
 */
export type ReasoningStepStatus = 'pending' | 'running' | 'completed' | 'error'

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
    metadata?: Record<string, any>
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
            return <FileText size={14} className="text-blue-500" />
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
 * 单个步骤组件
 */
function StepItem({ step, isLast }: { step: ReasoningStep; isLast: boolean }) {
    const [expanded, setExpanded] = useState(step.status === 'running')

    // 当步骤正在运行时自动展开
    useEffect(() => {
        if (step.status === 'running') {
            setExpanded(true)
        }
    }, [step.status])

    return (
        <div className={`relative ${!isLast ? 'pb-2' : ''}`}>
            {/* 连接线 */}
            {!isLast && (
                <div className="absolute left-[7px] top-6 bottom-0 w-px bg-gray-200" />
            )}

            {/* 步骤头部 */}
            <div
                className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5 -ml-1"
                onClick={() => setExpanded(!expanded)}
            >
                {getStepIcon(step.type, step.status)}
                <span className="text-xs font-medium text-gray-600">
                    {step.title || getStepTypeName(step.type)}
                </span>
                {step.duration && step.status === 'completed' && (
                    <span className="text-xs text-gray-400">
                        {formatDuration(step.duration)}
                    </span>
                )}
                {step.content && (
                    <span className="text-gray-400">
                        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    </span>
                )}
            </div>

            {/* 步骤内容 */}
            {expanded && step.content && (
                <div className="ml-5 mt-1 text-xs text-gray-600 bg-gray-50 rounded p-2 whitespace-pre-wrap">
                    {step.content}
                    {step.status === 'running' && (
                        <span className="inline-block w-1.5 h-3 ml-0.5 bg-gray-400 animate-pulse" />
                    )}
                </div>
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
