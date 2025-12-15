/**
 * ReasoningAccordion Component - Gemini-style thinking process display
 *
 * Design inspired by Google Gemini's "Show drafts" / thinking indicator:
 * - Subtle, borderless design with light grey background
 * - Smooth animations for expand/collapse
 * - Clean typography and iconography
 * - Auto-expand during streaming, auto-collapse when done
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
    Sparkles,
} from 'lucide-react'

/**
 * 推理步骤类型
 */
export type ReasoningStepType =
    | 'thinking'
    | 'retrieval'
    | 'workflow'
    | 'analysis'
    | 'conclusion'
    | 'tool_call'
    | 'tool_result'
    | 'response'

/**
 * 推理步骤状态
 */
export type ReasoningStepStatus = 'pending' | 'running' | 'completed' | 'error'

/**
 * 工具调用元数据
 */
export interface ToolCallMetadata {
    tool_name: string
    tool_input?: unknown
    tool_output?: unknown
    confidence?: number
    error_message?: string
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
    duration?: number
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
    const baseClass = 'flex-shrink-0'

    if (status === 'error') {
        return <AlertCircle size={14} className={`${baseClass} text-red-500`} />
    }

    if (status === 'running') {
        return <Loader size={14} className={`${baseClass} text-[--gemini-accent] animate-spin`} />
    }

    const iconMap: Record<ReasoningStepType, JSX.Element> = {
        thinking: <Brain size={14} className={`${baseClass} text-purple-500`} />,
        retrieval: <Search size={14} className={`${baseClass} text-green-600`} />,
        workflow: <Workflow size={14} className={`${baseClass} text-orange-500`} />,
        analysis: <Lightbulb size={14} className={`${baseClass} text-amber-500`} />,
        conclusion: <CheckCircle size={14} className={`${baseClass} text-green-600`} />,
        tool_call: <Wrench size={14} className={`${baseClass} text-[--gemini-accent]`} />,
        tool_result: <FileText size={14} className={`${baseClass} text-teal-600`} />,
        response: <MessageSquare size={14} className={`${baseClass} text-indigo-500`} />,
    }

    return iconMap[type] || <Brain size={14} className={`${baseClass} text-[--gemini-text-secondary]`} />
}

/**
 * 获取步骤类型的名称
 */
function getStepTypeName(type: ReasoningStepType): string {
    const nameMap: Record<ReasoningStepType, string> = {
        thinking: 'Thinking',
        retrieval: 'Searching',
        workflow: 'Workflow',
        analysis: 'Analyzing',
        conclusion: 'Conclusion',
        tool_call: 'Using tool',
        tool_result: 'Tool result',
        response: 'Responding',
    }
    return nameMap[type] || 'Processing'
}

/**
 * 格式化耗时
 */
function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
}

/**
 * 格式化 JSON 数据
 */
function formatJsonContent(data: unknown): string {
    if (data === undefined || data === null) return ''
    try {
        return JSON.stringify(data, null, 2)
    } catch {
        return String(data)
    }
}

/**
 * JSON 代码块组件
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

    if (data === undefined || data === null) return null

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
        default: 'bg-gray-900 dark:bg-black',
        success: 'bg-emerald-900/80',
        error: 'bg-red-900/80',
    }

    return (
        <div className="mt-2">
            <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-[--gemini-text-secondary]">{label}</span>
                <button
                    onClick={handleCopy}
                    className="text-xs text-[--gemini-accent] hover:underline px-1.5 py-0.5"
                >
                    {copied ? 'Copied' : 'Copy'}
                </button>
            </div>
            <pre className={`
                text-xs p-3 rounded-xl overflow-x-auto max-h-48 overflow-y-auto
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
 * 工具调用详情组件
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

    const hasJsonData = tool_input !== undefined || tool_output !== undefined

    return (
        <div className="mt-1.5 ml-5">
            {tool_name && (
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[--gemini-accent]/10 text-[--gemini-accent]">
                        <Wrench size={10} className="mr-1" />
                        {tool_name}
                    </span>
                    {confidence !== undefined && (
                        <span className="text-xs text-[--gemini-text-secondary]/60">
                            {(confidence * 100).toFixed(0)}% confidence
                        </span>
                    )}
                    {hasJsonData && expanded && (
                        <button
                            onClick={(e) => {
                                e.stopPropagation()
                                setShowDetails(!showDetails)
                            }}
                            className="text-xs text-[--gemini-accent] hover:underline"
                        >
                            {showDetails ? 'Hide JSON' : 'Show JSON'}
                        </button>
                    )}
                </div>
            )}

            {error_message && (
                <div className="mt-1.5 p-2 bg-red-50 rounded-lg text-xs text-red-600">
                    <AlertCircle size={12} className="inline mr-1" />
                    {error_message}
                </div>
            )}

            {showDetails && expanded && (
                <div className="space-y-2 mt-2">
                    {tool_input !== undefined && (
                        <JsonCodeBlock label="Input" data={tool_input} variant="default" />
                    )}
                    {tool_output !== undefined && (
                        <JsonCodeBlock
                            label="Output"
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

    useEffect(() => {
        if (step.status === 'running') {
            setExpanded(true)
        }
    }, [step.status])

    return (
        <div className={`relative ${!isLast ? 'pb-2' : ''}`}>
            {/* 连接线 */}
            {!isLast && (
                <div className="absolute left-[7px] top-6 bottom-0 w-px bg-[--gemini-border]" />
            )}

            {/* 步骤头部 */}
            <div
                className={`
                    flex items-center gap-2 cursor-pointer rounded-lg px-2 py-1.5 -ml-1
                    transition-colors duration-150
                    hover:bg-[--gemini-hover-bg]
                    ${step.status === 'error' ? 'bg-red-50 dark:bg-red-900/20' : ''}
                `}
                onClick={() => hasExpandableContent && setExpanded(!expanded)}
            >
                {getStepIcon(step.type, step.status)}
                <span className="text-sm text-[--gemini-text-primary]">
                    {step.title || getStepTypeName(step.type)}
                </span>
                {isToolStep && step.metadata?.tool_name && !expanded && (
                    <span className="text-xs text-[--gemini-accent] font-mono">
                        [{step.metadata.tool_name}]
                    </span>
                )}
                {step.duration && step.status === 'completed' && (
                    <span className="text-xs text-[--gemini-text-secondary]/60">
                        {formatDuration(step.duration)}
                    </span>
                )}
                {hasExpandableContent && (
                    <span className="text-[--gemini-text-secondary]/60 ml-auto">
                        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    </span>
                )}
            </div>

            {/* 步骤内容 */}
            {expanded && step.content && (
                <div className={`
                    ml-6 mt-1 text-sm text-[--gemini-text-secondary] rounded-lg p-3 whitespace-pre-wrap
                    bg-[--gemini-sidebar-bg] leading-relaxed
                `}>
                    {step.content}
                    {step.status === 'running' && (
                        <span className="inline-block w-1.5 h-4 ml-0.5 bg-[--gemini-accent] animate-pulse rounded-sm" />
                    )}
                </div>
            )}

            {/* 工具调用详情 */}
            {isToolStep && <ToolCallDetails step={step} expanded={expanded} />}
        </div>
    )
}

