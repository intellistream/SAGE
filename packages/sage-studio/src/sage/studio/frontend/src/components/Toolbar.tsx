/**
 * Toolbar Component - Gemini-style navigation bar for SAGE Studio
 *
 * Design follows the Gemini design system:
 * - Clean white background with subtle border
 * - Pill-shaped buttons with smooth hover transitions
 * - Accent color: #1a73e8 (Gemini blue)
 * - Consistent with ChatMode's visual language
 */

import { useState, useEffect } from 'react'
import { Modal, Input, message, List, Upload, Button } from 'antd'
import { UserOutlined, LogoutOutlined } from '@ant-design/icons'
import {
    Play,
    Square,
    Save,
    FolderOpen,
    Undo as UndoIcon,
    Redo as RedoIcon,
    ZoomIn,
    ZoomOut,
    MessageSquare,
    Download,
    Upload as UploadIcon,
    Settings as SettingsIcon,
    Layout as LayoutIcon,
    User,
    Sun,
    Moon,
    Zap,
} from 'lucide-react'
import { SageIcon } from './SageIcon'
import { useFlowStore } from '../store/flowStore'
import { usePlaygroundStore } from '../store/playgroundStore'
import { useAuthStore } from '../store/authStore'
import { useThemeStore } from '../store/themeStore'
import { submitFlow, getAllJobs, startJob, stopJob, exportFlow, importFlow } from '../services/api'
import { useJobStatusPolling } from '../hooks/useJobStatusPolling'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import Playground from './Playground'
import Settings from './Settings'
import type { AppMode } from '../App'

// ============================================================================
// Gemini-Style UI Components
// ============================================================================

/** SAGE Logo for the toolbar */
function SageLogo() {
    return (
        <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <SageIcon size={16} className="text-white" />
            </div>
            <span className="text-lg font-medium text-[--gemini-text-primary]">SAGE</span>
        </div>
    )
}

