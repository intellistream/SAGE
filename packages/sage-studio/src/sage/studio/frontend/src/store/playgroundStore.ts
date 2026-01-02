import { create } from 'zustand'

// 消息类型
export interface Message {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: Date
    agentSteps?: AgentStep[]  // Agent 执行步骤
    status?: 'pending' | 'streaming' | 'completed' | 'error'
    error?: string
}

// Agent 执行步骤
export interface AgentStep {
    step: number
    type: 'reasoning' | 'tool_call' | 'response'
    content: string
    timestamp: Date
    duration?: number
    toolName?: string
    toolInput?: any
    toolOutput?: any
}

// 会话信息
export interface Session {
    id: string
    name: string
    createdAt: Date
    lastActive: Date
    messageCount: number
}

// Playground 状态
export interface PlaygroundState {
    // 模态框显示状态
    isOpen: boolean

    // 当前会话
    currentSessionId: string
    sessions: Record<string, Session>

    // 消息历史
    messages: Record<string, Message[]>  // sessionId -> messages

    // 执行状态
    isExecuting: boolean
    canStop: boolean

    // 输入状态
    currentInput: string

    // 代码视图
    showCode: boolean
    codeLanguage: 'python' | 'curl'
    generatedCode: string

    // Actions
    setIsOpen: (open: boolean) => void

    // 会话管理
    createSession: (name?: string) => string
    switchSession: (sessionId: string) => void
    deleteSession: (sessionId: string) => void
    clearSession: (sessionId: string) => void
    renameSession: (sessionId: string, name: string) => void

    // 消息管理
    addMessage: (sessionId: string, message: Omit<Message, 'id' | 'timestamp'>) => string
    updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void
    addAgentStep: (sessionId: string, messageId: string, step: AgentStep) => void

    // 执行控制
    setIsExecuting: (executing: boolean) => void
    setCanStop: (canStop: boolean) => void
    stopExecution: () => void

    // 输入管理
    setCurrentInput: (input: string) => void

    // 代码视图
    setShowCode: (show: boolean) => void
    setCodeLanguage: (lang: 'python' | 'curl') => void
    generateCode: (flowId: string, apiKey: string) => void
}

export const usePlaygroundStore = create<PlaygroundState>((set, get) => ({
    // 初始状态
    isOpen: false,
    currentSessionId: 'default',
    sessions: {
        default: {
            id: 'default',
            name: 'Default Session',
            createdAt: new Date(),
            lastActive: new Date(),
            messageCount: 0,
        },
    },
    messages: {
        default: [],
    },
    isExecuting: false,
    canStop: false,
    currentInput: '',
    showCode: false,
    codeLanguage: 'python',
    generatedCode: '',

    // 模态框控制
    setIsOpen: (open) => {
        set({ isOpen: open })
    },

    // 会话管理
    createSession: (name) => {
        const sessionId = `session-${Date.now()}`
        const newSession: Session = {
            id: sessionId,
            name: name || `Session ${Object.keys(get().sessions).length + 1}`,
            createdAt: new Date(),
            lastActive: new Date(),
            messageCount: 0,
        }

        set((state) => ({
            sessions: {
                ...state.sessions,
                [sessionId]: newSession,
            },
            messages: {
                ...state.messages,
                [sessionId]: [],
            },
            currentSessionId: sessionId,
        }))

        return sessionId
    },

    switchSession: (sessionId) => {
        if (get().sessions[sessionId]) {
            set({
                currentSessionId: sessionId,
                currentInput: '',
            })
        }
    },

    deleteSession: (sessionId) => {
        if (sessionId === 'default') return // 不能删除默认会话

        const state = get()
        const { [sessionId]: _, ...remainingSessions } = state.sessions
        const { [sessionId]: __, ...remainingMessages } = state.messages

        set({
            sessions: remainingSessions,
            messages: remainingMessages,
            currentSessionId: state.currentSessionId === sessionId ? 'default' : state.currentSessionId,
        })
    },

    clearSession: (sessionId) => {
        set((state) => ({
            messages: {
                ...state.messages,
                [sessionId]: [],
            },
            sessions: {
                ...state.sessions,
                [sessionId]: {
                    ...state.sessions[sessionId],
                    messageCount: 0,
                    lastActive: new Date(),
                },
            },
        }))
    },

    renameSession: (sessionId, name) => {
        set((state) => ({
            sessions: {
                ...state.sessions,
                [sessionId]: {
                    ...state.sessions[sessionId],
                    name,
                },
            },
        }))
    },

    // 消息管理
    addMessage: (sessionId, message) => {
        const newMessage: Message = {
            ...message,
            id: `msg-${Date.now()}-${Math.random()}`,
            timestamp: new Date(),
        }

        set((state) => ({
            messages: {
                ...state.messages,
                [sessionId]: [...(state.messages[sessionId] || []), newMessage],
            },
            sessions: {
                ...state.sessions,
                [sessionId]: {
                    ...state.sessions[sessionId],
                    messageCount: (state.sessions[sessionId]?.messageCount || 0) + 1,
                    lastActive: new Date(),
                },
            },
        }))

        return newMessage.id
    },

    updateMessage: (sessionId, messageId, updates) => {
        set((state) => ({
            messages: {
                ...state.messages,
                [sessionId]: state.messages[sessionId].map((msg) =>
                    msg.id === messageId ? { ...msg, ...updates } : msg
                ),
            },
        }))
    },

    addAgentStep: (sessionId, messageId, step) => {
        set((state) => ({
            messages: {
                ...state.messages,
                [sessionId]: state.messages[sessionId].map((msg) =>
                    msg.id === messageId
                        ? {
                            ...msg,
                            agentSteps: [...(msg.agentSteps || []), step],
                        }
                        : msg
                ),
            },
        }))
    },

    // 执行控制
    setIsExecuting: (executing) => {
        set({ isExecuting: executing })
    },

    setCanStop: (canStop) => {
        set({ canStop })
    },

    stopExecution: () => {
        // TODO: 实现停止执行的逻辑
        // Issue URL: https://github.com/intellistream/SAGE/issues/1030
        set({
            isExecuting: false,
            canStop: false,
        })
    },

    // 输入管理
    setCurrentInput: (input) => {
        set({ currentInput: input })
    },

    // 代码视图
    setShowCode: (show) => {
        set({ showCode: show })
    },

    setCodeLanguage: (lang) => {
        set({ codeLanguage: lang })
    },

    generateCode: (flowId, apiKey) => {
        const lang = get().codeLanguage
        let code = ''

        if (lang === 'python') {
            code = `import requests

# SAGE Studio API Configuration
API_URL = "http://localhost:8889/api"
FLOW_ID = "${flowId}"
API_KEY = "${apiKey}"

# Execute the flow
response = requests.post(
    f"{API_URL}/playground/execute/{FLOW_ID}",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "input": "Your input text here",
        "session_id": "default",
        "stream": False
    }
)

# Print the result
if response.status_code == 200:
    result = response.json()
    print("Success:", result.get("output"))
else:
    print("Error:", response.text)
`
        } else {
            code = `# Execute SAGE Studio Flow

curl -X POST "http://localhost:8889/api/playground/execute/${flowId}" \\
  -H "Authorization: Bearer ${apiKey}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": "Your input text here",
    "session_id": "default",
    "stream": false
  }'
`
        }

        set({ generatedCode: code })
    },
}))
