/**
 * Chat Mode Component - Gemini-style interface for SAGE
 *
 * Design inspired by Google Gemini's clean, modern aesthetic:
 * - Sidebar: #F0F4F9 background with rounded-full hover states
 * - Main area: Pure white (#FFFFFF) with centered content (max-w-[830px])
 * - Floating capsule input bar with focus transitions
 * - User messages: Right-aligned with light grey bubbles
 * - AI messages: Left-aligned, no bubble, clean typography
 */

import React, { useEffect, useRef, useState } from 'react'
import type { Edge, Node } from 'reactflow'
import {
    Tooltip,
    Dropdown,
    Spin,
    message as antMessage,
} from 'antd'
import {
    Send,
    Plus,
    Trash2,
    MessageSquare,
    MoreHorizontal,
    Loader,
    Sparkles,
    ArrowRight,
    PanelLeftClose,
    PanelLeft,
    Mic,
    ChevronDown,
    Zap,
} from 'lucide-react'
import { useChatStore, type ChatMessage, type ReasoningStep } from '../store/chatStore'
import MessageContent from './MessageContent'
import FileUpload from './FileUpload'
import {
    sendChatMessage,
    getChatSessions,
    deleteChatSession,
    createChatSession,
    getChatSessionDetail,
    clearChatSession as clearSessionApi,
    convertChatSessionToPipeline,
    getLLMStatus,
    type ChatSessionSummary,
    type LLMStatus,
} from '../services/api'
import { useFlowStore } from '../store/flowStore'
import type { AppMode } from '../App'

// ============================================================================
// Sub-Components
// ============================================================================

/** SAGE Logo Icon for AI messages */
function SageLogo({ className = '' }: { className?: string }) {
    return (
        <div className={`w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center ${className}`}>
            <Zap size={16} className="text-white" />
        </div>
    )
}

/** Session list item in sidebar */
function SessionItem({
    session,
    isActive,
    onClick,
    onDelete,
}: {
    session: ChatSessionSummary
    isActive: boolean
    onClick: () => void
    onDelete: () => void
}) {
    return (
        <div
            className={`
                group flex items-center gap-3 px-3 py-2.5 mx-2 rounded-full cursor-pointer
                transition-all duration-200 ease-out
                ${isActive
                    ? 'bg-[#D3E3FD] text-[#1F1F1F]'
                    : 'hover:bg-[#E3E8EE] text-[#444746]'
                }
            `}
            onClick={onClick}
        >
            <MessageSquare size={18} className="flex-shrink-0" />
            <span className="flex-1 text-sm truncate font-medium">
                {session.title}
            </span>
            <Dropdown
                menu={{
                    items: [
                        {
                            key: 'delete',
                            label: 'Delete',
                            danger: true,
                            onClick: (e) => {
                                e.domEvent.stopPropagation()
                                onDelete()
                            },
                        },
                    ],
                }}
                trigger={['click']}
            >
                <button
                    className="opacity-0 group-hover:opacity-100 p-1 rounded-full hover:bg-[#D3E3FD] transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                >
                    <MoreHorizontal size={16} />
                </button>
            </Dropdown>
        </div>
    )
}

