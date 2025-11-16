/**
 * Chat Mode Store - Zustand state management for Chat UI
 */

import { create } from 'zustand'
import type { ChatSessionSummary } from '../services/api'

type SetState<T> = (partial: T | Partial<T> | ((state: T) => T | Partial<T>)) => void
type GetState<T> = () => T

export interface ChatMessage {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: string
    isStreaming?: boolean
    metadata?: Record<string, any>
}

interface ChatState {
    // 当前会话
    currentSessionId: string | null

    // 会话列表
    sessions: ChatSessionSummary[]

    // 消息列表（按会话ID分组）
    messages: Record<string, ChatMessage[]>

    // 当前输入
    currentInput: string

    // 流式响应状态
    isStreaming: boolean
    streamingMessageId: string | null

    // UI 状态
    isLoading: boolean

    // Actions
    setCurrentSessionId: (sessionId: string | null) => void
    setSessions: (sessions: ChatSessionSummary[]) => void
    addSession: (session: ChatSessionSummary) => void
    removeSession: (sessionId: string) => void
    updateSessionTitle: (sessionId: string, title: string) => void
    updateSessionStats: (sessionId: string, patch: Partial<ChatSessionSummary>) => void

    setMessages: (sessionId: string, messages: ChatMessage[]) => void
    addMessage: (sessionId: string, message: ChatMessage) => void
    updateMessage: (sessionId: string, messageId: string, content: string) => void
    appendToMessage: (sessionId: string, messageId: string, chunk: string) => void

    setCurrentInput: (input: string) => void
    setIsStreaming: (isStreaming: boolean) => void
    setStreamingMessageId: (messageId: string | null) => void
    setIsLoading: (isLoading: boolean) => void

    // 清空当前会话
    clearCurrentSession: () => void
}

export const useChatStore = create<ChatState>((
    set: SetState<ChatState>,
    get: GetState<ChatState>
) => ({
    currentSessionId: null,
    sessions: [],
    messages: {},
    currentInput: '',
    isStreaming: false,
    streamingMessageId: null,
    isLoading: false,

    setCurrentSessionId: (sessionId: string | null) => set({ currentSessionId: sessionId }),

    setSessions: (sessions: ChatSessionSummary[]) => set({ sessions }),

    addSession: (session: ChatSessionSummary) => set((state: ChatState) => {
        const filtered = state.sessions.filter((s: ChatSessionSummary) => s.id !== session.id)
        return {
            sessions: [session, ...filtered],
        }
    }),

    removeSession: (sessionId: string) => set((state: ChatState) => {
        const newSessions = state.sessions.filter((s: ChatSessionSummary) => s.id !== sessionId)
        const newMessages = { ...state.messages }
        delete newMessages[sessionId]

        return {
            sessions: newSessions,
            messages: newMessages,
            currentSessionId: state.currentSessionId === sessionId
                ? (newSessions[0]?.id || null)
                : state.currentSessionId,
        }
    }),

    updateSessionTitle: (sessionId: string, title: string) => set((state: ChatState) => ({
        sessions: state.sessions.map((s: ChatSessionSummary) =>
            s.id === sessionId ? { ...s, title } : s
        ),
    })),

    updateSessionStats: (sessionId: string, patch: Partial<ChatSessionSummary>) => set((state: ChatState) => ({
        sessions: state.sessions.map((s: ChatSessionSummary) =>
            s.id === sessionId ? { ...s, ...patch } : s
        ),
    })),

    setMessages: (sessionId: string, messages: ChatMessage[]) => set((state: ChatState) => ({
        messages: {
            ...state.messages,
            [sessionId]: messages,
        },
    })),

    addMessage: (sessionId: string, message: ChatMessage) => set((state: ChatState) => {
        const sessionMessages = state.messages[sessionId] || []
        return {
            messages: {
                ...state.messages,
                [sessionId]: [...sessionMessages, message],
            },
        }
    }),

    updateMessage: (sessionId: string, messageId: string, content: string) => set((state: ChatState) => {
        const sessionMessages = state.messages[sessionId] || []
        return {
            messages: {
                ...state.messages,
                [sessionId]: sessionMessages.map((msg: ChatMessage) =>
                    msg.id === messageId ? { ...msg, content } : msg
                ),
            },
        }
    }),

    appendToMessage: (sessionId: string, messageId: string, chunk: string) => set((state: ChatState) => {
        const sessionMessages = state.messages[sessionId] || []
        return {
            messages: {
                ...state.messages,
                [sessionId]: sessionMessages.map((msg: ChatMessage) =>
                    msg.id === messageId
                        ? { ...msg, content: msg.content + chunk }
                        : msg
                ),
            },
        }
    }),

    setCurrentInput: (input: string) => set({ currentInput: input }),

    setIsStreaming: (isStreaming: boolean) => set({ isStreaming }),

    setStreamingMessageId: (messageId: string | null) => set({ streamingMessageId: messageId }),

    setIsLoading: (isLoading: boolean) => set({ isLoading }),

    clearCurrentSession: () => {
        const { currentSessionId } = get()
        if (currentSessionId) {
            set((state: ChatState) => ({
                messages: {
                    ...state.messages,
                    [currentSessionId]: [],
                },
            }))
        }
    },
}))
