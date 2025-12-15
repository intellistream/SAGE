import { useCallback, useRef, useState } from 'react'
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    addEdge,
    Connection,
    Edge,
    Node,
    BackgroundVariant,
    ReactFlowInstance,
} from 'reactflow'
import CustomNode from './nodes/CustomNode'
import { useFlowStore } from '../store/flowStore'

const nodeTypes = {
    custom: CustomNode,
}

export default function FlowEditor() {
    const { nodes, edges, onNodesChange, onEdgesChange, addNode, selectNode, setReactFlowInstance } = useFlowStore()
    const reactFlowWrapper = useRef<HTMLDivElement>(null)
    const [reactFlowInstance, setLocalReactFlowInstance] = useState<ReactFlowInstance | null>(null)

    const handleInit = useCallback((instance: ReactFlowInstance) => {
        setLocalReactFlowInstance(instance)
        setReactFlowInstance(instance)
    }, [setReactFlowInstance])

    const onConnect = useCallback(
        (params: Connection) => {
            if (!params.source || !params.target) return

            const newEdge: Edge = {
                id: `e${params.source}-${params.target}`,
                source: params.source,
                target: params.target,
                sourceHandle: params.sourceHandle,
                targetHandle: params.targetHandle,
                type: 'smoothstep',
                animated: true,
            }
            useFlowStore.setState((state) => ({
                edges: addEdge(newEdge, state.edges),
            }))
        },
        []
    )

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault()
        event.dataTransfer.dropEffect = 'move'
    }, [])

    const onDrop = useCallback(
        (event: React.DragEvent) => {
            event.preventDefault()

            const nodeData = event.dataTransfer.getData('application/reactflow')
            if (!nodeData) return

            const data = JSON.parse(nodeData)

            // 获取 React Flow 画布的边界
            if (!reactFlowWrapper.current || !reactFlowInstance) return

            const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect()

            // 将屏幕坐标转换为 React Flow 画布坐标
            const position = reactFlowInstance.project({
                x: event.clientX - reactFlowBounds.left,
                y: event.clientY - reactFlowBounds.top,
            })

            // 生成唯一的节点 ID
            const nodeId = `node-${Date.now()}`

            // 计算同类型节点的数量，用于生成默认名称
            const sameTypeNodes = nodes.filter(n => n.data.nodeId === data.nodeId)
            const nodeNumber = sameTypeNodes.length + 1

            // 生成默认名称：节点类型名 + 编号
            const defaultLabel = `${data.label} ${nodeNumber}`

            const newNode: Node = {
                id: nodeId,
                type: 'custom',
                position,
                data: {
                    label: defaultLabel,  // 使用生成的默认名称
                    nodeId: data.nodeId,
                    description: data.description || '',
                    status: 'idle',
                },
            }

            addNode(newNode)
        },
        [addNode, reactFlowInstance, nodes]
    )

    const onNodeClick = useCallback(
        (_event: React.MouseEvent, node: Node) => {
            selectNode(node)
        },
        [selectNode]
    )

    const onPaneClick = useCallback(() => {
        selectNode(null)
    }, [selectNode])

    return (
        <div ref={reactFlowWrapper} style={{ width: '100%', height: '100%' }} className="bg-[--gemini-main-bg]">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onInit={handleInit}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                fitView
                snapToGrid
                snapGrid={[15, 15]}
                defaultEdgeOptions={{
                    type: 'smoothstep',
                    animated: true,
                }}
                className="react-flow-canvas"
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={12}
                    size={1}
                    className="react-flow-background"
                />
                <Controls className="react-flow-controls" />
                <MiniMap
                    nodeColor={(node) => {
                        if (node.data.status === 'running') return '#52c41a'
                        if (node.data.status === 'error') return '#ff4d4f'
                        return '#1890ff'
                    }}
                    maskColor="rgba(128, 128, 128, 0.3)"
                />
            </ReactFlow>
        </div>
    )
}