/** Model selector dropdown in header */
function ModelSelector({ llmStatus }: { llmStatus: LLMStatus | null }) {
    const modelName = llmStatus?.model_name
        ? (llmStatus.model_name.split('/').pop() || llmStatus.model_name.split('__').pop() || 'Unknown')
        : 'SAGE'

    const isLocal = llmStatus?.is_local
    const isHealthy = llmStatus?.healthy

    return (
        <Dropdown
            menu={{
                items: [
                    {
                        key: 'current',
                        label: (
                            <div className="py-1">
                                <div className="font-medium">{modelName}</div>
                                <div className="text-xs text-gray-500">
                                    {isLocal ? 'Local Model' : 'Cloud Model'} · {isHealthy ? 'Connected' : 'Disconnected'}
                                </div>
                            </div>
                        ),
                        disabled: true,
                    },
                ],
            }}
            trigger={['click']}
        >
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[#F0F4F9] transition-colors">
                <span className="text-sm font-medium text-[#1F1F1F]">
                    {modelName}
                </span>
                <ChevronDown size={16} className="text-[#444746]" />
                {isHealthy && (
                    <span className="w-2 h-2 bg-green-500 rounded-full" />
                )}
            </button>
        </Dropdown>
    )
}

/** Floating input bar - Gemini style */
function ChatInput({
    value,
    onChange,
    onSend,
    onUpload,
    disabled,
    isSending,
}: {
    value: string
    onChange: (value: string) => void
    onSend: () => void
    onUpload: () => void
    disabled: boolean
    isSending: boolean
}) {
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const [isFocused, setIsFocused] = useState(false)

    // Auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current
        if (textarea) {
            textarea.style.height = 'auto'
            textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
        }
    }, [value])

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            onSend()
        }
    }

    return (
        <div className="w-full max-w-[830px] mx-auto px-4 pb-6">
            <div
                className={`
                    relative flex flex-col rounded-[28px] transition-all duration-200
                    ${isFocused
                        ? 'bg-white shadow-lg ring-1 ring-gray-200'
                        : 'bg-[#F0F4F9]'
                    }
                `}
            >
                {/* Textarea */}
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    placeholder="Ask SAGE anything..."
                    disabled={disabled}
                    rows={1}
                    className={`
                        w-full px-6 pt-4 pb-2 bg-transparent resize-none outline-none
                        text-[#1F1F1F] text-base placeholder:text-[#444746]/60
                        min-h-[24px] max-h-[200px]
                    `}
                />

                {/* Bottom toolbar */}
                <div className="flex items-center justify-between px-3 pb-3">
                    {/* Left: Upload button */}
                    <div className="flex items-center gap-1">
                        <Tooltip title="Upload files">
                            <button
                                onClick={onUpload}
                                className="p-2.5 rounded-full hover:bg-[#E3E8EE] transition-colors text-[#444746]"
                            >
                                <Plus size={20} />
                            </button>
                        </Tooltip>
                        <Tooltip title="Voice input (coming soon)">
                            <button
                                className="p-2.5 rounded-full hover:bg-[#E3E8EE] transition-colors text-[#444746] opacity-50 cursor-not-allowed"
                                disabled
                            >
                                <Mic size={20} />
                            </button>
                        </Tooltip>
                    </div>

                    {/* Right: Send button */}
                    <button
                        onClick={onSend}
                        disabled={!value.trim() || disabled}
                        className={`
                            p-2.5 rounded-full transition-all duration-200
                            ${value.trim() && !disabled
                                ? 'bg-[#1F1F1F] text-white hover:bg-[#444746]'
                                : 'bg-[#E8EAED] text-[#444746]/40 cursor-not-allowed'
                            }
                        `}
                    >
                        {isSending ? (
                            <Loader size={20} className="animate-spin" />
                        ) : (
                            <Send size={20} />
                        )}
                    </button>
                </div>
            </div>

            {/* Disclaimer */}
            <p className="text-center text-xs text-[#444746]/70 mt-3">
                SAGE may display inaccurate info, including about people, so double-check its responses.
            </p>
        </div>
    )
}

/** Single message bubble */
function MessageBubble({
    message,
    isStreaming,
    streamingMessageId,
}: {
    message: ChatMessage
    isStreaming: boolean
    streamingMessageId: string | null
}) {
    const isUser = message.role === 'user'

    if (isUser) {
        // User message: Right-aligned, light grey bubble
        return (
            <div className="flex justify-end mb-6">
                <div className="flex items-start gap-3 max-w-[80%]">
                    <div
                        className={`
                            px-5 py-3 rounded-[20px] rounded-tr-sm
                            bg-[#F0F4F9] text-[#1F1F1F]
                        `}
                    >
                        <p className="whitespace-pre-wrap break-words text-base leading-relaxed">
                            {message.content}
                        </p>
                    </div>
                </div>
            </div>
        )
    }

    // AI message: Left-aligned, no bubble, with SAGE logo
    return (
        <div className="flex justify-start mb-8">
            <div className="flex items-start gap-4 max-w-full">
                {/* SAGE Avatar */}
                <SageLogo className="flex-shrink-0 mt-1" />

                {/* Message content */}
                <div className="flex-1 min-w-0">
                    <MessageContent
                        content={message.content}
                        isUser={false}
                        isStreaming={isStreaming && streamingMessageId === message.id}
                        streamingMessageId={streamingMessageId}
                        messageId={message.id}
                        reasoningSteps={message.reasoningSteps}
                        isReasoning={message.isReasoning}
                    />
                </div>
            </div>
        </div>
    )
}

/** Empty state when no messages */
function EmptyState() {
    return (
        <div className="flex-1 flex flex-col items-center justify-center min-h-[400px]">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-6">
                <Zap size={32} className="text-white" />
            </div>
            <h2 className="text-2xl font-normal text-[#1F1F1F] mb-2">
                Hello, how can I help you today?
            </h2>
            <p className="text-[#444746] text-base">
                Start a conversation with SAGE
            </p>
        </div>
    )
}

// ============================================================================
// Main Component
// ============================================================================