/**
 * 推理过程手风琴组件 - Gemini Style
 */
export default function ReasoningAccordion({
    steps,
    isStreaming,
    defaultExpanded,
    className = '',
}: ReasoningAccordionProps) {
    const [expanded, setExpanded] = useState(defaultExpanded ?? isStreaming)

    // 流式传输结束后自动折叠
    useEffect(() => {
        if (!isStreaming && steps.length > 0) {
            const timer = setTimeout(() => {
                setExpanded(false)
            }, 800)
            return () => clearTimeout(timer)
        }
    }, [isStreaming, steps.length])

    // 开始流式传输时自动展开
    useEffect(() => {
        if (isStreaming) {
            setExpanded(true)
        }
    }, [isStreaming])

    if (steps.length === 0) {
        return null
    }

    const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0)
    const completedSteps = steps.filter(s => s.status === 'completed').length

    return (
        <div className={`mb-4 ${className}`}>
            {/* 手风琴头部 - Gemini Style */}
            <div
                className={`
                    flex items-center gap-2.5 px-3 py-2.5 rounded-xl cursor-pointer
                    transition-all duration-200 ease-out
                    ${isStreaming
                        ? 'bg-[--gemini-accent]/10 animate-pulse'
                        : 'bg-[--gemini-sidebar-bg] hover:bg-[--gemini-hover-bg]'
                    }
                `}
                onClick={() => setExpanded(!expanded)}
            >
                {/* 图标 */}
                <div className={`
                    flex items-center justify-center w-6 h-6 rounded-full
                    ${isStreaming ? 'bg-[--gemini-accent]/20' : 'bg-[--gemini-hover-bg]'}
                `}>
                    {isStreaming ? (
                        <Sparkles size={14} className="text-[--gemini-accent] animate-pulse" />
                    ) : (
                        <Brain size={14} className="text-[--gemini-text-secondary]" />
                    )}
                </div>

                {/* 标题 */}
                <span className={`text-sm font-medium ${isStreaming ? 'text-[--gemini-accent]' : 'text-[--gemini-text-primary]'}`}>
                    {isStreaming ? 'Thinking...' : 'Thought process'}
                </span>

                {/* 统计信息 */}
                {!isStreaming && (
                    <span className="text-xs text-[--gemini-text-secondary]/60">
                        {completedSteps} step{completedSteps !== 1 ? 's' : ''}
                        {totalDuration > 0 && ` · ${formatDuration(totalDuration)}`}
                    </span>
                )}

                {/* 展开/折叠图标 */}
                <span className="ml-auto text-[--gemini-text-secondary]/60">
                    {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>
            </div>

            {/* 手风琴内容 */}
            <div
                className={`
                    overflow-hidden transition-all duration-300 ease-out
                    ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}
                `}
            >
                <div className="mt-2 ml-3 pl-3 border-l-2 border-[--gemini-border] space-y-1">
                    {steps.map((step, index) => (
                        <StepItem
                            key={step.id}
                            step={step}
                            isLast={index === steps.length - 1}
                        />
                    ))}
                </div>
            </div>
        </div>
    )
}