/** Theme toggle button */
function ThemeToggle() {
    const { resolvedTheme, toggleTheme } = useThemeStore()

    return (
        <button
            onClick={toggleTheme}
            className="p-2 rounded-full text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] transition-all duration-200"
            title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label="Toggle theme"
        >
            {resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>
    )
}

/** Gemini-style icon button */
function IconButton({
    icon,
    label,
    onClick,
    disabled = false,
    primary = false,
    loading = false,
}: {
    icon: React.ReactNode
    label: string
    onClick?: () => void
    disabled?: boolean
    primary?: boolean
    loading?: boolean
}) {
    return (
        <button
            onClick={onClick}
            disabled={disabled || loading}
            className={`
                flex items-center gap-2 px-3 py-2 rounded-full text-sm font-medium
                transition-all duration-200 ease-out
                disabled:opacity-50 disabled:cursor-not-allowed
                ${primary
                    ? 'bg-[#1a73e8] text-white hover:bg-[#1557b0] hover:shadow-md dark:bg-[#8ab4f8] dark:text-[#1a1a1a] dark:hover:bg-[#aecbfa]'
                    : 'text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg]'
                }
            `}
            title={label}
        >
            {loading ? (
                <span className="animate-spin">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                </span>
            ) : icon}
            <span className="hidden sm:inline">{label}</span>
        </button>
    )
}

/** Mode switcher pill component */
function ModeSwitcher({
    mode,
    onModeChange,
}: {
    mode: AppMode
    onModeChange: (mode: AppMode) => void
}) {
    const modes = [
        { value: 'chat' as const, label: 'Chat', icon: <MessageSquare size={16} /> },
        { value: 'canvas' as const, label: 'Canvas', icon: <LayoutIcon size={16} /> },
        { value: 'finetune' as const, label: 'Finetune', icon: <Zap size={16} /> },
    ]

    return (
        <div className="flex items-center bg-[--gemini-sidebar-bg] rounded-full p-1">
            {modes.map(({ value, label, icon }) => (
                <button
                    key={value}
                    onClick={() => onModeChange(value)}
                    className={`
                        flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium
                        transition-all duration-200 ease-out
                        ${mode === value
                            ? 'bg-[--gemini-main-bg] text-[--gemini-accent] shadow-sm'
                            : 'text-[--gemini-text-secondary] hover:text-[--gemini-text-primary]'
                        }
                    `}
                >
                    {icon}
                    <span>{label}</span>
                </button>
            ))}
        </div>
    )
}

/** User menu dropdown */
function UserMenu({
    user,
    isAuthenticated,
    onLogout,
}: {
    user: any
    isAuthenticated: boolean
    onLogout: () => void
}) {
    const [isOpen, setIsOpen] = useState(false)

    if (!isAuthenticated) {
        return (
            <button
                onClick={() => (window.location.href = '/login')}
                className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium bg-[--gemini-accent] text-white hover:opacity-90 transition-all duration-200"
            >
                Login
            </button>
        )
    }

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 p-1 rounded-full hover:bg-[--gemini-hover-bg] transition-all duration-200"
            >
                <div className="w-8 h-8 rounded-full bg-[--gemini-accent] flex items-center justify-center text-white text-sm font-medium">
                    {user?.username?.[0]?.toUpperCase() || <User size={16} />}
                </div>
            </button>

            {isOpen && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
                    <div className="absolute right-0 top-full mt-2 w-48 bg-[--gemini-main-bg] rounded-xl shadow-lg border border-[--gemini-border] py-2 z-50">
                        <div className="px-4 py-2 border-b border-[--gemini-border]">
                            <div className="text-sm font-medium text-[--gemini-text-primary]">{user?.username || 'User'}</div>
                            {user?.is_guest && <div className="text-xs text-[--gemini-text-secondary]">Guest Mode</div>}
                        </div>
                        {user?.is_guest && (
                            <button
                                onClick={() => {
                                    setIsOpen(false)
                                    window.location.href = '/login'
                                }}
                                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] transition-colors"
                            >
                                <UserOutlined className="text-base" />
                                Login / Sign up
                            </button>
                        )}
                        <button
                            onClick={() => {
                                setIsOpen(false)
                                onLogout()
                            }}
                            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                        >
                            <LogoutOutlined className="text-base" />
                            {user?.is_guest ? 'Exit Guest Mode' : 'Logout'}
                        </button>
                    </div>
                </>
            )}
        </div>
    )
}

// ============================================================================
// Main Toolbar Component
// ============================================================================

interface ToolbarProps {
    mode: AppMode
    onModeChange: (mode: AppMode) => void
}