interface ChatModeProps {
    onModeChange?: (mode: AppMode) => void
}

export default function ChatMode({ onModeChange }: ChatModeProps) {
    const {
        currentSessionId,
        sessions,
        messages,
        currentInput,
        isStreaming,
        streamingMessageId,
        isLoading,
        setCurrentSessionId,
        setSessions,
        addSession,
        removeSession,
        addMessage,
        appendToMessage,
        setCurrentInput,
        setIsStreaming,
        setStreamingMessageId,
        setIsLoading,
        clearCurrentSession,
        setMessages,
        updateSessionStats,
        addReasoningStep,
        updateReasoningStep,
        appendToReasoningStep,
        setMessageReasoning,
    } = useChatStore()
    const { setNodes, setEdges } = useFlowStore()

    const messagesEndRef = useRef<HTMLDivElement>(null)
    const [isSending, setIsSending] = useState(false)
    const [isConverting, setIsConverting] = useState(false)
    const [recommendationSummary, setRecommendationSummary] = useState<string | null>(null)
    const [recommendationInsights, setRecommendationInsights] = useState<string[]>([])
    const [llmStatus, setLlmStatus] = useState<LLMStatus | null>(null)
    const [isUploadVisible, setIsUploadVisible] = useState(false)
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages[currentSessionId || '']])

    useEffect(() => {
        loadSessions()
        loadLLMStatus()
        const interval = setInterval(loadLLMStatus, 10000)
        return () => clearInterval(interval)
    }, [])

    const loadLLMStatus = async () => {
        try {
            const status = await getLLMStatus()
            setLlmStatus(status)
        } catch (error) {
            console.error('Failed to load LLM status:', error)
        }
    }

    useEffect(() => {
        setRecommendationSummary(null)
        setRecommendationInsights([])
    }, [currentSessionId])

    const loadSessions = async () => {
        try {
            setIsLoading(true)
            const sessionList = await getChatSessions()
            setSessions(sessionList)

            if (!currentSessionId && sessionList.length > 0) {
                setCurrentSessionId(sessionList[0].id)
                await loadSessionMessages(sessionList[0].id)
            }
        } catch (error) {
            console.error('Failed to load sessions:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const loadSessionMessages = async (sessionId: string) => {
        try {
            const detail = await getChatSessionDetail(sessionId)

            const mappedMessages: ChatMessage[] = detail.messages.map((msg, index) => {
                const reasoningSteps = msg.metadata?.reasoningSteps as ReasoningStep[] | undefined

                return {
                    id: `server_${index}_${msg.timestamp}`,
                    role: msg.role,
                    content: msg.content,
                    timestamp: msg.timestamp,
                    metadata: msg.metadata,
                    reasoningSteps: reasoningSteps,
                    isReasoning: false,
                }
            })
            setMessages(sessionId, mappedMessages)
            updateSessionStats(sessionId, {
                message_count: mappedMessages.length,
                last_active: detail.last_active,
            })
        } catch (error: any) {
            console.error('Failed to load session messages:', error)
            if (error?.response?.status === 404) {
                antMessage.error('Session not found or expired')
                removeSession(sessionId)
            } else {
                antMessage.error('Failed to load messages')
            }
            if (currentSessionId === sessionId) {
                setCurrentSessionId(null)
            }
        }
    }

    const handleSendMessage = async () => {
        if (!currentInput.trim() || isStreaming || isSending) {
            return
        }

        const userMessageContent = currentInput.trim()
        setCurrentInput('')
        setIsSending(true)

        try {
            let sessionId = currentSessionId
            if (!sessionId) {
                const newSession = await createChatSession()
                sessionId = newSession.id
                addSession({
                    id: newSession.id,
                    title: newSession.title,
                    created_at: newSession.created_at,
                    last_active: newSession.last_active,
                    message_count: 0,
                })
                setMessages(sessionId, [])
                setCurrentSessionId(sessionId)
            }

            const userMessage: ChatMessage = {
                id: `msg_${Date.now()}_user`,
                role: 'user',
                content: userMessageContent,
                timestamp: new Date().toISOString(),
            }
            addMessage(sessionId, userMessage)

            const assistantMessageId = `msg_${Date.now()}_assistant`
            const assistantMessage: ChatMessage = {
                id: assistantMessageId,
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
                isStreaming: true,
                isReasoning: true,
                reasoningSteps: [],
            }
            addMessage(sessionId, assistantMessage)

            setIsStreaming(true)
            setStreamingMessageId(assistantMessageId)

            await sendChatMessage(
                userMessageContent,
                sessionId,
                (chunk: string) => {
                    appendToMessage(sessionId, assistantMessageId, chunk)
                },
                (error: Error) => {
                    console.error('Streaming error:', error)
                    antMessage.error(`Failed: ${error.message}`)
                    setIsStreaming(false)
                    setStreamingMessageId(null)
                    setMessageReasoning(sessionId, assistantMessageId, false)
                },
                () => {
                    setIsStreaming(false)
                    setStreamingMessageId(null)
                    setMessageReasoning(sessionId, assistantMessageId, false)

                    updateSessionStats(sessionId!, {
                        message_count: (messages[sessionId!] || []).length,
                        last_active: new Date().toISOString(),
                    })
                },
                {
                    onReasoningStep: (step) => {
                        addReasoningStep(sessionId, assistantMessageId, step as ReasoningStep)
                    },
                    onReasoningStepUpdate: (stepId, updates) => {
                        updateReasoningStep(sessionId, assistantMessageId, stepId, updates)
                    },
                    onReasoningContent: (stepId, content) => {
                        appendToReasoningStep(sessionId, assistantMessageId, stepId, content)
                    },
                    onReasoningEnd: () => {
                        setMessageReasoning(sessionId, assistantMessageId, false)
                    },
                }
            )
        } catch (error) {
            console.error('Send message error:', error)
            antMessage.error('Failed to send message')
        } finally {
            setIsSending(false)
        }
    }

    const handleNewChat = async () => {
        try {
            setIsLoading(true)
            const newSession = await createChatSession()
            addSession({
                id: newSession.id,
                title: newSession.title,
                created_at: newSession.created_at,
                last_active: newSession.last_active,
                message_count: 0,
            })
            setMessages(newSession.id, [])
            setCurrentSessionId(newSession.id)
            setCurrentInput('')
        } catch (error) {
            antMessage.error('Failed to create chat')
        } finally {
            setIsLoading(false)
        }
    }

    const handleDeleteSession = async (sessionId: string) => {
        try {
            await deleteChatSession(sessionId)
            removeSession(sessionId)
            antMessage.success('Chat deleted')
        } catch (error) {
            console.error('Delete session error:', error)
            antMessage.error('Failed to delete chat')
        }
    }

    const handleClearCurrentSession = async () => {
        if (!currentSessionId) return
        try {
            await clearSessionApi(currentSessionId)
            clearCurrentSession()
            antMessage.success('Chat cleared')
        } catch (_error) {
            antMessage.error('Failed to clear chat')
        }
    }

    const handleConvertToPipeline = async () => {
        if (!currentSessionId) return
        setIsConverting(true)
        setRecommendationSummary(null)
        setRecommendationInsights([])
        try {
            const recommendation = await convertChatSessionToPipeline(currentSessionId)

            if (!recommendation.success) {
                throw new Error(recommendation.error || 'Failed to generate workflow')
            }

            const { visual_pipeline } = recommendation

            const edges = visual_pipeline.connections.map((conn) => ({
                id: conn.id,
                source: conn.source,
                target: conn.target,
                type: conn.type || 'smoothstep',
                animated: conn.animated !== false,
            }))

            setNodes(visual_pipeline.nodes as Node[])
            setEdges(edges as Edge[])
            setRecommendationSummary(recommendation.message || visual_pipeline.description)
            setRecommendationInsights([`Workflow: ${visual_pipeline.name}`])
            antMessage.success(`Generated: ${visual_pipeline.name}`)
        } catch (error) {
            console.error('Convert error', error)
            antMessage.error(error instanceof Error ? error.message : 'Cannot generate pipeline')
        } finally {
            setIsConverting(false)
        }
    }

    const currentMessages = messages[currentSessionId || ''] || []

    return (
        <div className="h-full flex bg-white">
            {/* ================================================================
                Sidebar - Gemini Style
            ================================================================ */}
            <div
                className={`
                    flex flex-col bg-[#F0F4F9] transition-all duration-300 ease-out
                    ${sidebarCollapsed ? 'w-0 overflow-hidden' : 'w-[280px]'}
                `}
            >
                {/* New Chat Button */}
                <div className="p-3">
                    <button
                        onClick={handleNewChat}
                        disabled={isStreaming}
                        className={`
                            flex items-center gap-3 w-full px-4 py-3 rounded-full
                            bg-[#DDE3EA] text-[#444746] font-medium text-sm
                            hover:bg-white hover:shadow-md transition-all duration-200
                            disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                    >
                        <Plus size={20} />
                        <span>New chat</span>
                    </button>
                </div>

                {/* Session List */}
                <div className="flex-1 overflow-y-auto gemini-scrollbar py-2">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-32">
                            <Spin />
                        </div>
                    ) : sessions.length === 0 ? (
                        <div className="text-center text-[#444746]/60 text-sm py-8 px-4">
                            No conversations yet
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {sessions.map((session: ChatSessionSummary) => (
                                <SessionItem
                                    key={session.id}
                                    session={session}
                                    isActive={currentSessionId === session.id}
                                    onClick={() => {
                                        setCurrentSessionId(session.id)
                                        loadSessionMessages(session.id)
                                    }}
                                    onDelete={() => handleDeleteSession(session.id)}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ================================================================
                Main Chat Area
            ================================================================ */}
            <div className="flex-1 flex flex-col min-w-0 bg-white">
                {/* Header */}
                <header className="sticky top-0 z-10 flex items-center justify-between px-4 py-2 bg-white/80 backdrop-blur-md border-b border-transparent">
                    <div className="flex items-center gap-2">
                        {/* Sidebar Toggle */}
                        <Tooltip title={sidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}>
                            <button
                                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                                className="p-2 rounded-full hover:bg-[#F0F4F9] transition-colors text-[#444746]"
                            >
                                {sidebarCollapsed ? <PanelLeft size={20} /> : <PanelLeftClose size={20} />}
                            </button>
                        </Tooltip>

                        {/* Model Selector */}
                        <ModelSelector llmStatus={llmStatus} />
                    </div>

                    {/* Right Actions */}
                    <div className="flex items-center gap-1">
                        {currentMessages.length > 0 && (
                            <>
                                <Tooltip title="Convert to pipeline">
                                    <button
                                        onClick={handleConvertToPipeline}
                                        disabled={isStreaming || isConverting}
                                        className={`
                                            flex items-center gap-2 px-3 py-2 rounded-full text-sm
                                            transition-colors duration-200
                                            ${isConverting
                                                ? 'bg-[#E8EAED] text-[#444746]/50'
                                                : 'hover:bg-[#F0F4F9] text-[#444746]'
                                            }
                                        `}
                                    >
                                        {isConverting ? (
                                            <Loader size={16} className="animate-spin" />
                                        ) : (
                                            <Sparkles size={16} />
                                        )}
                                        <span className="hidden sm:inline">Convert</span>
                                    </button>
                                </Tooltip>

                                <Tooltip title="Clear chat">
                                    <button
                                        onClick={handleClearCurrentSession}
                                        disabled={isStreaming}
                                        className="p-2 rounded-full hover:bg-[#F0F4F9] transition-colors text-[#444746]"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </Tooltip>
                            </>
                        )}
                    </div>
                </header>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto gemini-scrollbar">
                    <div className="max-w-[830px] mx-auto px-4 py-6">
                        {/* Recommendation Banner */}
                        {recommendationSummary && (
                            <div className="mb-6 p-4 bg-[#E8F0FE] rounded-2xl border border-[#D2E3FC]">
                                <p className="text-[#1F1F1F] text-sm mb-2">{recommendationSummary}</p>
                                {recommendationInsights.length > 0 && (
                                    <ul className="text-xs text-[#444746] mb-3">
                                        {recommendationInsights.map((tip) => (
                                            <li key={tip}>• {tip}</li>
                                        ))}
                                    </ul>
                                )}
                                <button
                                    onClick={() => onModeChange?.('canvas')}
                                    className="flex items-center gap-2 text-sm font-medium text-[#1a73e8] hover:underline"
                                >
                                    Go to Canvas
                                    <ArrowRight size={16} />
                                </button>
                            </div>
                        )}

                        {/* Empty State or Messages */}
                        {currentMessages.length === 0 ? (
                            <EmptyState />
                        ) : (
                            <>
                                {currentMessages.map((msg) => (
                                    <MessageBubble
                                        key={msg.id}
                                        message={msg}
                                        isStreaming={isStreaming}
                                        streamingMessageId={streamingMessageId}
                                    />
                                ))}
                                <div ref={messagesEndRef} />
                            </>
                        )}
                    </div>
                </div>

                {/* Input Area */}
                <div className="flex-shrink-0 bg-gradient-to-t from-white via-white to-transparent pt-4">
                    <ChatInput
                        value={currentInput}
                        onChange={setCurrentInput}
                        onSend={handleSendMessage}
                        onUpload={() => setIsUploadVisible(true)}
                        disabled={isStreaming || isSending}
                        isSending={isSending || isStreaming}
                    />
                </div>
            </div>

            {/* File Upload Modal */}
            <FileUpload visible={isUploadVisible} onClose={() => setIsUploadVisible(false)} />
        </div>
    )
}
