/**
 * Chat Mode Component - ChatGPT-style interface for SAGE
 */

import React, { useEffect, useRef, useState } from 'react'
import type { Edge, Node } from 'reactflow'
import {
    Button,
    Input,
    Tooltip,
    Dropdown,
    Empty,
    Spin,
    message as antMessage,
    Typography,
    Space,
} from 'antd'
import {
    Send,
    Plus,
    Trash2,
    MessageSquare,
    User,
    Bot,
    MoreVertical,
    Loader,
    Sparkles,
    ArrowRightCircle,
} from 'lucide-react'
import { useChatStore, type ChatMessage } from '../store/chatStore'
import MessageContent from './MessageContent'
import {
    sendChatMessage,
    getChatSessions,
    deleteChatSession,
    createChatSession,
    getChatSessionDetail,
    clearChatSession as clearSessionApi,
    convertChatSessionToPipeline,
    type ChatSessionSummary,
} from '../services/api'
import { useFlowStore } from '../store/flowStore'
import type { AppMode } from '../App'

const { TextArea } = Input

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
    } = useChatStore()
    const { setNodes, setEdges } = useFlowStore()

    const messagesEndRef = useRef<HTMLDivElement>(null)
    const textAreaRef = useRef<any>(null)
    const [isSending, setIsSending] = useState(false)
    const [isConverting, setIsConverting] = useState(false)
    const [recommendationSummary, setRecommendationSummary] = useState<string | null>(null)
    const [recommendationInsights, setRecommendationInsights] = useState<string[]>([])

    // 自动滚动到底部
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages[currentSessionId || '']])

    useEffect(() => {
        loadSessions()
    }, [])

    // 自动聚焦输入框
    useEffect(() => {
        if (!isStreaming && textAreaRef.current) {
            textAreaRef.current.focus()
        }
    }, [isStreaming])

    useEffect(() => {
        setRecommendationSummary(null)
        setRecommendationInsights([])
    }, [currentSessionId])

    const loadSessions = async () => {
        try {
            setIsLoading(true)
            const sessionList = await getChatSessions()
            setSessions(sessionList)

            // 如果没有当前会话且有会话列表，选择第一个
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
            const mappedMessages: ChatMessage[] = detail.messages.map((msg, index) => ({
                id: `server_${index}_${msg.timestamp}`,
                role: msg.role,
                content: msg.content,
                timestamp: msg.timestamp,
                metadata: msg.metadata,
            }))
            setMessages(sessionId, mappedMessages)
            updateSessionStats(sessionId, {
                message_count: mappedMessages.length,
                last_active: detail.last_active,
            })
        } catch (error) {
            console.error('Failed to load sessions:', error)
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
            // 如果没有当前会话，创建一个新会话
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

            // 添加用户消息
            const userMessage: ChatMessage = {
                id: `msg_${Date.now()}_user`,
                role: 'user',
                content: userMessageContent,
                timestamp: new Date().toISOString(),
            }
            addMessage(sessionId, userMessage)

            // 创建 AI 消息占位符
            const assistantMessageId = `msg_${Date.now()}_assistant`
            const assistantMessage: ChatMessage = {
                id: assistantMessageId,
                role: 'assistant',
                content: '',
                timestamp: new Date().toISOString(),
                isStreaming: true,
            }
            addMessage(sessionId, assistantMessage)

            // 开始流式响应
            setIsStreaming(true)
            setStreamingMessageId(assistantMessageId)

            // 调用 API（SSE 流式）
            await sendChatMessage(
                userMessageContent,
                sessionId,
                (chunk: string) => {
                    // 流式更新消息内容
                    appendToMessage(sessionId, assistantMessageId, chunk)
                },
                (error: Error) => {
                    // 错误处理
                    console.error('Streaming error:', error)
                    antMessage.error(`发送失败: ${error.message}`)
                    setIsStreaming(false)
                    setStreamingMessageId(null)
                },
                () => {
                    // 完成回调
                    setIsStreaming(false)
                    setStreamingMessageId(null)

                    // 更新会话列表（消息数+1）
                    updateSessionStats(sessionId!, {
                        message_count: (messages[sessionId!] || []).length,
                        last_active: new Date().toISOString(),
                    })
                }
            )
        } catch (error) {
            console.error('Send message error:', error)
            antMessage.error('发送消息失败')
        } finally {
            setIsSending(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
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
            antMessage.error('创建会话失败')
        } finally {
            setIsLoading(false)
        }
    }

    const handleDeleteSession = async (sessionId: string) => {
        try {
            await deleteChatSession(sessionId)
            removeSession(sessionId)
            antMessage.success('会话已删除')
        } catch (error) {
            console.error('Delete session error:', error)
            antMessage.error('删除会话失败')
        }
    }

    const handleClearCurrentSession = async () => {
        if (!currentSessionId) return
        try {
            await clearSessionApi(currentSessionId)
            clearCurrentSession()
            antMessage.success('当前会话已清空')
        } catch (_error) {
            antMessage.error('清空会话失败')
        }
    }

    const handleConvertToPipeline = async () => {
        if (!currentSessionId) return
        setIsConverting(true)
        setRecommendationSummary(null)
        setRecommendationInsights([])
        try {
            const recommendation = await convertChatSessionToPipeline(currentSessionId)
            setNodes(recommendation.nodes as Node[])
            setEdges(recommendation.edges as Edge[])
            setRecommendationSummary(recommendation.summary)
            setRecommendationInsights(recommendation.insights)
            antMessage.success(`已生成推荐：${recommendation.suggested_name}`)
        } catch (error) {
            console.error('Convert error', error)
            antMessage.error('无法生成推荐管道')
        } finally {
            setIsConverting(false)
        }
    }

    const currentMessages = messages[currentSessionId || ''] || []

    return (
        <div className="h-full flex">
            {/* 左侧会话列表 */}
            <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
                {/* 新建按钮 */}
                <div className="p-4 border-b border-gray-200">
                    <Button
                        type="primary"
                        icon={<Plus size={16} />}
                        onClick={handleNewChat}
                        block
                        disabled={isStreaming}
                    >
                        New Chat
                    </Button>
                </div>

                {/* 会话列表 */}
                <div className="flex-1 overflow-y-auto p-2">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-32">
                            <Spin />
                        </div>
                    ) : sessions.length === 0 ? (
                        <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="No chats yet"
                            className="mt-8"
                        />
                    ) : (
                        sessions.map((session: ChatSessionSummary) => (
                            <div
                                key={session.id}
                                className={`
                                    group p-3 mb-2 rounded-lg cursor-pointer
                                    transition-colors duration-200
                                    ${currentSessionId === session.id
                                        ? 'bg-blue-100 border border-blue-300'
                                        : 'bg-white hover:bg-gray-100 border border-gray-200'
                                    }
                                `}
                                onClick={() => {
                                    setCurrentSessionId(session.id)
                                    loadSessionMessages(session.id)
                                }}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <MessageSquare size={14} className="text-gray-500 flex-shrink-0" />
                                            <span className="text-sm font-medium text-gray-800 truncate">
                                                {session.title}
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1">
                                            {session.message_count} messages
                                        </div>
                                    </div>

                                    <Dropdown
                                        menu={{
                                            items: [
                                                {
                                                    key: 'delete',
                                                    label: 'Delete',
                                                    danger: true,
                                                    onClick: () => handleDeleteSession(session.id),
                                                },
                                            ],
                                        }}
                                        trigger={['click']}
                                    >
                                        <Button
                                            type="text"
                                            size="small"
                                            icon={<MoreVertical size={14} />}
                                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                                            onClick={(e: React.MouseEvent<HTMLButtonElement>) => e.stopPropagation()}
                                        />
                                    </Dropdown>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* 右侧聊天区域 */}
            <div className="flex-1 flex flex-col bg-white">
                {!currentSessionId ? (
                    <div className="flex-1 flex items-center justify-center">
                        <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="Select or create a chat to get started"
                        />
                    </div>
                ) : (
                    <>
                        {/* 顶部工具栏 */}
                        <div className="h-14 border-b border-gray-200 flex items-center justify-between px-6">
                            <div className="flex items-center gap-2">
                                <MessageSquare size={18} className="text-gray-600" />
                                <span className="font-medium text-gray-800">
                                    {sessions.find(s => s.id === currentSessionId)?.title || 'Chat'}
                                </span>
                            </div>

                            <Space>
                                <Tooltip title="Convert to pipeline">
                                    <Button
                                        type="default"
                                        icon={<Sparkles size={16} />}
                                        onClick={handleConvertToPipeline}
                                        disabled={currentMessages.length === 0 || isStreaming}
                                        loading={isConverting}
                                    >
                                        Convert
                                    </Button>
                                </Tooltip>

                                <Tooltip title="Clear current chat">
                                    <Button
                                        type="text"
                                        icon={<Trash2 size={16} />}
                                        onClick={handleClearCurrentSession}
                                        disabled={currentMessages.length === 0 || isStreaming}
                                    >
                                        Clear
                                    </Button>
                                </Tooltip>
                            </Space>
                        </div>

                        {/* 消息列表 */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-4">
                            {recommendationSummary && (
                                <div className="max-w-3xl mx-auto space-y-2">
                                    <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                                        <Typography.Text>{recommendationSummary}</Typography.Text>
                                        {recommendationInsights.length > 0 && (
                                            <ul className="mt-2 list-disc list-inside text-sm text-gray-600">
                                                {recommendationInsights.map((tip) => (
                                                    <li key={tip}>{tip}</li>
                                                ))}
                                            </ul>
                                        )}
                                        <Button
                                            type="link"
                                            icon={<ArrowRightCircle size={16} />}
                                            onClick={() => onModeChange?.('builder')}
                                            className="px-0 mt-2"
                                        >
                                            Go to Builder
                                        </Button>
                                    </div>
                                </div>
                            )}
                            {currentMessages.length === 0 ? (
                                <div className="flex items-center justify-center h-full">
                                    <div className="text-center">
                                        <Bot size={48} className="text-gray-300 mx-auto mb-4" />
                                        <p className="text-gray-500">Start a conversation with SAGE</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="max-w-3xl mx-auto space-y-6">
                                    {currentMessages.map((msg) => (
                                        <div
                                            key={msg.id}
                                            className={`flex gap-4 ${
                                                msg.role === 'user' ? 'justify-end' : 'justify-start'
                                            }`}
                                        >
                                            {msg.role === 'assistant' && (
                                                <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                                                    <Bot size={18} className="text-white" />
                                                </div>
                                            )}

                                            <div
                                                className={`
                                                    max-w-2xl px-4 py-3 rounded-lg
                                                    ${msg.role === 'user'
                                                        ? 'bg-blue-500 text-white'
                                                        : 'bg-gray-100 text-gray-800'
                                                    }
                                                `}
                                            >
                                                <MessageContent
                                                    content={msg.content}
                                                    isUser={msg.role === 'user'}
                                                    isStreaming={msg.isStreaming}
                                                    streamingMessageId={streamingMessageId}
                                                    messageId={msg.id}
                                                />
                                            </div>

                                            {msg.role === 'user' && (
                                                <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0">
                                                    <User size={18} className="text-white" />
                                                </div>
                                            )}
                                        </div>
                                    ))}

                                    {isStreaming && (
                                        <div className="flex gap-4 justify-start">
                                            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                                                <Loader size={18} className="text-white animate-spin" />
                                            </div>
                                            <div className="text-gray-500 italic">Thinking...</div>
                                        </div>
                                    )}

                                    <div ref={messagesEndRef} />
                                </div>
                            )}
                        </div>

                        {/* 底部输入框 */}
                        <div className="border-t border-gray-200 p-4">
                            <div className="max-w-3xl mx-auto">
                                <div className="flex gap-2">
                                    <TextArea
                                        ref={textAreaRef}
                                        value={currentInput}
                                        onChange={(e) => setCurrentInput(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                                        autoSize={{ minRows: 1, maxRows: 6 }}
                                        disabled={isStreaming || isSending}
                                        className="flex-1"
                                    />
                                    <Button
                                        type="primary"
                                        icon={<Send size={16} />}
                                        onClick={handleSendMessage}
                                        disabled={!currentInput.trim() || isStreaming || isSending}
                                        loading={isSending || isStreaming}
                                    >
                                        Send
                                    </Button>
                                </div>
                                <div className="text-xs text-gray-400 mt-2">
                                    SAGE can make mistakes. Consider checking important information.
                                </div>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}
