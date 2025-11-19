import { useState, useEffect } from 'react'
import { Button, Space, Tooltip, Modal, Input, message, List, Upload, Segmented } from 'antd'
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
} from 'lucide-react'
import { useFlowStore } from '../store/flowStore'
import { usePlaygroundStore } from '../store/playgroundStore'
import { submitFlow, getAllJobs, startJob, stopJob, exportFlow, importFlow } from '../services/api'
import { useJobStatusPolling } from '../hooks/useJobStatusPolling'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import Playground from './Playground'
import Settings from './Settings'
import type { AppMode } from '../App'

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
            <div className="toolbar">
                <div className="flex items-center justify-between w-full">
                    <Space>
                        <span className="text-lg font-bold text-gray-800 ml-4">
                            SAGE Studio
                        </span>

                        {/* 模式切换 */}
                        <Segmented
                            value={mode}
                            onChange={(value) => onModeChange(value as AppMode)}
                            options={[
                                {
                                    label: (
                                        <Space size={4}>
                                            <LayoutIcon size={14} />
                                            <span>Builder</span>
                                        </Space>
                                    ),
                                    value: 'builder',
                                },
                                {
                                    label: (
                                        <Space size={4}>
                                            <MessageSquare size={14} />
                                            <span>Chat</span>
                                        </Space>
                                    ),
                                    value: 'chat',
                                },
                            ]}
                        />
                    </Space>

                    <Space>
                        {/* Builder 模式的工具按钮 */}
                        {mode === 'builder' && (
                            <>
                                <Tooltip title="运行流程">
                                    <Button
                                        type="primary"
                                        icon={<Play size={16} />}
                                        onClick={handleRun}
                                        disabled={nodes.length === 0 || running}
                                        loading={running}
                                    >
                                        运行
                                    </Button>
                                </Tooltip>

                                <Tooltip title="停止">
                                    <Button
                                        icon={<Square size={16} />}
                                        onClick={handleStop}
                                        disabled={!currentJobId}
                                    >
                                        停止
                                    </Button>
                                </Tooltip>

                                <Tooltip title="Playground">
                                    <Button
                                        icon={<MessageSquare size={16} />}
                                        onClick={() => setPlaygroundOpen(true)}
                                        disabled={nodes.length === 0}
                                    >
                                        Playground
                                    </Button>
                                </Tooltip>

                                <div className="h-6 w-px bg-gray-300 mx-2" />

                                <Tooltip title="保存流程">
                                    <Button
                                        icon={<Save size={16} />}
                                        onClick={() => setSaveModalOpen(true)}
                                        disabled={nodes.length === 0}
                                    >
                                        保存
                                    </Button>
                                </Tooltip>

                                <Tooltip title="打开流程">
                                    <Button
                                        icon={<FolderOpen size={16} />}
                                        onClick={handleOpenLoadModal}
                                    >
                                        打开
                                    </Button>
                                </Tooltip>

                                <Tooltip title="导出流程">
                                    <Button
                                        icon={<Download size={16} />}
                                        onClick={handleExport}
                                        disabled={!currentJobId}
                                    >
                                        导出
                                    </Button>
                                </Tooltip>

                                <Tooltip title="导入流程">
                                    <Upload
                                        accept=".json"
                                        showUploadList={false}
                                        beforeUpload={handleImport}
                                    >
                                        <Button icon={<UploadIcon size={16} />}>
                                            导入
                                        </Button>
                                    </Upload>
                                </Tooltip>

                                <div className="h-6 w-px bg-gray-300 mx-2" />

                                <Tooltip title="撤销 (Ctrl/Cmd+Z)">
                                    <Button
                                        icon={<UndoIcon size={16} />}
                                        onClick={undo}
                                        disabled={!canUndo()}
                                    />
                                </Tooltip>

                                <Tooltip title="重做 (Ctrl/Cmd+Shift+Z)">
                                    <Button
                                        icon={<RedoIcon size={16} />}
                                        onClick={redo}
                                        disabled={!canRedo()}
                                    />
                                </Tooltip>

                                <div className="h-6 w-px bg-gray-300 mx-2" />

                                <Tooltip title="放大">
                                    <Button
                                        icon={<ZoomIn size={16} />}
                                        onClick={() => reactFlowInstance?.zoomIn()}
                                    />
                                </Tooltip>

                                <Tooltip title="缩小">
                                    <Button
                                        icon={<ZoomOut size={16} />}
                                        onClick={() => reactFlowInstance?.zoomOut()}
                                    />
                                </Tooltip>

                                <div className="h-6 w-px bg-gray-300 mx-2" />
                            </>
                        )}

                        <Tooltip title="设置">
                            <Button
                                icon={<SettingsIcon size={16} />}
                                onClick={() => setSettingsOpen(true)}
                            />
                        </Tooltip>
                    </Space>
                </div>
            </div>

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

            {/* Playground */}
            <Playground />

            {/* Settings */}
            <Settings open={settingsOpen} onClose={() => setSettingsOpen(false)} />
        </>
    )
}
