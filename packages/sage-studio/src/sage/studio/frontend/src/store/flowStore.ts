import { create } from 'zustand'
import {
    Node,
    Edge,
    OnNodesChange,
    OnEdgesChange,
    applyNodeChanges,
    applyEdgeChanges,
} from 'reactflow'

// 历史记录接口
interface HistoryState {
    nodes: Node[]
    edges: Edge[]
}

// 作业状态接口（与 API 保持一致）
export interface JobStatus {
    job_id: string
    status: 'idle' | 'running' | 'stopped' | 'error'
    use_ray: boolean
    isRunning: boolean
    // 扩展字段：节点状态
    nodeStates?: Record<string, {
        status: 'pending' | 'running' | 'completed' | 'failed'
        startTime?: string
        endTime?: string
        error?: string
    }>
    startTime?: string
    endTime?: string
    error?: string
}

export interface FlowState {
    nodes: Node[]
    edges: Edge[]
    selectedNode: Node | null
    reactFlowInstance: any | null

    // 历史记录（撤销/重做）
    history: HistoryState[]
    historyIndex: number
    maxHistorySize: number

    // 作业状态
    currentJobId: string | null
    jobStatus: JobStatus | null
    isPolling: boolean

    onNodesChange: OnNodesChange
    onEdgesChange: OnEdgesChange
    addNode: (node: Node) => void
    updateNode: (id: string, data: any) => void
    deleteNode: (id: string) => void
    selectNode: (node: Node | null) => void
    setNodes: (nodes: Node[]) => void
    setEdges: (edges: Edge[]) => void
    setReactFlowInstance: (instance: any) => void

    // 历史记录操作
    pushHistory: () => void
    undo: () => void
    redo: () => void
    canUndo: () => boolean
    canRedo: () => boolean

    // 作业状态操作
    setCurrentJobId: (jobId: string | null) => void
    setJobStatus: (status: JobStatus | null) => void
    updateNodeStatus: (nodeId: string, status: any) => void
    setIsPolling: (polling: boolean) => void
}

// 防抖计时器（用于避免拖动时每个像素都保存历史）
let pushHistoryTimer: NodeJS.Timeout | null = null