export default function Toolbar({ mode, onModeChange }: ToolbarProps) {
    const {
        nodes,
        edges,
        setNodes,
        setEdges,
        updateNode,
        reactFlowInstance,
        undo,
        redo,
        canUndo,
        canRedo,
        currentJobId,
        setCurrentJobId,
        isPolling,
    } = useFlowStore()

    const { setIsOpen: setPlaygroundOpen } = usePlaygroundStore()
    const { user, logout, isAuthenticated } = useAuthStore()

    const [saveModalOpen, setSaveModalOpen] = useState(false)
    const [loadModalOpen, setLoadModalOpen] = useState(false)
    const [flowName, setFlowName] = useState('')
    const [flowDescription, setFlowDescription] = useState('')
    const [saving, setSaving] = useState(false)
    const [loading, setLoading] = useState(false)
    const [savedFlows, setSavedFlows] = useState<any[]>([])
    const [running, setRunning] = useState(false)
    const [settingsOpen, setSettingsOpen] = useState(false)

    // 监听 isPolling 状态，同步 running 状态
    useEffect(() => {
        if (!isPolling && running) {
            setRunning(false)
        }
    }, [isPolling, running])

    // 导出流程
    const handleExport = async () => {
        if (!currentJobId) {
            message.warning('请先保存或运行流程后再导出')
            return
        }

        try {
            const blob = await exportFlow(currentJobId)
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `flow_${currentJobId}_${Date.now()}.json`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)
            message.success('流程导出成功')
        } catch (error) {
            message.error(`导出失败: ${error instanceof Error ? error.message : '未知错误'}`)
        }
    }

    // 导入流程
    const handleImport = async (file: File) => {
        try {
            const result = await importFlow(file)
            message.success(`流程导入成功！ID: ${result.flowId}`)

            // 重新加载流程列表
            if (loadModalOpen) {
                const jobs = await getAllJobs()
                setSavedFlows(jobs)
            }

            return false // 阻止默认上传行为
        } catch (error) {
            message.error(`导入失败: ${error instanceof Error ? error.message : '未知错误'}`)
            return false
        }
    }

    // 运行流程
    const handleRun = async () => {
        if (nodes.length === 0) {
            message.warning('画布为空，无法运行')
            return
        }

        try {
            setRunning(true)

            // 先提交流程
            const flowConfig = {
                name: 'Untitled Flow',
                description: 'Running from editor',
                nodes: nodes.map(node => ({
                    id: node.id,
                    type: node.type || 'default',
                    position: node.position,
                    data: node.data,
                })),
                edges: edges.map(edge => ({
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    sourceHandle: edge.sourceHandle || undefined,
                    targetHandle: edge.targetHandle || undefined,
                })),
            }

            const submitResult = await submitFlow(flowConfig)
            const pipelineId = submitResult.pipeline_id

            // 启动任务
            await startJob(pipelineId)
            setCurrentJobId(pipelineId)

            // 更新所有节点状态为运行中
            nodes.forEach(node => {
                updateNode(node.id, { status: 'running' })
            })

            message.success('流程已开始运行，正在自动更新状态...')

            // 状态轮询会自动开始
        } catch (error) {
            message.error(`运行失败: ${error instanceof Error ? error.message : '未知错误'}`)
            setRunning(false)
            setCurrentJobId(null)
        }
    }

    // 停止流程
    const handleStop = async () => {
        if (!currentJobId) {
            message.warning('没有正在运行的任务')
            return
        }

        try {
            await stopJob(currentJobId)
            setRunning(false)
            setCurrentJobId(null)

            // 更新所有节点状态
            nodes.forEach(node => {
                updateNode(node.id, { status: 'idle' })
            })

            message.success('流程已停止')
        } catch (error) {
            message.error(`停止失败: ${error instanceof Error ? error.message : '未知错误'}`)
        }
    }

    // 保存流程
    const handleSave = async () => {
        if (!flowName.trim()) {
            message.warning('请输入流程名称')
            return
        }

        if (nodes.length === 0) {
            message.warning('画布为空，无法保存')
            return
        }

        try {
            setSaving(true)

            // 转换为后端格式
            const flowConfig = {
                name: flowName,
                description: flowDescription,
                nodes: nodes.map(node => ({
                    id: node.id,
                    type: node.type || 'default',
                    position: node.position,
                    data: node.data,
                })),
                edges: edges.map(edge => ({
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    sourceHandle: edge.sourceHandle || undefined,
                    targetHandle: edge.targetHandle || undefined,
                })),
            }

            const result = await submitFlow(flowConfig)
            message.success(`流程保存成功！ID: ${result.pipeline_id}`)
            setSaveModalOpen(false)
            setFlowName('')
            setFlowDescription('')
        } catch (error) {
            message.error(`保存失败: ${error instanceof Error ? error.message : '未知错误'}`)
        } finally {
            setSaving(false)
        }
    }

    // 加载流程列表
    const handleOpenLoadModal = async () => {
        setLoadModalOpen(true)
        setLoading(true)

        try {
            const jobs = await getAllJobs()
            setSavedFlows(jobs)
        } catch (error) {
            message.error('加载流程列表失败')
        } finally {
            setLoading(false)
        }
    }

    // 加载选中的流程
    const handleLoadFlow = (flow: any) => {
        try {
            // 从后端加载的流程数据转换为 React Flow 格式
            if (flow.config && flow.config.nodes) {
                const config = flow.config

                // 检测数据格式：Angular 格式有 operatorId 字段，React Flow 格式有 data 字段
                const isAngularFormat = config.nodes.some((n: any) => n.operatorId !== undefined)

                let loadedNodes, loadedEdges

                if (isAngularFormat) {
                    // 转换 Angular 格式到 React Flow 格式
                    console.log('检测到 Angular 格式，正在转换...')

                    loadedNodes = config.nodes.map((node: any, index: number) => ({
                        id: node.id,
                        type: 'custom',
                        position: node.position || { x: 100 + index * 150, y: 100 + index * 100 },
                        data: {
                            label: node.name || `节点 ${index + 1}`,
                            nodeId: node.name, // 使用节点名作为类型标识
                            description: '',
                            status: 'idle',
                            ...node.config, // 保留原始配置
                        },
                    }))

                    loadedEdges = config.edges?.map((edge: any) => ({
                        id: edge.id,
                        source: edge.source,
                        target: edge.target,
                        type: 'smoothstep',
                        animated: true,
                    })) || []
                } else {
                    // React Flow 格式直接使用
                    console.log('检测到 React Flow 格式')

                    loadedNodes = config.nodes.map((node: any) => ({
                        id: node.id,
                        type: node.type || 'custom',
                        position: node.position || { x: 0, y: 0 },
                        data: node.data || {},
                    }))

                    loadedEdges = config.edges?.map((edge: any) => ({
                        id: edge.id,
                        source: edge.source,
                        target: edge.target,
                        sourceHandle: edge.sourceHandle,
                        targetHandle: edge.targetHandle,
                        type: 'smoothstep',
                        animated: true,
                    })) || []
                }

                setNodes(loadedNodes)
                setEdges(loadedEdges)

                message.success(`已加载流程: ${flow.name || flow.jobId}`)
            } else {
                message.warning('流程数据格式错误：缺少 config.nodes')
            }
        } catch (error) {
            message.error('加载流程失败')
            console.error('Load flow error:', error)
        } finally {
            setLoadModalOpen(false)
        }
    }

    // 启用状态轮询（所有函数定义完成后）
    useJobStatusPolling(currentJobId, 1000, running)

    // 启用键盘快捷键（传入打开保存对话框的函数）
    useKeyboardShortcuts(() => setSaveModalOpen(true), true)

    return (
        <>
            {/* Gemini-style Toolbar */}
            <div className="h-16 px-4 flex items-center justify-between bg-[--gemini-main-bg] border-b border-[--gemini-border]">
                {/* Left: Logo */}
                <SageLogo />

                {/* Center: Mode-specific tools */}
                <div className="flex items-center gap-2">
                    {mode === 'canvas' && (
                        // Canvas mode: Show editing tools
                        <>
                            <IconButton
                                icon={<Play size={16} />}
                                label="运行"
                                onClick={handleRun}
                                disabled={nodes.length === 0 || running}
                                loading={running}
                                primary
                            />
                            <IconButton
                                icon={<Square size={16} />}
                                label="停止"
                                onClick={handleStop}
                                disabled={!currentJobId}
                            />
                            <IconButton
                                icon={<MessageSquare size={16} />}
                                label="Playground"
                                onClick={() => setPlaygroundOpen(true)}
                                disabled={nodes.length === 0}
                            />

                            <div className="h-6 w-px bg-[--gemini-border] mx-1" />

                            <IconButton
                                icon={<Save size={16} />}
                                label="保存"
                                onClick={() => setSaveModalOpen(true)}
                                disabled={nodes.length === 0}
                            />
                            <IconButton
                                icon={<FolderOpen size={16} />}
                                label="打开"
                                onClick={handleOpenLoadModal}
                            />
                            <IconButton
                                icon={<Download size={16} />}
                                label="导出"
                                onClick={handleExport}
                                disabled={!currentJobId}
                            />
                            <Upload
                                accept=".json"
                                showUploadList={false}
                                beforeUpload={handleImport}
                            >
                                <IconButton
                                    icon={<UploadIcon size={16} />}
                                    label="导入"
                                />
                            </Upload>

                            <div className="h-6 w-px bg-[--gemini-border] mx-1" />

                            <button
                                onClick={undo}
                                disabled={!canUndo}
                                className="p-2 rounded-full text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                                title="撤销"
                            >
                                <UndoIcon size={16} />
                            </button>
                            <button
                                onClick={redo}
                                disabled={!canRedo}
                                className="p-2 rounded-full text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                                title="重做"
                            >
                                <RedoIcon size={16} />
                            </button>

                            <div className="h-6 w-px bg-[--gemini-border] mx-1" />

                            <button
                                onClick={() => reactFlowInstance?.zoomIn()}
                                className="p-2 rounded-full text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] transition-all duration-200"
                                title="放大"
                            >
                                <ZoomIn size={16} />
                            </button>
                            <button
                                onClick={() => reactFlowInstance?.zoomOut()}
                                className="p-2 rounded-full text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] transition-all duration-200"
                                title="缩小"
                            >
                                <ZoomOut size={16} />
                            </button>
                        </>
                    )}
                </div>

                {/* Right: Mode switcher (always) + Theme toggle + Settings + User */}
                <div className="flex items-center gap-3">
                    <ModeSwitcher mode={mode} onModeChange={onModeChange} />

                    <ThemeToggle />

                    <button
                        onClick={() => setSettingsOpen(true)}
                        className="p-2 rounded-full text-[--gemini-text-secondary] hover:bg-[--gemini-hover-bg] transition-all duration-200"
                        title="设置"
                    >
                        <SettingsIcon size={18} />
                    </button>

                    <UserMenu
                        user={user}
                        isAuthenticated={isAuthenticated}
                        onLogout={logout}
                    />
                </div>
            </div>

            {/* Modals */}
            <Playground />
            <Settings open={settingsOpen} onClose={() => setSettingsOpen(false)} />

            {/* 保存模态框 */}
            <Modal
                title="保存流程"
                open={saveModalOpen}
                onOk={handleSave}
                onCancel={() => setSaveModalOpen(false)}
                confirmLoading={saving}
                okText="保存"
                cancelText="取消"
            >
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            流程名称 *
                        </label>
                        <Input
                            placeholder="请输入流程名称"
                            value={flowName}
                            onChange={(e) => setFlowName(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            流程描述
                        </label>
                        <Input.TextArea
                            placeholder="请输入流程描述（可选）"
                            value={flowDescription}
                            onChange={(e) => setFlowDescription(e.target.value)}
                            rows={4}
                        />
                    </div>
                </div>
            </Modal>

            {/* 加载模态框 */}
            <Modal
                title="打开流程"
                open={loadModalOpen}
                onCancel={() => setLoadModalOpen(false)}
                footer={null}
                width={600}
            >
                <List
                    loading={loading}
                    dataSource={savedFlows}
                    renderItem={(flow: any) => (
                        <List.Item
                            actions={[
                                <Button type="link" onClick={() => handleLoadFlow(flow)}>
                                    打开
                                </Button>
                            ]}
                        >
                            <List.Item.Meta
                                title={flow.name || flow.pipeline_id}
                                description={flow.description || `ID: ${flow.pipeline_id}`}
                            />
                        </List.Item>
                    )}
                    locale={{ emptyText: '暂无保存的流程' }}
                />
            </Modal>
        </>
    )
}
