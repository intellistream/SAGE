import { useState, useRef, useEffect } from 'react'
import {
    Modal,
    Input,
    Button,
    Space,
    Dropdown,
    Tabs,
    Badge,
    Tooltip,
    Collapse,
    Typography,
    Empty,
    message,
} from 'antd'
import {
    Send,
    Square,
    Trash2,
    Copy,
    Code,
    MessageSquare,
    CheckCircle2,
    XCircle,
    Loader,
    ChevronDown,
} from 'lucide-react'
import { usePlaygroundStore, type Message, type AgentStep } from '../store/playgroundStore'
import { useFlowStore } from '../store/flowStore'
import { executePlayground } from '../services/api'
import './Playground.css'

const { TextArea } = Input
const { Text, Paragraph } = Typography
const { Panel } = Collapse

export default function Playground() {
    const {
        isOpen,
        currentSessionId,
        sessions,
        messages,
        isExecuting,
        canStop,
        currentInput,
        showCode,
        codeLanguage,
        generatedCode,
        setIsOpen,
        switchSession,
        createSession,
        deleteSession,
        clearSession,
        addMessage,
        updateMessage,
        setCurrentInput,
        setIsExecuting,
        setCanStop,
        stopExecution,
        setShowCode,
        setCodeLanguage,
        generateCode,
    } = usePlaygroundStore()

    const { nodes, currentJobId } = useFlowStore()
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const [activeTab, setActiveTab] = useState<string>('chat')

    // 自动滚动到底部
    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
        }
    }, [messages[currentSessionId]])

    // 生成代码
    useEffect(() => {
        if (showCode && currentJobId) {
            generateCode(currentJobId, 'your-api-key-here')
        }
    }, [showCode, codeLanguage, currentJobId])

    // 发送消息
    const handleSend = async () => {
        if (!currentInput.trim()) {
            message.warning('请输入消息')
            return
        }

        if (nodes.length === 0) {
            message.warning('请先在画布中创建 Flow')
            return
        }

        // 添加用户消息
        addMessage(currentSessionId, {
            role: 'user',
            content: currentInput,
            status: 'completed',
        })

        const userInput = currentInput
        setCurrentInput('')
        setIsExecuting(true)
        setCanStop(true)

        // 添加助手消息占位符
        const assistantMessageId = `msg-${Date.now()}-${Math.random()}`
        addMessage(currentSessionId, {
            role: 'assistant',
            content: '',
            status: 'pending',
        })

        try {
            // 调用执行 API
            const response = await executePlayground({
                flowId: currentJobId || 'temp-flow',
                input: userInput,
                sessionId: currentSessionId,
                stream: false,
            })

            // 更新助手消息
            updateMessage(currentSessionId, assistantMessageId, {
                content: response.output || '执行完成',
                status: 'completed',
                agentSteps: response.agentSteps?.map(step => ({
                    ...step,
                    timestamp: new Date(step.timestamp),
                })),
            })

            setCanStop(false)
        } catch (error) {
            updateMessage(currentSessionId, assistantMessageId, {
                content: `执行失败: ${error instanceof Error ? error.message : '未知错误'}`,
                status: 'error',
                error: error instanceof Error ? error.message : '未知错误',
            })
            message.error('执行失败')
        } finally {
            setIsExecuting(false)
        }
    }

    // 停止执行
    const handleStop = () => {
        stopExecution()
        message.info('已停止执行')
    }

    // 清空会话
    const handleClearSession = () => {
        Modal.confirm({
            title: '确认清空',
            content: '确定要清空当前会话的所有消息吗？',
            onOk: () => {
                clearSession(currentSessionId)
                message.success('会话已清空')
            },
        })
    }

    // 复制消息
    const handleCopyMessage = (content: string) => {
        navigator.clipboard.writeText(content)
        message.success('已复制到剪贴板')
    }

    // 复制代码
    const handleCopyCode = () => {
        navigator.clipboard.writeText(generatedCode)
        message.success('代码已复制到剪贴板')
    }

    // 会话下拉菜单
    const sessionMenuItems = Object.values(sessions).map((session) => ({
        key: session.id,
        label: (
            <div className="flex justify-between items-center">
                <span>{session.name}</span>
                <Badge count={session.messageCount} />
            </div>
        ),
        onClick: () => switchSession(session.id),
    }))

    // 渲染 Agent 步骤
    const renderAgentSteps = (steps: AgentStep[]) => {
        return (
            <Collapse className="agent-steps mt-2">
                {steps.map((step, index) => (
                    <Panel
                        key={index}
                        header={
                            <div className="flex items-center gap-2">
                                {step.type === 'reasoning' && <MessageSquare size={16} />}
                                {step.type === 'tool_call' && <Code size={16} />}
                                {step.type === 'response' && <CheckCircle2 size={16} />}
                                <span className="font-medium">
                                    步骤 {step.step}: {step.toolName || step.type}
                                </span>
                                {step.duration && (
                                    <Text type="secondary" className="text-xs">
                                        ({step.duration}ms)
                                    </Text>
                                )}
                            </div>
                        }
                    >
                        <div className="space-y-2">
                            <div>
                                <Text type="secondary">内容:</Text>
                                <Paragraph className="mt-1">{step.content}</Paragraph>
                            </div>
                            {step.toolInput && (
                                <div>
                                    <Text type="secondary">工具输入:</Text>
                                    <pre className="bg-gray-50 p-2 rounded mt-1 text-xs">
                                        {JSON.stringify(step.toolInput, null, 2)}
                                    </pre>
                                </div>
                            )}
                            {step.toolOutput && (
                                <div>
                                    <Text type="secondary">工具输出:</Text>
                                    <pre className="bg-gray-50 p-2 rounded mt-1 text-xs">
                                        {JSON.stringify(step.toolOutput, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    </Panel>
                ))}
            </Collapse>
        )
    }

    // 渲染消息
    const renderMessage = (msg: Message) => {
        const isUser = msg.role === 'user'

        return (
            <div
                key={msg.id}
                className={`message-item ${isUser ? 'message-user' : 'message-assistant'}`}
            >
                <div className="message-header">
                    <Space>
                        <span className="message-role">
                            {isUser ? '你' : 'AI'}
                        </span>
                        <Text type="secondary" className="text-xs">
                            {msg.timestamp.toLocaleTimeString()}
                        </Text>
                        {msg.status === 'streaming' && <Loader className="animate-spin" size={14} />}
                        {msg.status === 'completed' && <CheckCircle2 className="text-green-500" size={14} />}
                        {msg.status === 'error' && <XCircle className="text-red-500" size={14} />}
                    </Space>
                    <Space>
                        <Tooltip title="复制">
                            <Button
                                type="text"
                                size="small"
                                icon={<Copy size={14} />}
                                onClick={() => handleCopyMessage(msg.content)}
                            />
                        </Tooltip>
                    </Space>
                </div>
                <div className="message-content">
                    <Paragraph className="mb-0">{msg.content}</Paragraph>
                    {msg.error && (
                        <div className="error-message mt-2">
                            <XCircle size={16} className="inline mr-2" />
                            {msg.error}
                        </div>
                    )}
                    {msg.agentSteps && msg.agentSteps.length > 0 && renderAgentSteps(msg.agentSteps)}
                </div>
            </div>
        )
    }

    // 渲染聊天视图
    const renderChatView = () => {
        const currentMessages = messages[currentSessionId] || []

        return (
            <div className="chat-container">
                <div className="messages-list">
                    {currentMessages.length === 0 ? (
                        <Empty
                            description="暂无消息"
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            className="mt-20"
                        />
                    ) : (
                        currentMessages.map(renderMessage)
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <div className="input-area">
                    <TextArea
                        value={currentInput}
                        onChange={(e) => setCurrentInput(e.target.value)}
                        onPressEnter={(e) => {
                            if (!e.shiftKey) {
                                e.preventDefault()
                                handleSend()
                            }
                        }}
                        placeholder="输入消息... (Shift+Enter 换行)"
                        autoSize={{ minRows: 1, maxRows: 4 }}
                        disabled={isExecuting}
                        className="flex-1"
                    />
                    <Space>
                        {canStop ? (
                            <Tooltip title="停止执行">
                                <Button
                                    danger
                                    icon={<Square size={16} />}
                                    onClick={handleStop}
                                >
                                    停止
                                </Button>
                            </Tooltip>
                        ) : (
                            <Tooltip title="发送 (Enter)">
                                <Button
                                    type="primary"
                                    icon={<Send size={16} />}
                                    onClick={handleSend}
                                    disabled={isExecuting || !currentInput.trim()}
                                    loading={isExecuting}
                                >
                                    发送
                                </Button>
                            </Tooltip>
                        )}
                    </Space>
                </div>
            </div>
        )
    }

    // 渲染代码视图
    const renderCodeView = () => {
        return (
            <div className="code-container">
                <div className="code-header">
                    <Space>
                        <span className="font-medium">API 代码示例</span>
                        <Tabs
                            activeKey={codeLanguage}
                            onChange={(key) => setCodeLanguage(key as 'python' | 'curl')}
                            size="small"
                            items={[
                                { key: 'python', label: 'Python' },
                                { key: 'curl', label: 'cURL' },
                            ]}
                        />
                    </Space>
                    <Button
                        icon={<Copy size={16} />}
                        onClick={handleCopyCode}
                    >
                        复制代码
                    </Button>
                </div>
                <pre className="code-content">{generatedCode || '// 正在生成代码...'}</pre>
            </div>
        )
    }

    return (
        <Modal
            title={
                <div className="flex justify-between items-center" style={{ marginRight: '24px' }}>
                    <Space>
                        <span>Playground</span>
                        <Dropdown menu={{ items: sessionMenuItems }}>
                            <Button size="small">
                                {sessions[currentSessionId]?.name}
                                <ChevronDown size={14} />
                            </Button>
                        </Dropdown>
                    </Space>
                    <Space>
                        <Tooltip title="清空会话">
                            <Button
                                size="small"
                                icon={<Trash2 size={14} />}
                                onClick={handleClearSession}
                            />
                        </Tooltip>
                        <Tooltip title="新建会话">
                            <Button
                                size="small"
                                type="primary"
                                onClick={() => createSession()}
                            >
                                新建
                            </Button>
                        </Tooltip>
                    </Space>
                </div>
            }
            open={isOpen}
            onCancel={() => setIsOpen(false)}
            footer={null}
            width={900}
            className="playground-modal"
            styles={{
                body: { padding: 0, height: '70vh' },
            }}
        >
            <Tabs
                activeKey={activeTab}
                onChange={setActiveTab}
                className="playground-tabs"
                items={[
                    {
                        key: 'chat',
                        label: (
                            <span>
                                <MessageSquare size={14} className="inline mr-1" />
                                聊天
                            </span>
                        ),
                        children: renderChatView(),
                    },
                    {
                        key: 'code',
                        label: (
                            <span>
                                <Code size={14} className="inline mr-1" />
                                代码
                            </span>
                        ),
                        children: renderCodeView(),
                    },
                ]}
            />
        </Modal>
    )
}