export const useFlowStore = create<FlowState>((set, get) => ({
    nodes: [],
    edges: [],
    selectedNode: null,
    reactFlowInstance: null,

    // 历史记录初始化 - 包含初始空状态
    history: [{ nodes: [], edges: [] }],
    historyIndex: 0,
    maxHistorySize: 50,

    // 作业状态初始化
    currentJobId: null,
    jobStatus: null,
    isPolling: false,

    onNodesChange: (changes) => {
        set({
            nodes: applyNodeChanges(changes, get().nodes),
        })

        // 检查是否是拖动结束事件
        const isDragEnd = changes.some(change =>
            change.type === 'position' && change.dragging === false
        )

        // 只在非拖动事件或拖动结束时保存历史
        if (isDragEnd || !changes.some(change => change.type === 'position')) {
            // 清除之前的计时器
            if (pushHistoryTimer) {
                clearTimeout(pushHistoryTimer)
            }
            // 使用防抖，300ms 后保存历史
            pushHistoryTimer = setTimeout(() => {
                get().pushHistory()
            }, 300)
        }
    },

    onEdgesChange: (changes) => {
        set({
            edges: applyEdgeChanges(changes, get().edges),
        })
        // 边变化时保存历史（边的变化通常不频繁，直接保存）
        get().pushHistory()
    },

    addNode: (node) => {
        set((state) => ({
            nodes: [...state.nodes, node],
        }))
        get().pushHistory()
    },

    updateNode: (id, data) => {
        set((state) => {
            const updatedNodes = state.nodes.map((node) =>
                node.id === id ? { ...node, data: { ...node.data, ...data } } : node
            )
            // 同时更新 selectedNode，如果它是被修改的节点
            const updatedSelectedNode = state.selectedNode?.id === id
                ? updatedNodes.find(n => n.id === id) || null
                : state.selectedNode

            return {
                nodes: updatedNodes,
                selectedNode: updatedSelectedNode,
            }
        })
        get().pushHistory()
    },

    deleteNode: (id) => {
        set((state) => ({
            nodes: state.nodes.filter((node) => node.id !== id),
            edges: state.edges.filter((edge) => edge.source !== id && edge.target !== id),
        }))
        get().pushHistory()
    },

    selectNode: (node) => {
        set({ selectedNode: node })
    },

    setNodes: (nodes) => {
        set({ nodes })
        get().pushHistory()
    },

    setEdges: (edges) => {
        set({ edges })
        get().pushHistory()
    },

    setReactFlowInstance: (instance) => {
        set({ reactFlowInstance: instance })
    },

    // 历史记录操作
    pushHistory: () => {
        const { nodes, edges, history, historyIndex, maxHistorySize } = get()

        // 创建当前状态快照
        const newState: HistoryState = {
            nodes: JSON.parse(JSON.stringify(nodes)),
            edges: JSON.parse(JSON.stringify(edges)),
        }

        // 检查是否与当前历史状态相同（避免重复保存）
        const currentState = history[historyIndex]
        if (currentState &&
            JSON.stringify(currentState.nodes) === JSON.stringify(newState.nodes) &&
            JSON.stringify(currentState.edges) === JSON.stringify(newState.edges)) {
            return // 状态未变化，不保存
        }

        // 如果不在历史末尾，删除当前位置之后的历史
        const newHistory = history.slice(0, historyIndex + 1)

        // 添加新状态
        newHistory.push(newState)

        // 限制历史大小
        if (newHistory.length > maxHistorySize) {
            newHistory.shift()
            // 如果删除了第一个元素，historyIndex 需要减 1
            set({
                history: newHistory,
                historyIndex: newHistory.length - 1,
            })
        } else {
            set({
                history: newHistory,
                historyIndex: newHistory.length - 1,
            })
        }
    },

    undo: () => {
        const { history, historyIndex } = get()

        if (historyIndex > 0) {
            const previousState = history[historyIndex - 1]
            set({
                nodes: JSON.parse(JSON.stringify(previousState.nodes)),
                edges: JSON.parse(JSON.stringify(previousState.edges)),
                historyIndex: historyIndex - 1,
            })
        }
    },

    redo: () => {
        const { history, historyIndex } = get()

        if (historyIndex < history.length - 1) {
            const nextState = history[historyIndex + 1]
            set({
                nodes: JSON.parse(JSON.stringify(nextState.nodes)),
                edges: JSON.parse(JSON.stringify(nextState.edges)),
                historyIndex: historyIndex + 1,
            })
        }
    },

    canUndo: () => {
        const { historyIndex } = get()
        return historyIndex > 0
    },

    canRedo: () => {
        const { history, historyIndex } = get()
        return historyIndex < history.length - 1
    },

    // 作业状态操作
    setCurrentJobId: (jobId) => {
        set({ currentJobId: jobId })
    },

    setJobStatus: (status) => {
        set({ jobStatus: status })

        // 如果有节点状态，更新节点视觉状态
        if (status?.nodeStates) {
            const { nodes } = get()
            const updatedNodes = nodes.map(node => {
                const nodeStatus = status.nodeStates?.[node.id]
                if (nodeStatus) {
                    return {
                        ...node,
                        data: {
                            ...node.data,
                            status: nodeStatus.status,
                            error: nodeStatus.error,
                        },
                        style: {
                            ...node.style,
                            border: nodeStatus.status === 'running'
                                ? '2px solid #1890ff'
                                : nodeStatus.status === 'completed'
                                    ? '2px solid #52c41a'
                                    : nodeStatus.status === 'failed'
                                        ? '2px solid #ff4d4f'
                                        : undefined,
                        },
                    }
                }
                return node
            })
            set({ nodes: updatedNodes })
        }
    },

    updateNodeStatus: (nodeId, status) => {
        set((state) => {
            const updatedNodes = state.nodes.map((node) =>
                node.id === nodeId
                    ? {
                        ...node,
                        data: {
                            ...node.data,
                            status: status.status,
                            error: status.error,
                        },
                        style: {
                            ...node.style,
                            border: status.status === 'running'
                                ? '2px solid #1890ff'
                                : status.status === 'completed'
                                    ? '2px solid #52c41a'
                                    : status.status === 'failed'
                                        ? '2px solid #ff4d4f'
                                        : undefined,
                        },
                    }
                    : node
            )
            return { nodes: updatedNodes }
        })
    },

    setIsPolling: (polling) => {
        set({ isPolling: polling })
    },
}))
