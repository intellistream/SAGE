import { useState, useEffect } from 'react'
import { Input, Collapse, Badge, message, Spin } from 'antd'
import { Search, Box, Database, Zap, FileText, AlertCircle } from 'lucide-react'
import { getNodes, type NodeDefinition } from '../services/api'

const { Panel } = Collapse

// 节点分类映射
const categoryMap: Record<string, string> = {
    'FileSource': '数据源',
    'Source': '数据源',
    'Retriever': '处理',
    'SimpleRetriever': '处理',
    'Embedding': '处理',
    'LLM': '处理',
    'Sink': '输出',
    'TerminalSink': '输出',
}

// 节点图标映射
const iconMap: Record<string, React.ReactNode> = {
    '数据源': <FileText size={16} />,
    '处理': <Zap size={16} />,
    '输出': <Database size={16} />,
    '其他': <Box size={16} />,
}

export default function NodePalette() {
    const [nodes, setNodes] = useState<NodeDefinition[]>([])
    const [searchTerm, setSearchTerm] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        loadNodes()
    }, [])

    const loadNodes = async () => {
        try {
            setLoading(true)
            setError(null)
            const data = await getNodes()
            setNodes(data)
            message.success(`加载了 ${data.length} 个节点定义`)
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : '加载节点失败'
            setError(errorMsg)
            message.error(errorMsg)
            console.error('Failed to load nodes:', err)
        } finally {
            setLoading(false)
        }
    }

    const filteredNodes = nodes.filter(
        (node) =>
            node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            node.description.toLowerCase().includes(searchTerm.toLowerCase())
    )

    // 按分类分组
    const groupedNodes = filteredNodes.reduce((acc, node) => {
        // 根据节点名称推断分类
        const category = categoryMap[node.name] || '其他'
        if (!acc[category]) {
            acc[category] = []
        }
        acc[category].push(node)
        return acc
    }, {} as Record<string, NodeDefinition[]>)

    const onDragStart = (event: React.DragEvent, node: NodeDefinition) => {
        event.dataTransfer.setData('application/reactflow', JSON.stringify({
            type: 'custom',
            nodeId: node.name,
            label: node.name,
            description: node.description,
        }))
        event.dataTransfer.effectAllowed = 'move'
    }

    return (
        <div className="node-palette">
            <div className="p-4">
                <Input
                    prefix={<Search size={16} />}
                    placeholder="搜索节点..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    allowClear
                />
            </div>

            {/* 加载状态 */}
            {loading && (
                <div className="flex justify-center items-center p-8">
                    <Spin tip="加载节点..." />
                </div>
            )}

            {/* 错误状态 */}
            {error && !loading && (
                <div className="p-4 text-center">
                    <AlertCircle className="mx-auto mb-2 text-red-500" size={32} />
                    <p className="text-sm text-red-500 mb-2">{error}</p>
                    <button
                        onClick={loadNodes}
                        className="text-blue-500 hover:text-blue-700 text-sm"
                    >
                        重新加载
                    </button>
                </div>
            )}

            {/* 节点列表 */}
            {!loading && !error && (
                <Collapse
                    defaultActiveKey={['数据源', '处理', '输出', '其他']}
                    ghost
                    className="node-categories"
                >
                    {Object.entries(groupedNodes).map(([category, categoryNodes]) => (
                        <Panel
                            key={category}
                            header={
                                <div className="flex items-center justify-between text-[--gemini-text-primary]">
                                    <span>{category}</span>
                                    <Badge count={categoryNodes.length} showZero color="#1890ff" />
                                </div>
                            }
                        >
                            <div className="space-y-2">
                                {categoryNodes.map((node) => (
                                    <div
                                        key={node.id}
                                        className="node-item"
                                        draggable
                                        onDragStart={(e) => onDragStart(e, node)}
                                        title={node.description}
                                    >
                                        <div className="node-icon">{iconMap[category]}</div>
                                        <div className="flex-1 min-w-0">
                                            <div className="node-name text-[--gemini-text-primary] truncate">{node.name}</div>
                                            <div className="text-xs text-[--gemini-text-secondary] truncate">
                                                {node.description}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </Panel>
                    ))}
                </Collapse>
            )}

            {!loading && !error && filteredNodes.length === 0 && (
                <div className="text-center py-4 text-[--gemini-text-secondary]">
                    没有找到匹配的节点
                </div>
            )}
        </div>
    )
}
